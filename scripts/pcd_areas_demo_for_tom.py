import os
import sys
import configparser
import csv
import re
from collections import defaultdict, OrderedDict
import fiona
import glob
import itertools
from shapely.geometry import shape, Polygon, MultiPolygon, mapping
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.wkt import loads
from rtree import index
from tqdm import tqdm

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')
DATA_RAW_SHAPES = os.path.join(BASE_PATH, 'raw', 'd_shapes')
DATA_BUILDING_DATA = os.path.join(BASE_PATH, 'raw', 'e_dem_and_buildings')

def read_exchange_areas():
    """Read all exchange area shapes

    Data Schema
    -----------
    * id: 'string'
        Unique exchange id
    """
    exchange_areas = []

    with fiona.open(
        os.path.join(
            DATA_RAW_SHAPES, 'all_exchange_areas', '_exchange_areas.shp')
            , 'r'
            ) as source:
            for feature in source:
                new_id = feature['properties']['id'].replace('/','')
                exchange_areas.append({
                    'type': feature['type'],
                    'geometry': feature['geometry'],
                    'properties':{
                        'id': new_id
                    }
                })

            return exchange_areas

def write_shapefile(data, directory, id):

    # Translate props to Fiona sink schema
    prop_schema = []
    for name, value in data[0]['properties'].items():
        fiona_prop_type = next((fiona_type for fiona_type, python_type in fiona.FIELD_TYPES_MAP.items() if python_type == type(value)), None)
        prop_schema.append((name, fiona_prop_type))

    sink_driver = 'ESRI Shapefile'
    sink_crs = {'init': 'epsg:27700'}
    sink_schema = {
        'geometry': data[0]['geometry']['type'],
        'properties': OrderedDict(prop_schema)
    }

    # Create path
    folder_directory = os.path.join(DATA_RAW_SHAPES, directory)
    if not os.path.exists(folder_directory):
        os.makedirs(folder_directory)

    for area in data:
        filename = area['properties'][id].replace('/', '')
        # Write all elements to output file
        with fiona.open(os.path.join(folder_directory, filename + '.shp'), 'w', driver=sink_driver, crs=sink_crs, schema=sink_schema) as sink:
            sink.write(area)

def read_postcode_sectors(path):
    """
    Read all shapes

    Yields
    ------
    postcode_areas : iterable[dict]

    """
    with fiona.open(path, 'r') as source:
        for feature in source:
            #if feature['properties']['postcode'].startswith('CB'):
            yield feature

# def postcode_sector_area(path):
#     """
#     Read .csv with postcode sector areas (m^2)

#     """
#     area_data = []

#     directory = os.path.dirname(os.path.abspath(path))
#     csv_path = os.path.join(directory, 'postcode_sectors_area.csv')

#     with open(csv_path, 'r') as source:
#         reader = csv.DictReader(source)
#         for feature in reader:
#             print(feature)
#             area_data.append({
#                 'postcode': feature['postcode'],
#                 'area': ['area'],
#             })

#     output = []

#     for area in area_data:
#         first_two_characters = area['postcode'][2:]
#         postcode_area = ''.join([i for i in first_two_characters if not i.isdigit()])
#         interim_data = []
#         for second_area in area_data:
#             if second_area.startswith(postcode_area):
#                 interim_data.append(second_area['area'])
#         mean = mean(interim_data)
#         minimum = min(interim_data)
#         output.append({
#             'postcode_area': postcode_area,
#             'mean': mean,
#             'minimum': minimum,
#         })

#     return output

def generate_postcode_areas(data, min_area, special_areas):
    """
    Create postcode area polygons using postcode sectors.

    - Gets the postcode area by cutting the first two characters of the postcode.
    - Numbers are then removed to leave just the postcode area character(s).
    - Polygons are then dissolved on this variable

    """
    def get_postcode_area(feature):
        postcode = feature['properties']['postcode']
        match = re.search('^[A-Z]+', postcode)
        if match:
            return match.group(0)

    for key, group in itertools.groupby(data, key=get_postcode_area):
        # print(key)
        # print(special_areas)
        if key not in special_areas:
            threshold = min_area
        else:
            threshold = 1e6

        # print(key)
        buffer_distance = 0.001
        geoms = [shape(feature['geometry']) for feature in group]

        # total_area = sum([geom.area for geom in geoms])/10e6
        # print(total_area)

        # print(len(geoms))
        geoms = [geom for geom in geoms if geom.area > threshold]
        # print(len(geoms))
        buffered = [geom.buffer(buffer_distance) for geom in geoms]
        # print(len(buffered))
        geom = unary_union(buffered)
        # print('done union')
        yield {
            'type': "Feature",
            'geometry': mapping(geom),
            'properties': {
                'postcode_area': key
            }
        }

def fix_up(feature, threshold_area, special_areas):
    """
    Dissolve/buffer

    """
    geom = shape(feature['geometry'])
    if feature['properties']['postcode_area'] not in special_areas:
        threshold = threshold_area
    else:
        threshold = 1e6
    geom = drop_small_multipolygon_parts(geom, threshold)
    geom = drop_holes(geom)
    if geom.type != 'MultiPolygon':
        geom = MultiPolygon([geom])

    return {
        'type': "Feature",
        'geometry': mapping(geom),
        'properties': feature['properties']
    }

def drop_small_multipolygon_parts(geom, threshold_area):
    if geom.type == 'MultiPolygon':
        return MultiPolygon(
            p
            for p in geom.geoms
            if p.area > threshold_area
        )
    return geom

def pick_biggest_if_multi(geom):
    if geom.type == 'MultiPolygon':
        geom = max(geom, key=lambda g: g.area)
    return geom


def drop_holes(geom):
    if geom.type == 'Polygon':
        return Polygon(geom.exterior)
    if geom.type == 'MultiPolygon':
        return MultiPolygon(Polygon(p.exterior) for p in geom.geoms)
    return geom


def get_fiona_type(value):
    for fiona_type, python_type in fiona.FIELD_TYPES_MAP.items():
        if python_type == type(value):
            return fiona_type
    return None


def write_single_shapefile(feature, directory):
    first_data_item = feature

    prop_schema = []
    for name, value in first_data_item['properties'].items():
        fiona_prop_type = get_fiona_type(value)
        prop_schema.append((name, fiona_prop_type))

    driver = 'ESRI Shapefile'
    crs = {'init': 'epsg:27700'}
    schema = {
        'geometry': first_data_item['geometry']['type'],
        'properties': OrderedDict(prop_schema)
    }

    # Create path
    if not os.path.exists(directory):
        os.makedirs(directory)
    name = first_data_item['properties']['postcode_area']
    path = os.path.join(directory, name.lower() + '.shp')

    with fiona.open(path, 'w', driver=driver, crs=crs, schema=schema) as sink:
        sink.write(first_data_item)

def run_postcode_area_generation():
    """
    Generates postcode areas from postcode sectors.

    MIN_AREA helps to remove smaller areas first, to speed up processing. However,
    Central East London won't process if it's set too large.

    MIN_AREA = 1e7 works well for everywhere except EC, HA, N, NW, SE, SM, SW, W, WC
    MIN_AREA = 1e2 works well for EC, HA, N, NW, SE, SM, SW, W, WC.

    """
    min_area_small_areas = [
        'EC',
        'HA',
        'N',
        'NW',
        'SE',
        'SM',
        'SW',
        'W',
        'WC',
    ]

    MIN_AREA = 1e6  # 10km^2

    PC_PATH = os.path.join(DATA_RAW_SHAPES,'postcode_sectors', '_postcode_sectors.shp')
    PC_OUT_PATH = os.path.join(DATA_RAW_SHAPES, 'postcode_areas')

    PC_SECTORS = read_postcode_sectors(PC_PATH)
    # area_stats_postcode_area = postcode_sector_area(PC_PATH)
    # print(area_stats_postcode_area)
    pc_sectors_by_area = generate_postcode_areas(PC_SECTORS, MIN_AREA, min_area_small_areas)

    for pc_area_feature in tqdm(pc_sectors_by_area):
        PC_AREA = fix_up(pc_area_feature, MIN_AREA, min_area_small_areas)
        write_single_shapefile(PC_AREA, PC_OUT_PATH)

def read_postcode_areas():

    directory = os.path.join(DATA_RAW_SHAPES, 'postcode_areas')
    pathlist = glob.iglob(os.path.join(directory + '/*.shp'), recursive=True)

    for path in pathlist:
        with fiona.open(path, 'r') as source:
            for feature in source:
                yield feature

def intersect_pcd_areas_and_exchanges(exchanges, areas):

    exchange_to_pcd_area_lut = defaultdict(list)

    idx = index.Index(
        (i, shape(exchange['geometry']).bounds, exchange)
        for i, exchange in enumerate(exchanges)
    )

    for area in areas:
        print(area['properties'])
        for n in idx.intersection((shape(area['geometry']).bounds), objects=True):
            area_shape = shape(area['geometry'])
            exchange_shape = shape(n.object['geometry'])
            if area_shape.intersects(exchange_shape):
                exchange_to_pcd_area_lut[n.object['properties']['id']].append({
                    'postcode_area': area['properties']['postcode_a'],
                    })

    return exchange_to_pcd_area_lut

#####################################################################################
# 7) intersect lad_areas with exchanges to get exchange_to_lad_area_lut
#####################################################################################

def read_lad_areas():
    with fiona.open(os.path.join(DATA_RAW_SHAPES, 'lad_uk_2016-12', 'lad_uk_2016-12.shp'), 'r') as source:
        return [area for area in source]

def intersect_lad_areas_and_exchanges(exchanges, areas):

    exchange_to_lad_area_lut = defaultdict(list)

    # Initialze Rtree
    idx = index.Index()
    [idx.insert(0, shape(exchange['geometry']).bounds, exchange) for exchange in exchanges]

    for area in areas:
        for n in idx.intersection((shape(area['geometry']).bounds), objects=True):
            area_shape = shape(area['geometry'])
            exchange_shape = shape(n.object['geometry'])
            if area_shape.intersects(exchange_shape):
                exchange_to_lad_area_lut[n.object['properties']['id']].append({
                    'lad': area['properties']['name'],
                    })

    return exchange_to_lad_area_lut
###############################################################################

# # add necessary properties (postcode) to exchange polygons
exchange_areas = read_exchange_areas()

# generate single set of postcode areas from postcode sectors
run_postcode_area_generation()

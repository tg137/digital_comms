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

DATA_RAW_INPUTS = os.path.join(BASE_PATH, 'raw', 'a_fixed_model')
DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')
DATA_RAW_SHAPES = os.path.join(BASE_PATH, 'raw', 'd_shapes')
DATA_BUILDING_DATA = os.path.join(BASE_PATH, 'raw', 'e_dem_and_buildings')

#####################################################################################
# 1) generate unique postcode to exchange lut and export as one .csv per exchange
#####################################################################################

def get_unique_postcodes_by_exchanges(lower_units):
    """
    Function to get unique postcodes by exchange.
    Produce a dict with the key being the grouping variable and the value being a list.
    """

    all_data = []

    for item in lower_units:
        all_data.append(item['exchange_id'])

    all_unique_exchanges = set(all_data)

    data_by_exchange = defaultdict(list)

    for exchange in all_unique_exchanges:
        for unit in lower_units:
            if exchange == unit['exchange_id']:
                data_by_exchange[exchange].append({
                    'postcode': unit['postcode']
                    })

    return data_by_exchange

def read_pcd_to_exchange_lut():
    """
    Produces all unique postcode-to-exchange combinations from available data, including:

    'January 2013 PCP to Postcode File Part One.csv'
    'January 2013 PCP to Postcode File Part Two.csv'
    'pcp.to.pcd.dec.11.one.csv'
    'pcp.to.pcd.dec.11.two.csv'
    'from_tomasso_valletti.csv'

    Data Schema
    ----------
    * exchange_id: 'string'
        Unique Exchange ID
    * postcode: 'string'
        Unique Postcode

    Returns
    -------
    pcd_to_exchange_data: List of dicts
    """
    pcd_to_exchange_data = []

    with open(os.path.join(DATA_RAW_INPUTS, 'network_hierarchy_data', 'January 2013 PCP to Postcode File Part One.csv'), 'r', encoding='utf8', errors='replace') as system_file:
        reader = csv.reader(system_file)
        for skip in range(11):
            next(reader)
        for line in reader:
            pcd_to_exchange_data.append({
                'exchange_id': line[0].replace("/", ""),
                'postcode': line[2].replace(" ", "")
            })

    with open(os.path.join(DATA_RAW_INPUTS, 'network_hierarchy_data','January 2013 PCP to Postcode File Part Two.csv'), 'r',  encoding='utf8', errors='replace') as system_file:
        reader = csv.reader(system_file)
        for skip in range(11):
            next(reader)
        for line in reader:
            pcd_to_exchange_data.append({
                'exchange_id': line[0].replace("/", ""),
                'postcode': line[2].replace(" ", "")
            })

    with open(os.path.join(DATA_RAW_INPUTS, 'network_hierarchy_data','pcp.to.pcd.dec.11.one.csv'), 'r',  encoding='utf8', errors='replace') as system_file:
        reader = csv.reader(system_file)
        for skip in range(11):
            next(reader)
        for line in reader:
            pcd_to_exchange_data.append({
                'exchange_id': line[0].replace("/", ""),
                'postcode': line[2].replace(" ", "")
            })

    with open(os.path.join(DATA_RAW_INPUTS, 'network_hierarchy_data','pcp.to.pcd.dec.11.two.csv'), 'r', encoding='utf8', errors='replace') as system_file:
        reader = csv.reader(system_file)
        next(reader)
        for line in reader:
            pcd_to_exchange_data.append({
                'exchange_id': line[0].replace("/", ""),
                'postcode': line[2].replace(" ", "")
            })

    with open(os.path.join(DATA_RAW_INPUTS, 'network_hierarchy_data','from_tomasso_valletti.csv'), 'r', encoding='utf8', errors='replace') as system_file:
        reader = csv.reader(system_file)
        next(reader)
        for line in reader:
            pcd_to_exchange_data.append({
                'exchange_id': line[0].replace("/", ""),
                'postcode': line[1].replace(" ", "")
            })

    ### find unique values in list of dicts
    return list({pcd['postcode']:pcd for pcd in pcd_to_exchange_data}.values())

#####################################################################################
# 2) generate unique postcode to cabinet lut and export as one .csv per exchange
#####################################################################################

def read_pcd_to_cabinet_lut():
    """
    Produces all postcode-to-cabinet-to-exchange combinations from available data, including:

        - January 2013 PCP to Postcode File Part One.csv
        - January 2013 PCP to Postcode File Part Two.csv
        - pcp.to.pcd.dec.11.one.csv'
        - pcp.to.pcd.dec.11.two.csv'

    Data Schema
    -----------
    * exchange_id: 'string'
        Unique Exchange ID
    * name: 'string'
        Unique Exchange Name
    * cabinet_id: 'string'
        Unique Cabinet ID
    * exchange_only_flag: 'int'
        Exchange only binary

    Returns
    -------
    pcp_data: Dict of dicts
    """

    pcp_data = []

    with open(os.path.join(DATA_RAW_INPUTS, 'network_hierarchy_data','January 2013 PCP to Postcode File Part One.csv'), 'r', encoding='utf8', errors='replace') as system_file:
        reader = csv.reader(system_file)
        for skip in range(11):
            next(reader)
        for line in reader:
            pcp_data.append({
                'exchange_id': line[0].replace("/", ""),
                'name': line[1],
                'postcode': line[2],
                'cabinet': line[3],
                'exchange_only_flag': line[4]
            })

    with open(os.path.join(DATA_RAW_INPUTS, 'network_hierarchy_data','January 2013 PCP to Postcode File Part Two.csv'), 'r', encoding='utf8', errors='replace') as system_file:
        reader = csv.reader(system_file)
        for skip in range(11):
            next(reader)
        for line in reader:
            pcp_data.append({
                'exchange_id': line[0].replace("/", ""),
                'name': line[1],
                'postcode': line[2],
                'cabinet': line[3],
                'exchange_only_flag': line[4]
            })

    with open(os.path.join(DATA_RAW_INPUTS, 'network_hierarchy_data','pcp.to.pcd.dec.11.one.csv'), 'r', encoding='utf8', errors='replace') as system_file:
        reader = csv.reader(system_file)
        next(reader)
        for line in reader:
            pcp_data.append({
                'exchange_id': line[0].replace("/", ""),
                'name': line[1],
                'postcode': line[2],
                'cabinet': line[3],
                'exchange_only_flag': line[4]
            })

    with open(os.path.join(DATA_RAW_INPUTS, 'network_hierarchy_data','pcp.to.pcd.dec.11.two.csv'), 'r', encoding='utf8', errors='replace') as system_file:
        reader = csv.reader(system_file)
        next(reader)
        for line in reader:
            pcp_data.append({
                'exchange_id': line[0].replace("/", ""),
                'name': line[1],
                'postcode': line[2],
                'cabinet': line[3],
                'exchange_only_flag': line[4]
            })

    return pcp_data

def get_unique_postcodes_to_cabs_by_exchange(lower_units):
    """
    Function to get unique postcodes by exchange.
    Produce a dict with the key being the grouping variable and the value being a list.
    """

    all_data = []

    for item in lower_units:
        all_data.append(item['exchange_id'])

    all_unique_exchanges = set(all_data)

    data_by_exchange = defaultdict(list)

    for exchange in all_unique_exchanges:
        for unit in lower_units:
            if exchange == unit['exchange_id']:
                data_by_exchange[exchange].append({
                    'postcode': unit['postcode'],
                    'cabinet': unit['cabinet'],
                    'exchange_only_flag': unit['exchange_only_flag']
                    })

    return data_by_exchange

#####################################################################################
# 3) add necessary properties (postcode) to exchange polygons
#####################################################################################

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

def load_exchange_properties():
    """Read all exchange properties data

    Data Schema
    -----------
    * postcode: 'string'
        Unique exchange postcode
    * id: 'string'
        Unique exchange id

    """
    exchange_postcodes_path = os.path.join(DATA_RAW_INPUTS, 'exchange_geotypes', 'exchange_properties.csv')

    output = []

    with open(exchange_postcodes_path, 'r') as system_file:
        reader = csv.reader(system_file)
        next(reader)
        for line in reader:
            output.append({
                'id': line[0].replace("/", ""),
                # 'Name': line[1],
                'postcode': line[2],
                # 'Region': line[3],
                # 'County': line[4],
                'geotype': line[5],
                'prems_over': line[6],
                'prems_under': line[7],
            })

    return output

def add_properties_to_exchanges(exchanges, properties):

    """
    Takes exchange polygons, adds required data from properties.

    Data Schema
    -----------
    * postcode: 'string'
        Unique exchange postcode
    * id: 'string'
        Unique exchange id
    """

    output = []

    for exchange in exchanges:
        for exchange_property in properties:
            if exchange['properties']['id'] == exchange_property['id']:
                output.append({
                    'type': exchange['type'],
                    'geometry': exchange['geometry'],
                    'properties': {
                        'id': exchange['properties']['id'],
                        'postcode': exchange_property['postcode'],
                        'geotype': exchange_property['geotype'],
                        'prems_over': exchange_property['prems_over'],
                        'prems_under': exchange_property['prems_under'],
                    }
                })

    return output

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

#####################################################################################
# 4) generate single set of postcode areas from postcode sectors
#####################################################################################

"""Fix up a shapefile with slivers, islands
- keep only polygon exteriors (drop holes)
- keep only polygons (or parts of multipolygons) above an area threshold

e.g. run after a dissolve operation:
    ogr2ogr output.shp postcode_sectors.shp -dialect sqlite \
        -sql "SELECT ST_Union(geometry), postcode_area FROM _postcode_sectors \
            GROUP BY postcode_area"
"""

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

#####################################################################################
# 5) remove verticals from postcode areas and write out individually
#####################################################################################

pathlist = glob.iglob(os.path.join(BASE_PATH, 'raw', 'd_shapes', 'codepoint', 'codepoint-poly_2429451/**/*.shp'), recursive=True)

def remove_verticals(path):
    # Initialze Rtree
    idx = index.Index()

    # Initialize output dir
    output_dir = os.path.join(BASE_PATH, 'raw', 'd_shapes', 'individual_postcode_areas_no_verticals')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with fiona.open(path, 'r') as source:

        sink_schema = source.schema.copy()

        # Store shapes in Rtree
        for src_shape in source:
            idx.insert(int(src_shape['id']), shape(src_shape['geometry']).bounds, src_shape)

        # Open output file
        with fiona.open(
                os.path.join(output_dir,os.path.basename(path)), 'w',
                crs=source.crs,
                driver=source.driver,
                schema=sink_schema,
                ) as sink:

            print(sink_schema)

            # Split list in regular and vertical postcodes
            postcodes = {}
            vertical_postcodes = {}

            for x in source:

                if x['properties']['POSTCODE'].startswith('V'):
                    vertical_postcodes[x['id']] = x
                else:
                    postcodes[x['id']] = x

            for key, f in vertical_postcodes.items():

                vpost_geom = shape(f['geometry'])
                best_neighbour = {'id': 0, 'intersection': 0}

                # Find best neighbour
                for n in idx.intersection((vpost_geom.bounds), objects=True):
                    if shape(n.object['geometry']).intersection(vpost_geom).length > best_neighbour['intersection'] and n.object['id'] != f['id']:
                        best_neighbour['id'] = n.object['id']
                        best_neighbour['intersection'] = shape(n.object['geometry']).intersection(vpost_geom).length

                # Merge with best neighbour
                neighbour = postcodes[best_neighbour['id']]
                merged_geom = unary_union([shape(neighbour['geometry']), vpost_geom])

                merged_postcode = {
                    'id': neighbour['id'],
                    'properties': neighbour['properties'],
                    'geometry': mapping(merged_geom)
                }

                try:
                    postcodes[merged_postcode['id']] = merged_postcode
                except:
                    print('print(f)')
                    print(f)
                    print('print(neighbour)')
                    print(neighbour)
                    print('print(merged_postcode)')
                    print(merged_postcode)
                    raise Exception

            for key, p in tqdm(postcodes.items()):
                sink.write(p)

#####################################################################################
# 6) intersect postcode_areas with exchanges to get exchange_to_pcd_area_lut
#####################################################################################

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

#####################################################################################
# 8) read premises by exchange and export
#####################################################################################

def get_lad_area_ids(exchange_name):
    """Read in existing exchange to lad lookup table

    Returns
    ------
    string
        lad values as strings
    """
    lad_area_ids = []

    dirname = os.path.join(DATA_INTERMEDIATE, 'lut_exchange_to_lad')
    pathlist = glob.iglob(dirname + '/*.csv', recursive=True)
    filename = os.path.join(DATA_INTERMEDIATE, 'lut_exchange_to_lad', 'ex_to_lad_' + exchange_name + '.csv')

    for path in pathlist:
        if path == filename:
            with open(path, 'r') as system_file:
                reader = csv.reader(system_file)
                for line in reader:
                    lad_area_ids.append(line[0])

    unique_lads = list(set(lad_area_ids))

    return unique_lads

def read_premises_data(exchange_area):

    prepared_area = prep(shape(exchange_area['geometry']))

    lads = get_lad_area_ids(exchange_area['properties']['id'].replace("/", ""))

    def premises():
        i = 0
        for lad in lads:
            directory = os.path.join(DATA_BUILDING_DATA, 'prems_by_lad', lad)
            pathlist = glob.iglob(directory + '/*.csv', recursive=True)
            for path in pathlist:
                with open(path, 'r') as system_file:
                    reader = csv.DictReader(system_file)
                    for line in reader:
                        geom = loads(line['geom'])
                        geom_point = geom.representative_point()
                        feature = {
                            'type': 'Feature',
                            'geometry': mapping(geom),
                            'representative_point': geom_point,
                            'properties':{
                                #'landparcel_id': line[0],
                                #'mistral_function': line[1],
                                'toid': line['toid'],
                                #'household_id': line[4],
                                #'res_count': line[6],
                                #'lad': line[13],
                                'oa': line['oa'],
                            }
                        }
                        yield (i, geom_point.bounds, feature)
                        i += 1
    output = []

    try:
        idx = index.Index(premises())

        for n in idx.intersection((shape(exchange_area['geometry']).bounds), objects=True):
            point = n.object['representative_point']
            if prepared_area.contains(point):
                del n.object['representative_point']
                output.append(n.object)

    except:
        print('{} failed'.format(exchange_area['properties']['id']))

    return output

def write_premises_shapefile(data, path):

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

    # Write all elements to output file
    with fiona.open(path, 'w', driver=sink_driver, crs=sink_crs, schema=sink_schema) as sink:
        [sink.write(feature) for feature in data]

def read_premises_by_exchange(exchange_areas):

    for exchange in exchange_areas:
        exchange_id = exchange['properties']['id'].replace("/", "")
        PATH = os.path.join(DATA_INTERMEDIATE, 'premises_by_exchange', exchange_id + '.shp')
        if not os.path.isfile(PATH):
            premises = read_premises_data(exchange)
            print('prems {} {}'.format(len(premises), exchange_id))
            if len(premises) > 0:
                write_premises_shapefile(premises, PATH)
            else:
                print('{} was empty'.format(exchange_id))
        else:
            continue

    return print('completed read_premises_by_exchange')

#####################################################################################
# 9) find problem exchanges and export
#####################################################################################

def find_problem_exchanges(exchange_areas):

    missing = []

    for exchange in exchange_areas:
        exchange_id = exchange['properties']['id'].replace("/", "")

        PATH = os.path.join(DATA_INTERMEDIATE, 'premises_by_exchange', exchange_id + '.shp')

        if not os.path.isfile(PATH):
            try:
                missing.append({
                    'problem_exchange': exchange_id
                    })
            except:
                print('problem with {}'.format(exchange_id))
        else:
            pass
    print('completed find_problem_exchanges')

    missing_output = defaultdict(list)

    for exchange in missing:
        missing_output['problem_exchange'].append({
            'problem_exchange': exchange['problem_exchange']
            })

    return missing_output

def get_problem_exchange_shapes(exchange_areas, problem_exchanges):

    output_shapes = []

    for exchange in exchange_areas:
        for value in problem_exchanges.values():
            for v in value:
                if exchange['properties']['id'] == v['problem_exchange']:
                    output_shapes.append({
                        'type': exchange['type'],
                        'geometry': exchange['geometry'],
                        'properties': exchange['properties']
                    })

    return output_shapes

def write_single_exchange_shapefile(data, path):

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

    # Write all elements to output file
    with fiona.open(path, 'w', driver=sink_driver, crs=sink_crs, schema=sink_schema) as sink:
        [sink.write(feature) for feature in data]

#####################################################################################
# 10) get OA to exchange LUT and export
#####################################################################################

def read_premises(path):
    """Read all shapes

    Yields
    ------
    premises : iterable[dict]
    """
    with fiona.open(path, 'r') as source:
        for feature in source:
            yield feature

def get_oa_to_exchange_lut(exchange_areas):
    """
    Get a set of Ouput Areas by Exchange Area

    """
    unique_lad_to_oa_lut = defaultdict(set)
    missing_exchanges = []

    for exchange in exchange_areas:

        exchange_id = exchange['properties']['id']
        PATH = os.path.join(DATA_INTERMEDIATE, 'premises_by_exchange', exchange_id + '.shp')

        if os.path.isfile(PATH):
            premises = read_premises(PATH)
            for premise in premises:
                unique_lad_to_oa_lut[exchange_id].add(premise['properties']['oa'])

        else:
            print('could not find {}'.format(os.path.basename(PATH)))
            missing_exchanges.append(exchange)
            pass

    output_lut = defaultdict(list)

    for key, values in unique_lad_to_oa_lut.items():
        output_values = []
        for value in values:
            output_values.append({
                'oa': value})
        for value in output_values:
            output_lut[key].append(value)

    print('completed get_oa_to_exchange_lut')

    return output_lut, missing_exchanges

#####################################################################################
# Write out data
#####################################################################################

def write_to_csv(data, folder, file_prefix, fieldnames):
    """
    Write data to a CSV file path

    """
    # Create path
    directory = os.path.join(DATA_INTERMEDIATE, folder)
    if not os.path.exists(directory):
        os.makedirs(directory)

    try:
        for key, value in data.items():
            print('finding prem data for {}'.format(key))
            filename = key.replace("/", "")

            if len(value) > 0:
                with open(os.path.join(directory, file_prefix + filename + '.csv'), 'w') as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames, lineterminator = '\n')
                    writer.writerows(value)
            else:
                pass
    except:
        print('problem writing {}'.format(folder))
###############################################################################

# #Run functions
# # 1) generate unique postcode to exchange lut and export as one .csv per exchange
# pcd_to_exchange_data = read_pcd_to_exchange_lut()
# pcd_to_exchange_data = get_unique_postcodes_by_exchanges(pcd_to_exchange_data)
# fieldnames = ['postcode']
# write_to_csv(pcd_to_exchange_data, 'lut_pcd_to_exchange', 'pcd_to_ex_', fieldnames)

# # 2) generate unique postcode to cabinet lut and export as one .csv per exchange
# pcd_to_cabinet_data = read_pcd_to_cabinet_lut()
# pcd_to_cabinet_data = get_unique_postcodes_to_cabs_by_exchange(pcd_to_cabinet_data)
# fieldnames = ['postcode','cabinet','exchange_only_flag']
# write_to_csv(pcd_to_cabinet_data, 'lut_pcd_to_cabinet_by_exchange', 'pcd_to_cab_', fieldnames)

# # 3) add necessary properties (postcode) to exchange polygons
exchange_areas = read_exchange_areas()

# exchange_properties = load_exchange_properties()
# exchange_areas = add_properties_to_exchanges(exchange_areas, exchange_properties)
# write_shapefile(exchange_areas, 'individual_exchange_areas', 'id')

# 4) generate single set of postcode areas from postcode sectors
run_postcode_area_generation()

# # 5) remove verticals from postcode areas and write out individually
# for path in pathlist:
#     remove_verticals(path)
#     print('completed {}'.format(os.path.basename(path)))

# # 6) intersect postcode_areas with exchanges to get exchange_to_pcd_area_lut
# postcode_areas = read_postcode_areas()
# lut = intersect_pcd_areas_and_exchanges(exchange_areas, postcode_areas)
# fieldnames = ['postcode_area']
# write_to_csv(lut, 'lut_exchange_to_pcd_area', 'ex_to_pcd_area_', fieldnames)

# # 7) intersect lad_areas with exchanges to get exchange_to_lad_area_lut
# lad_areas = read_lad_areas()
# lut = intersect_lad_areas_and_exchanges(exchange_areas, lad_areas)
# fieldnames = ['lad']
# write_to_csv(lut, 'lut_exchange_to_lad', 'ex_to_lad_', fieldnames)
# write_shapefile(lad_areas, 'individual_lad_areas', 'name')

# 8) get premises by exchange

# def yield_single_exchange(exchange_id):

#     for exchange in exchange_areas:
#         if exchange['properties']['id'] == exchange_id:
#             yield exchange

# # # 8) read premises by exchange and export
# read_premises_by_exchange(exchange_areas)

# # 9) find problem exchanges and export
# problem_exchanges = find_problem_exchanges(exchange_areas)
# fieldnames = ['problem_exchange']
# write_to_csv(problem_exchanges, 'problem_exchanges', '', fieldnames)
# problem_exchange_shapes = get_problem_exchange_shapes(exchange_areas, problem_exchanges)
# PC_OUT_PATH = os.path.join(DATA_INTERMEDIATE, 'problem_exchanges', 'problem_exchanges_2.shp')
# write_single_exchange_shapefile(problem_exchange_shapes, PC_OUT_PATH)

# # 10) get OA to exchange LUT and export
# oa_to_ex_lut, missing_exchanges = get_oa_to_exchange_lut(exchange_areas)
# fieldnames = ['oa']
# write_to_csv(oa_to_ex_lut, 'oa_to_ex_lut', '', fieldnames)
# write_shapefile(missing_exchanges, 'missing_exchanges', 'id')
# fieldnames = ['missing_exchanges']
# write_to_csv(missing_exchanges, 'missing_exchanges', '', fieldnames)

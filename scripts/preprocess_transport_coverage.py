import os
from pprint import pprint
import configparser
import csv
import fiona
import numpy as np

from itertools import groupby
from operator import itemgetter

from rtree import index
from shapely.geometry import shape, Point, LineString, Polygon, mapping
from collections import OrderedDict, defaultdict
from pyproj import Proj, transform

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

#####################################
# SETUP FILE LOCATIONS
#####################################

SYSTEM_INPUT_FIXED = os.path.join(BASE_PATH, 'raw')
SYSTEM_OUTPUT_FILENAME = os.path.join(BASE_PATH, 'processed')

#####################################
# IMPORT SUPPLY SIDE DATA
#####################################

def read_in_traffic_counts():

    traffic_data = []

    TRAFFIC_COUNT_INPUTS = os.path.join(SYSTEM_INPUT_FIXED,'dft_road_traffic_counts', 'all_regions')

    for x in os.listdir(TRAFFIC_COUNT_INPUTS):
        with open(os.path.join(TRAFFIC_COUNT_INPUTS, x), 'r', encoding='utf8', errors='replace') as system_file:
            reader = csv.DictReader(system_file)
            next(reader)
            for line in reader:
                try:
                    if line['AADFYear'] == '2016': 
                        traffic_data.append({
                            'road': line['Road'],
                            'count': line['AllMotorVehicles'],
                            'easting': line['Easting'],
                            'northing': line['Northing']
                        })
                except:
                    print(x)
                else:
                    if line['AADFYear'] == '2015': 
                        traffic_data.append({
                            'road': line['Road'],
                            'count': line['AllMotorVehicles'],
                            'easting': line['Easting'],
                            'northing': line['Northing']
                        })

    with open(os.path.join(SYSTEM_INPUT_FIXED,'dft_road_traffic_counts','minor_roads','aadt_minor_roads.csv'), 'r', encoding='utf8', errors='replace') as system_file:
        reader = csv.DictReader(system_file)
        next(reader)
        for line in reader:
            if line['AADFYear'] == '2016':
                traffic_data.append({
                    'road': line['Road'],
                    'count': line['FdAll_MV'],
                    'easting': line['S Ref Longitude'],
                    'northing': line['S Ref Latitude']
                })

    return traffic_data


def find_average_count(data):

    roads_by_road_name = defaultdict(list)

    for road in data:
    
        roads_by_road_name[road['road']].append(road)

    average_count = defaultdict(dict)

    for road in roads_by_road_name.keys():
        summed_count = sum([int(road['count']) for road in roads_by_road_name[road]])
        number_of_count_points = len(roads_by_road_name[road]) 
        
        average_count[road] = {
            'average_count': round(summed_count / number_of_count_points, 0),
            'summed_count': summed_count
        }

    return average_count


def covert_data_into_list_of_dicts(data, variable1, variable2, variable3):
    my_data = []

    # output and report results for this timestep
    for datum in data:
        my_data.append({
        variable1: datum,
        variable2: data[datum][variable2],
        variable3: data[datum][variable3]
        })

    return my_data


def apply_road_categories(data):

    for point in data:

        if int(point['average_count']) >= 17000:
            point['geotype'] = 'high demand'

        elif int(point['average_count']) >= 10000 and int(point['average_count']) < 17000:
            point['geotype'] = 'moderate demand'

        elif int(point['average_count']) < 10000  :
            point['geotype'] = 'low demand'
    
    return data


def read_in_os_open_roads():

    open_roads_network = []

    DIR = os.path.join(SYSTEM_INPUT_FIXED, 'os_open_roads', 'open-roads_2443825')

    for my_file in os.listdir(DIR):
        if my_file.endswith("RoadLink.shp"):
            with fiona.open(os.path.join(DIR, my_file), 'r') as source:

                for src_shape in source:   
                    #open_roads_network.extend([src_shape for src_shape in source if src_shape['properties']['function'] == 'Motorway' or src_shape['properties']['function'] == 'A Road' or src_shape['properties']['function'] == 'B Road']) 
                    open_roads_network.extend([src_shape for src_shape in source]) 
                    for element in open_roads_network:

                        if element['properties']['name1'] in element['properties']:
                            del element['properties']['name1']
                        else:
                            pass 

                        if element['properties']['name1_lang'] in element['properties']:
                            del element['properties']['name1_lang']
                        else:
                            pass 

                        if element['properties']['name2'] in element['properties']:
                            del element['properties']['name2']
                        else:
                            pass 

                        if element['properties']['name2_lang'] in element['properties']:
                            del element['properties']['name2_lang']
                        else:
                            pass 

                        if element['properties']['structure'] in element['properties']:
                            del element['properties']['structure']
                        else:
                            pass 

                        if element['properties']['nameTOID'] in element['properties']:
                            del element['properties']['nameTOID']
                        else:
                            pass 

                        if element['properties']['numberTOID'] in element['properties']:
                            del element['properties']['numberTOID']
                        else:
                            pass 

    return open_roads_network

def read_in_built_up_areas():

    built_up_area_polygon_data = []

    with fiona.open(os.path.join(SYSTEM_INPUT_FIXED, 'built_up_areas', 'Builtup_Areas_December_2011_Boundaries_V2_england_and_wales', 'urban_areas_england_and_wales.shp'), 'r') as source:
        for src_shape in source:           
            built_up_area_polygon_data.extend([src_shape for src_shape in source]) 

    with fiona.open(os.path.join(SYSTEM_INPUT_FIXED, 'built_up_areas', 'shapefiles-mid-2016-settlements-localities_scotland', 'urban_areas.shp'), 'r') as source:
        for src_shape in source:           
            built_up_area_polygon_data.extend([src_shape for src_shape in source]) 

    return built_up_area_polygon_data


def convert_projection(data):

    converted_data = []

    projOSGB1936 = Proj(init='epsg:27700')
    projWGS84 = Proj(init='epsg:4326')

    for feature in data:

        new_geom = []
        coords = feature['geometry']['coordinates']

        for coordList in coords:
            

            coordList = list(transform(projOSGB1936, projWGS84, coordList[0], coordList[1]))

            new_geom.append(coordList)
               
        feature['geometry']['coordinates'] = new_geom

        converted_data.append(feature)
        
    return converted_data

def add_urban_rural_indicator_to_roads(road_data, built_up_polygons): 

    joined_road_data = []

    # Initialze Rtree
    idx = index.Index()

    for rtree_idx, road in enumerate(road_data):
        idx.insert(rtree_idx, shape(road['geometry']).bounds, road)
    
    # Join the two
    for area in built_up_polygons:
        for n in idx.intersection((shape(area['geometry']).bounds), objects=True):  
            urban_area_shape = shape(area['geometry'])
            urban_shape = shape(n.object['geometry'])
            if urban_area_shape.contains(urban_shape):
                n.object['properties']['urban_rural_indicator'] = 'urban'
                joined_road_data.append(n.object)

            else:
                n.object['properties']['urban_rural_indicator'] = 'rural'
                joined_road_data.append(n.object) 

    return joined_road_data


def extract_geojson_properties(data):
    
    my_data = []

    for item in data:
        my_data.append({
            'road': item['properties']['roadNumber'],
            'formofway': item['properties']['formOfWay'], 
            'length': item['properties']['length'],
            'function': item['properties']['function'], 
            'urban_rural_indicator': item['properties']['urban_rural_indicator'],         
        })

    return my_data


def deal_with_none_values(data):

    my_data = []

    for road in data:
        if road['road'] == None:
            my_data.append({
                'road': road['function'],
                'formofway': road['formofway'],    
                'length': road['length'],
                'function': road['function'],   
                'urban_rural_indicator': road['urban_rural_indicator']      
        })
        else:
            my_data.append({
                'road': road['road'],
                'formofway': road['formofway'],    
                'length': road['length'],
                'function': road['function'],    
                'urban_rural_indicator': road['urban_rural_indicator']         
        })
    
    return my_data


def grouper(data, aggregated_metric, group_item1, group_item2, group_item3, group_item4):

    my_grouper = itemgetter(group_item1, group_item2, group_item3, group_item4)
    result = []
    for key, grp in groupby(sorted(data, key = my_grouper), my_grouper):
        try:
            temp_dict = dict(zip([group_item1, group_item2, group_item3, group_item4], key))
            temp_dict[aggregated_metric] = sum(int(item[aggregated_metric]) for item in grp)
            result.append(temp_dict)
        except:
            pass
    
    return result


def aggregator(data, aggregated_metric, group_item1, group_item2, group_item3):

    my_grouper = itemgetter(group_item1, group_item2, group_item3)
    result = []
    for key, grp in groupby(sorted(data, key = my_grouper), my_grouper):
        try:
            temp_dict = dict(zip([group_item1, group_item2, group_item3], key))
            temp_dict[aggregated_metric] = sum(int(item[aggregated_metric]) for item in grp)
            result.append(temp_dict)
        except:
            pass
    
    return result


def merge_two_list_of_dicts(data1, data2, shared_id):

    d1 = {d[shared_id]:d for d in data1}

    result = [dict(d, **d1.get(d[shared_id], {})) for d in data2]

    return result


#####################################
# WRITE LOOK UP TABLE (LUT) DATA
#####################################

def csv_writer(data, output_fieldnames, filename):
    """
    Write data to a CSV file path
    """
    fieldnames = data[0].keys()
    with open(os.path.join(SYSTEM_OUTPUT_FILENAME, filename),'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames, lineterminator = '\n')
        writer.writeheader()
        writer.writerows(data)


def write_shapefile(data, path):

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

    with fiona.open(os.path.join(SYSTEM_OUTPUT_FILENAME, path), 'w', driver=sink_driver, crs=sink_crs, schema=sink_schema) as sink:
        for datum in data:
            sink.write(datum)

#####################################
# RUN SCRIPTS
#####################################

# print("read in traffic flow data")
# flow_data = read_in_traffic_counts()

# print("calculating average count per road")
# average_flow_data = find_average_count(flow_data)

# print("converting to list of dicts structure")
# average_flow_data = covert_data_into_list_of_dicts(average_flow_data, 'road', 'average_count', 'summed_count') 

# print("categorising flow data")
# average_flow_data = apply_road_categories(average_flow_data)

print('read in road network')
road_network = read_in_os_open_roads()

print('converting road network projection into wgs84')
road_network = convert_projection(road_network)

print('read in built up area polygons')
built_up_areas = read_in_built_up_areas()

print('add built up area indicator to urban roads')
road_network = add_urban_rural_indicator_to_roads(road_network, built_up_areas)

print("extracting geojson properties")
aggegated_road_statistics = extract_geojson_properties(road_network)

print("add any missing items")
aggegated_road_statistics = deal_with_none_values(aggegated_road_statistics)   

print("applying grouped aggregation")
aggegated_road_statistics = grouper(aggegated_road_statistics, 'length', 'road', 'function', 'formofway', 'urban_rural_indicator')

print('write all road statistics')
road_statistics_fieldnames = ['road', 'function', 'formofway', 'length', 'urban_rural_indicator']
csv_writer(aggegated_road_statistics, road_statistics_fieldnames, 'aggregated_road_statistics.csv')

print("applying aggregation to road types")
road_length_by_type = aggregator(aggegated_road_statistics, 'length', 'function', 'formofway', 'urban_rural_indicator')

print('write road lengths')
road_statistics_fieldnames = ['road', 'function', 'formofway', 'length', 'urban_rural_indicator']
csv_writer(road_length_by_type, road_statistics_fieldnames, 'road_length_by_type.csv')

# print("merging road network stats with flow estimates")
# average_flow_statistics = merge_two_list_of_dicts(aggegated_road_statistics, average_flow_data, 'road')

# print('write average flow statistics')
# road_statistics_fieldnames = ['road', 'average_count', 'geotype', 'function', 'length']
# csv_writer(average_flow_statistics, road_statistics_fieldnames, 'average_road_statistics.csv')

print("script finished")

print("now check the column integer slices were correct for desired columns")

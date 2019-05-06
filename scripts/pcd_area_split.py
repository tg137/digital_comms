"""Split postcode areas to single feature per file

Run this after pcd_area_fix_up.py.
"""
import configparser
import os
import re
from collections import OrderedDict

import fiona
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from tqdm import tqdm


def main(base_path):
    input_filename = os.path.join(
        base_path, 'raw', 'd_shapes', 'postcode_areas', '_postcode_areas_fixed_up.shp')
    output_dirname = os.path.join(
        base_path, 'raw', 'd_shapes', 'postcode_areas')

    areas = read(input_filename)
    write(output_dirname, (pcd for pcd in tqdm(areas)))


def read(filename):
    with fiona.open(filename, 'r') as source:
        for feature in source:
            yield feature


def get_filename(feature, dirname):
    return os.path.join(dirname, "{}.shp".format(feature['properties']['pcd_area'].lower()))


def write(dirname, features):
    driver = 'ESRI Shapefile'
    crs = {'init': 'epsg:27700'}
    schema = {
        'geometry': 'Polygon',
        'properties': {
            'pcd_area': 'str'
        }
    }
    for feature in features:
        filename = get_filename(feature, dirname)
        with fiona.open(filename, 'w', driver=driver, crs=crs, schema=schema) as sink:
            sink.write(feature)


if __name__ == '__main__':
    CONFIG = configparser.ConfigParser()
    CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
    BASE_PATH = CONFIG['file_locations']['base_path']
    main(BASE_PATH)

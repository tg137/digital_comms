"""Add area column to postcode sectors

Run this first:
1. * pcd_sector_add_area.py
2. pcd_sector_group_to_area.sh
3. pcd_area_fix_up.py

"""
import configparser
import os
import re
from collections import OrderedDict

import fiona
from tqdm import tqdm


def main(base_path):
    input_filename = os.path.join(
        base_path, 'raw', 'd_shapes', 'postcode_sectors', '_postcode_sectors.shp')
    output_filename = os.path.join(
        base_path, 'raw', 'd_shapes', 'postcode_sectors', '_postcode_sectors_with_area.shp')

    postcodes = read(input_filename)
    write(output_filename, (transform(pcd) for pcd in tqdm(postcodes)))


def transform(feature):
    """Transform each feature - add pcd_area property with the first one or two alphabetical
    characters of the postcode (sector)
    """
    return {
        'geometry': feature['geometry'],
        'properties': {
            'pcd_sector': feature['properties']['postcode'],
            'pcd_area': get_postcode_area(feature['properties']['postcode'])
        }
    }


def get_postcode_area(postcode):
    match = re.search('^[A-Z]+', postcode)
    if match:
        return match.group(0)


def read(filename):
    with fiona.open(filename, 'r') as source:
        for feature in source:
            yield feature


def write(filename, features):
    driver = 'ESRI Shapefile'
    crs = {'init': 'epsg:27700'}
    schema = {
        'geometry': 'Polygon',
        'properties': {
            'pcd_sector': 'str',
            'pcd_area': 'str'
        }
    }
    with fiona.open(filename, 'w', driver=driver, crs=crs, schema=schema) as sink:
        for feature in features:
            sink.write(feature)


if __name__ == '__main__':
    CONFIG = configparser.ConfigParser()
    CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
    BASE_PATH = CONFIG['file_locations']['base_path']
    main(BASE_PATH)

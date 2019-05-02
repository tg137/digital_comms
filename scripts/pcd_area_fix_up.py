"""Fix up postcode areas - drop holes and small multipolygon parts


Run this third:
1. pcd_sector_add_area.py
2. pcd_sector_group_to_area.sh
3. * pcd_area_fix_up.py
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
        base_path, 'raw', 'd_shapes', 'postcode_areas', '_postcode_areas.shp')
    output_filename = os.path.join(
        base_path, 'raw', 'd_shapes', 'postcode_areas', '_postcode_areas_fixed_up.shp')

    areas = read(input_filename)
    drop_threshold = 1e6
    write(
        output_filename,
        (transform(pcd, drop_threshold) for pcd in tqdm(areas))
    )


def transform(feature, threshold):
    """Transform each feature - drop holes and small multipolygon parts
    """
    geom = shape(feature['geometry'])
    geom = drop_holes(geom)
    geom = drop_small_multipolygon_parts(geom, threshold)
    return {
        'geometry': mapping(geom),
        'properties': {
            'pcd_area': feature['properties']['pcd_area']
        }
    }


def drop_small_multipolygon_parts(geom, threshold_area):
    if geom.type == 'MultiPolygon':
        return MultiPolygon(
            p
            for p in geom.geoms
            if p.area > threshold_area
        )
    return geom


def drop_holes(geom):
    if geom.type == 'Polygon':
        return Polygon(geom.exterior)
    if geom.type == 'MultiPolygon':
        return MultiPolygon(Polygon(p.exterior) for p in geom.geoms)
    return geom


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

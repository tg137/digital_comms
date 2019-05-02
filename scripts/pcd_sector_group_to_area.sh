#!/usr/bin/env bash

#
# Merge postcode sector polygons on pcd_area attribute
#
# Run this second:
# 1. pcd_sector_add_area.py
# 2. * pcd_sector_group_to_area.sh
# 3. pcd_area_fix_up.py

# use first and second arguments passed to this script
# e.g. usage:
#  group_by_pcd_area.sh ./path/to/_postcode_sectors_with_area.shp ./path/to/_postcode_areas.shp

input_filename=$1  # ./path/to/_postcode_sectors_with_area.shp
output_filename=$2  # ./path/to/_postcode_areas.shp

ogr2ogr \
    $output_filename \
    $input_filename  \
    -dialect sqlite \
    -sql "SELECT ST_Union(geometry), pcd_area FROM _postcode_sectors_with_area GROUP BY pcd_area"

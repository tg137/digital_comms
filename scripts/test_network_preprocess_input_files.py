from pprint import pprint

import numpy as np
import osmnx as ox

from pytest import fixture
from pyproj import Proj, transform

from .network_preprocess_input_files import *


@fixture
def street_graph():
    point = (52.180918, 0.093319)  # center  lat,lng
    return ox.graph_from_point(point, distance=500, network_type='all')


@fixture
def area_feature():
    return {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [0.0905, 52.179], [0.0978, 52.179], [0.0978, 52.184],
                [0.0905, 52.184], [0.0905, 52.179]
            ]]
        }
    }


@fixture
def destination_features():
    return [
        {
            "type": "Feature",
            "properties": {"id": "destination"},
            "geometry": {"type": "Point", "coordinates": [0.0933, 52.1809]}
        }
    ]


@fixture
def origin_features():
    return [
        {
            "type": "Feature",
            "properties": {"id":"a", "connection": "destination"},
            "geometry": {"type": "Point", "coordinates": [0.0914, 52.1818]}
        },
        {
            "type": "Feature",
            "properties": {"id":"b", "connection": "destination"},
            "geometry": {"type": "Point", "coordinates": [0.0925, 52.1813]}
        }
    ]


def test_snap_point_to_graph(street_graph):
    x, y = (0.094239, 52.182635)
    expected_x, expected_y = (0.094054, 52.1826791)
    actual_x, actual_y = snap_point_to_graph(x, y, street_graph)

    actual = np.array([actual_x, actual_y])
    expected = np.array([expected_x, expected_y])
    print("Actual:", actual)
    print("Expected:", expected)
    np.testing.assert_allclose(actual, expected, atol=1e-06)


def test_steiner_tree(origin_features, destination_features, area_feature):
    destination_features = [feature_to_osgb(f) for f in destination_features]
    origin_features = [feature_to_osgb(f) for f in origin_features]
    area_feature = feature_to_osgb(area_feature)
    links, junctions = generate_link_steiner_tree(
        origin_features, destination_features, area_feature)

    pprint(junctions)
    assert len(junctions) == 5  # 5 tree nodes
    pprint(links)
    assert len(links) == 7  # 4 tree edges plus 3 terminal

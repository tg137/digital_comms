"""Test Path Loss Calculations
"""

import pytest
from digital_comms.mobile_network.path_loss_calculations import path_loss_calc_module

@pytest.mark.parametrize("frequency, distance, ant_height, ant_type, settlement_type, type_of_sight, ue_height, expected", [
    (3.5,1000,10,'micro','urban','los',1.5, 108),
    (3.5,1000,10,'micro','urban','nlos',1.5, 147),
    (3.5,1000,25,'macro','urban','los',1.5, 101),
    (3.5,1000,25,'macro','urban','nlos',1.5, 142),
    (3.5,1000,25,'macro','suburban','los',1.5, 101),
    (3.5,1000,25,'macro','suburban','nlos',1.5, 142),
    (3.5,1000,25,'macro','rural','los',1.5, 101),
    (3.5,1000,25,'macro','rural','nlos',1.5, 142),
])

def test_eval(frequency, distance, ant_height, ant_type, settlement_type, type_of_sight, ue_height, expected):
    assert (path_loss_calc_module(frequency, distance, ant_height, ant_type, settlement_type, type_of_sight, ue_height)) == expected

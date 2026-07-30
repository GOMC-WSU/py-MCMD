import sys
sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")

from utils.path import zero_prefix, format_cycle_id

def test_zero_prefix_legacy_behavior():
    assert zero_prefix(1, 10) == "000000000"
    assert zero_prefix(123, 5) == "00"
    assert zero_prefix(12345, 5) == ""
    assert zero_prefix(123456, 5) == ""

def test_format_cycle_id():
    assert format_cycle_id(1, 10) == "0000000001"
    assert format_cycle_id(123, 5) == "00123"
    assert format_cycle_id(0, 4) == "0000"

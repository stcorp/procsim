'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex mission constants.
'''

import datetime

SATELLITE_ID = 'FLX'
ORBIT0_START = datetime.datetime(2021, 1, 1, 0, 0, 0)    # Just an arbitrary value, to calculate orbit numbers
ORBITAL_PERIOD = datetime.timedelta(0, 5890.98007989)
ABS_ORBIT = '12345'
SLICE_GRID_SPACING = datetime.timedelta(0, 95)  # TODO check value
SLICE_OVERLAP_START = datetime.timedelta(0, 5.0)
SLICE_OVERLAP_END = datetime.timedelta(0, 7.0)
SLICE_MINIMUM_DURATION = datetime.timedelta(0, 0.0)

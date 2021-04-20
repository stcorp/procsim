'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass mission constants.
'''

import datetime

SATELLITE_ID = 'BIO'
ORBIT0_START = datetime.datetime(2021, 1, 1, 0, 0, 0)    # Just an arbitrary value, to calculate orbit numbers
ORBITAL_PERIOD = datetime.timedelta(0, 5890.98007989)
FRAME_GRID_SPACING = datetime.timedelta(0, 19.00316155)
FRAME_OVERLAP = datetime.timedelta(0, 2.0)
FRAME_LOWER_BOUND = datetime.timedelta(0, 8.0)
SLICE_GRID_SPACING = 5 * FRAME_GRID_SPACING
SLICE_OVERLAP_START = datetime.timedelta(0, 5.0)
SLICE_OVERLAP_END = datetime.timedelta(0, 7.0)

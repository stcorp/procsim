'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass mission constants.
'''

import datetime

SATELLITE_ID = 'BIO'
ORBIT0_START = datetime.datetime(2021, 1, 1, 0, 0, 0)    # Just an arbitrary value
ORBIT_DURATION = datetime.timedelta(0, 5890.98)
SLICE_DURATION = datetime.timedelta(0, 19.003)
COMPACT_DATE_EPOCH = datetime.datetime(2000, 1, 1, 0, 0, 0)

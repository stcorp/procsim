'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import os
import unittest

from biomass.main_product_header import MainProductHeader

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_MPH_FILE = 'bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_01_acz976.xml'

VALIDITY_START = datetime.datetime(2023, 1, 1, 12, 0)
VALIDITY_STOP = datetime.datetime(2023, 1, 1, 12, 0, 21)
DATA_TAKE_ID = 1234
MISSION_PHASE = 'INTERFEROMETRIC'


class MphTest(unittest.TestCase):
    def testParse(self):
        mph = MainProductHeader()
        mph.parse(os.path.join(THIS_DIR, TEST_MPH_FILE))
        self.assertEqual(mph._validity_start, VALIDITY_START)
        self.assertEqual(mph._validity_stop, VALIDITY_STOP)
        self.assertEqual(mph.acquisitions[0].data_take_id, DATA_TAKE_ID)
        self.assertEqual(mph.acquisitions[0].mission_phase, MISSION_PHASE)

    def testCreate(self):
        # TODO: Parse, re-write and compare mph structure (or even the files?)
        pass


if __name__ == '__main__':
    unittest.main()

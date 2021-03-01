'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import unittest
from typing import List

from biomass.product_name import ProductName


class _TestData():
    def __init__(self, level, dir, bin, type, start, stop, create, baseline, downlink,
                 mission_phase=None, global_coverage_id=None, major_cycle_id=None, repeat_cycle_id=None,
                 track_nr=None, frame_nr=None, suffix=None):
        self.level = level
        self.dir = dir
        self.bin = bin
        self.mph = dir.lower() + '.xml'
        self.type = type
        self.start = start
        self.stop = stop
        self.create = create
        self.baseline = baseline
        self.downlink = downlink
        self.mission_phase = mission_phase
        self.global_coverage_id = global_coverage_id
        self.major_cycle_id = major_cycle_id
        self.repeat_cycle_id = repeat_cycle_id
        self.track_nr = track_nr
        self.frame_nr = frame_nr
        self.suffix = suffix


_TEST_DATA: List[_TestData] = [
    _TestData(
        'raw',
        'BIO_RAW_022_10_20210201T000000_20210201T013810_D20210201T013811_01_B07390',
        'bio_raw_022_10_20210201t000000_20210201t013810_d20210201t013811.dat',
        'RAW_022_10',
        datetime.datetime(2021, 2, 1, 0, 0, 0),
        datetime.datetime(2021, 2, 1, 1, 38, 10),
        datetime.datetime(2021, 2, 1, 1, 39, 0),
        1,
        datetime.datetime(2021, 2, 1, 1, 38, 11)
    ),
    _TestData(
        'raw',
        'BIO_RAWS025_10_20210201T000000_20210201T013810_D20210201T013811_01_B07390',
        'bio_raws025_10_20210201t000000_20210201t013810_d20210201t013811.dat',
        'RAWS025_10',
        datetime.datetime(2021, 2, 1, 0, 0, 0),
        datetime.datetime(2021, 2, 1, 1, 38, 10),
        datetime.datetime(2021, 2, 1, 1, 39, 0),
        1,
        datetime.datetime(2021, 2, 1, 1, 38, 11)
    ),
    _TestData(
        # L0 Standard
        'l0',
        'BIO_S3_RAW__0S_20230101T120000_20230101T120147_I_G03_M03_C03_T022_F061_01_AFRS00',
        'bio_s3_raw__0s_20230101t120000_20230101t120147_i_g03_m03_c03_t022_f061_rxh.dat',
        'S3_RAW__0S',
        datetime.datetime(2023, 1, 1, 12, 0, 0),
        datetime.datetime(2023, 1, 1, 12, 1, 47),
        datetime.datetime(2020, 1, 1, 0, 0, 0),
        1,
        None,
        'Interferometric', '03', '03', '03', '022', 61,
        '_rxh'
    ),
    _TestData(
        # L0 MONITORING
        'l0',
        'BIO_S3_RAW__0M_20230101T120000_20230101T120147_I_G03_M03_C03_T022_F____01_AFRS00',
        'bio_s3_raw__0m_20230101t120000_20230101t120147_i_g03_m03_c03_t022_f____rxh.dat',
        'S3_RAW__0M',
        datetime.datetime(2023, 1, 1, 12, 0, 0),
        datetime.datetime(2023, 1, 1, 12, 1, 47),
        datetime.datetime(2020, 1, 1, 0, 0, 0),
        1,
        None,
        'Interferometric', '03', '03', '03', '022', None,
        '_rxh'
    ),
    _TestData(
        # L0 PLATFORM ANCILLARY
        'l0',
        'BIO_AC_RAW__0A_20230101T120000_20230101T120147_I_G___M03_C03_T022_F____01_AFRS00',
        'bio_ac_raw__0a_20230101t120000_20230101t120147_i_g___m03_c03_t022_f___.dat',
        'AC_RAW__0A',
        datetime.datetime(2023, 1, 1, 12, 0, 0),
        datetime.datetime(2023, 1, 1, 12, 1, 47),
        datetime.datetime(2020, 1, 1, 0, 0, 0),
        1,
        None,
        'Interferometric', 'NA', '03', '03', '022', None,
        None
    ),
]


class ProductNameTest(unittest.TestCase):

    def testGenerate(self):
        for d in _TEST_DATA:
            pn = ProductName()

            # Setup
            pn.file_type = d.type
            pn.start_time = d.start
            pn.stop_time = d.stop
            pn.baseline_identifier = d.baseline
            pn.set_creation_date(d.create)
            if d.level == 'raw':
                pn.downlink_time = d.downlink
            else:
                pn.mission_phase = str(d.mission_phase)
                pn.global_coverage_id = d.global_coverage_id
                pn.major_cycle_id = d.major_cycle_id
                pn.repeat_cycle_id = d.repeat_cycle_id
                pn._track_nr_str = d.track_nr
                pn.frame_slice_nr = d.frame_nr

            path = pn.generate_path_name()
            mph = pn.generate_mph_file_name()
            bin = pn.generate_binary_file_name(d.suffix)
            self.assertEqual(path, d.dir)
            self.assertEqual(mph, d.mph)
            self.assertEqual(bin, d.bin)

    def testParse(self):
        for d in _TEST_DATA:
            pn = ProductName()
            pn.parse_path(d.dir)
            self.assertEqual(pn.level, d.level)
            self.assertEqual(pn.file_type, d.type)
            self.assertEqual(pn.baseline_identifier, d.baseline)
            self.assertEqual(pn.start_time, d.start)
            self.assertEqual(pn.stop_time, d.stop)
            self.assertEqual(pn._compact_create_date, d.dir[-6:])
            if d.level == 'raw':
                self.assertEqual(pn.downlink_time, d.downlink)
            elif d.level == 'l0':
                self.assertEqual(pn.mission_phase, d.mission_phase)
                self.assertEqual(pn.global_coverage_id, d.global_coverage_id)
                self.assertEqual(pn.major_cycle_id, d.major_cycle_id)
                self.assertEqual(pn.repeat_cycle_id, d.repeat_cycle_id)
                self.assertEqual(pn._track_nr_str, d.track_nr)
                self.assertEqual(pn.frame_slice_nr, d.frame_nr)
            else:
                assert()

    def testMissingParams(self):
        pn = ProductName()
        self.assertRaises(Exception, pn.generate_path_name)
        pn.start_time = datetime.datetime.now()
        pn.stop_time = datetime.datetime.now()
        pn.baseline_identifier = 0
        self.assertRaises(Exception, pn.generate_path_name)
        pn.mission_phase = 'Commissioning'
        self.assertRaises(Exception, pn.generate_path_name)
        pn.global_coverage_id = None
        self.assertRaises(Exception, pn.generate_path_name)
        pn.major_cycle_id = '1'
        self.assertRaises(Exception, pn.generate_path_name)
        pn.repeat_cycle_id = '1'
        self.assertRaises(Exception, pn.generate_path_name)
        pn.track_nr = '0'
        self.assertRaises(Exception, pn.generate_path_name)
        pn.frame_slice_nr = 1
        pn.generate_path_name()

    def testInvalidParameters(self):
        pn = ProductName()
        with self.assertRaises(ValueError):
            pn.file_type = 'UNKNOWN'
        with self.assertRaises(ValueError):
            pn.frame_slice_nr = -1
        with self.assertRaises(ValueError):
            pn.track_nr = 1000


if __name__ == '__main__':
    unittest.main()

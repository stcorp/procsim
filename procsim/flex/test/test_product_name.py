'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import unittest
from typing import List

from procsim.flex.product_name import ProductName
from procsim.core.exceptions import GeneratorError, ScenarioError


class _TestData():
    def __init__(self, level, dir, bin, type, start, stop, create=None, baseline=None, downlink=None, suffix=None):
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
        self.suffix = suffix


_TEST_DATA: List[_TestData] = [
    _TestData(
        'raw',
        'FLX_RAW___HKTM_20170101T060131_20170101T060706_O12345',
        'flx_raw___hktm_20170101t060131_20170101t060706_o12345.dat',
        'RAW___HKTM',
        datetime.datetime(2017, 1, 1, 6, 1, 31, tzinfo=datetime.timezone.utc),
        datetime.datetime(2017, 1, 1, 6, 7, 6, tzinfo=datetime.timezone.utc),
        None,
        None,
        datetime.datetime(2021, 1, 1, 6, 7, 6, tzinfo=datetime.timezone.utc),
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

#            elif d.level == 'mpl':
#                pn.file_class = d.file_class
#                pn.downlink_time = d.downlink
#                pn.mission_phase = d.mission_phase
#                pn.version_nr = d.version_nr
#            else:
#                pn.mission_phase = str(d.mission_phase)
#                pn.global_coverage_id = d.global_coverage_id
#                pn.major_cycle_id = d.major_cycle_id
#                pn.repeat_cycle_id = d.repeat_cycle_id
#                pn.track_nr = d.track_nr
#                pn.frame_slice_nr = d.frame_nr

            path = pn.generate_path_name()
            mph = pn.generate_mph_file_name()
            bin = pn.generate_binary_file_name(d.suffix)
            self.assertEqual(path, d.dir)
            self.assertEqual(mph, d.mph)
            if d.bin:
                # Only compare binary files if we expect one to exist.
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

            if pn._compact_create_date:
                # Not all product names have a creation date.
                self.assertEqual(pn._compact_create_date, d.dir[-6:])

    '''
            elif d.level == 'l0':
                self.assertEqual(pn.mission_phase, d.mission_phase)
                self.assertEqual(pn.global_coverage_id, d.global_coverage_id)
                self.assertEqual(pn.major_cycle_id, d.major_cycle_id)
                self.assertEqual(pn.repeat_cycle_id, d.repeat_cycle_id)
                self.assertEqual(pn.track_nr, d.track_nr)
                self.assertEqual(pn.frame_slice_nr, d.frame_nr)
            elif d.level == 'mpl':
                self.assertEqual(pn.file_class, d.file_class)
                self.assertEqual(pn.baseline_identifier, d.baseline)
                self.assertEqual(pn.version_nr, d.version_nr)
    '''

    def testMissingParams(self):
        pn = ProductName()
        self.assertRaises(Exception, pn.generate_path_name)
        pn.start_time = datetime.datetime.now(tz=datetime.timezone.utc)
        pn.stop_time = datetime.datetime.now(tz=datetime.timezone.utc)
        pn.baseline_identifier = 'BB'
        self.assertRaises(Exception, pn.generate_path_name)
        pn.mission_phase = 'Commissioning'
        self.assertRaises(Exception, pn.generate_path_name)
        pn.file_type = 'RAW___HKTM'
        self.assertRaises(Exception, pn.generate_path_name)

        pn.downlink_time = datetime.datetime.now()
        pn.generate_path_name()


if __name__ == '__main__':
    unittest.main()

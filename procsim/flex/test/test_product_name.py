'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import unittest
from typing import List

from procsim.flex.product_name import ProductName
from procsim.core.exceptions import GeneratorError, ScenarioError


class _TestData():
    def __init__(self, level, dir, bin, type, start, stop, create=None, baseline=None, downlink=None, suffix=None,
                 cycle_number=None, rel_orbit=None, anx_elapsed=None):
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
        self.cycle_number = cycle_number
        self.rel_orbit = rel_orbit
        self.anx_elapsed = anx_elapsed


_TEST_DATA: List[_TestData] = [
    _TestData(
        level='raw',
        dir='FLX_RAW___HKTM_20170101T060131_20170101T060706_O12345',
        bin='flx_raw___hktm_20170101t060131_20170101t060706_o12345.dat',
        type='RAW___HKTM',
        start=datetime.datetime(2017, 1, 1, 6, 1, 31, tzinfo=datetime.timezone.utc),
        stop=datetime.datetime(2017, 1, 1, 6, 7, 6, tzinfo=datetime.timezone.utc),
        downlink=datetime.datetime(2021, 1, 1, 6, 7, 6, tzinfo=datetime.timezone.utc),
    ),
    _TestData(
        level='l0',
        dir='FLX_L0__DEFDAR_20170101T060131_20170101T060344_20230213T104618_0133_012_046_0090_1B',
        bin='flx_l0__defdar_20170101t060131_20170101t060344_20230213t104618_0133_012_046_0090_1b_hre1.dat',
        type='L0__DEFDAR',
        start=datetime.datetime(2017, 1, 1, 6, 1, 31, tzinfo=datetime.timezone.utc),
        stop=datetime.datetime(2017, 1, 1, 6, 3, 44, tzinfo=datetime.timezone.utc),
        downlink=datetime.datetime(2023, 2, 13, 10, 46, 18, tzinfo=datetime.timezone.utc),  # TODO remove
        create=datetime.datetime(2023, 2, 13, 10, 46, 18, tzinfo=datetime.timezone.utc),
        cycle_number='012',
        rel_orbit='046',
        anx_elapsed='0090',
        baseline='1B',
        suffix='_hre1',
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

            elif d.level == 'l0':
                pn.downlink_time = d.downlink  # TODO shouldn't this be creation date
                pn.cycle_number = d.cycle_number
                pn.relative_orbit_number = d.rel_orbit
                pn.anx_elapsed = d.anx_elapsed
                pn.suffix = d.suffix

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

            if d.level == 'l0':
                self.assertEqual(pn.cycle_number, d.cycle_number)

    def testMissingParams(self):
        pn = ProductName()
        self.assertRaises(Exception, pn.generate_path_name)
        pn.start_time = datetime.datetime.now(tz=datetime.timezone.utc)
        pn.stop_time = datetime.datetime.now(tz=datetime.timezone.utc)
        pn.baseline_identifier = 'BB'
        self.assertRaises(Exception, pn.generate_path_name)
        pn.file_type = 'RAW___HKTM'
        self.assertRaises(Exception, pn.generate_path_name)

        pn.downlink_time = datetime.datetime.now()
        pn.generate_path_name()


if __name__ == '__main__':
    unittest.main()

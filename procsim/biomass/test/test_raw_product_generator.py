'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import glob
import os
import shutil
import unittest
from xml.etree import ElementTree as et

from procsim.biomass import main_product_header
from procsim.biomass import constants
from procsim.biomass.raw_product_generator import RAWSxxx_10

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')


class _Logger:
    def __init__(self):
        self.count = 0

    def debug(self, *args, **kwargs):
        # print(*args, **kwargs)
        pass

    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        print(*args, **kwargs)


class RAWSxxx_10Test(unittest.TestCase):

    @staticmethod
    def is_aligned(slice_start, slice_end, anx):
        # Check if start/end times are on grid within +/-SIGMA (referred to anx)
        SIGMA = datetime.timedelta(0, 0.1)
        rest = ((slice_start + constants.SLICE_OVERLAP_START - anx + SIGMA) % constants.SLICE_GRID_SPACING)
        start_is_aligned = rest < SIGMA * 2
        rest = ((slice_end - constants.SLICE_OVERLAP_END - anx + SIGMA) % constants.SLICE_GRID_SPACING)
        end_is_aligned = rest < SIGMA * 2
        return start_is_aligned, end_is_aligned

    def create_class_under_test(self):
        logger = _Logger()
        job_config = None
        config = {
            'anx': [
                '2021-01-31T22:47:21.765Z',
                '2021-02-01T00:25:33.745Z',  # 1 second too late
                '2021-02-01T02:03:43.725Z'   # 1 second too early
            ],
            'output_path': TEST_DIR,
            'type': 'RAWS025_10',
            'processor_name': 'unittest',
            'processor_version': '01.01',
            'baseline': 10,
            'acquisition_date': '2021-01-01T00:00:00.000Z',
            'acquisition_station': 'unittest',
            'num_isp': 387200,
            'num_isp_erroneous': 0,
            'num_isp_corrupt': 0,
            'zip_output': False
        }
        self.anx1 = datetime.datetime(2021, 1, 31, 22, 47, 21, 765000)
        self.anx2 = datetime.datetime(2021, 2, 1, 0, 25, 33, 745000)

        self.addCleanup(shutil.rmtree, TEST_DIR)
        return RAWSxxx_10(logger, job_config, config, config)

    def parse_product(self, productpath):
        filename = os.path.join(
            TEST_DIR,
            productpath,
            productpath.lower() + '.xml'
        )

        # TODO: Write separate XML code, to avoid using the MainProductHeader
        # class here?
        files = glob.glob(filename)
        hdr = main_product_header.MainProductHeader()
        hdr.parse(files[0])
        return hdr

    def testSlicerCase1(self):
        '''
        Datatake overlaps with ANX. Expect slice 62, aligned to anx#1,
        then slice 1, 2, 3, aligned to anx#2.
        '''
        gen = self.create_class_under_test()

        # Normally we read this from input products, but now we set it by hand.
        begin = datetime.datetime(2021, 2, 1, 0, 24, 32, 0)
        end = datetime.datetime(2021, 2, 1, 0, 29, 32, 0)
        gen._hdr.validity_start = gen._hdr.begin_position = begin
        gen._hdr.validity_stop = gen._hdr.end_position = end

        gen.read_scenario_parameters()
        gen.generate_output()

        # Test output. We expect 4 files.
        anx = self.anx1

        hdr = self.parse_product('BIO_RAWS025_10_20210201T002432_20210201T002539_D20210101T000000_10_??????')
        self.assertEqual(hdr.begin_position, begin)
        self.assertNotEqual(hdr.begin_position, hdr.validity_start)
        self.assertEqual(hdr.end_position, hdr.validity_stop)
        start_aligned, end_aligned = self.is_aligned(hdr.begin_position, hdr.end_position, anx)
        self.assertFalse(start_aligned)
        self.assertTrue(end_aligned)
        start_aligned, end_aligned = self.is_aligned(hdr.validity_start, hdr.validity_stop, anx)
        self.assertTrue(start_aligned)
        self.assertTrue(end_aligned)

        anx = self.anx2
        hdr = self.parse_product('BIO_RAWS025_10_20210201T002528_20210201T002715_D20210101T000000_10_??????')
        self.assertEqual(hdr.begin_position, hdr.validity_start)
        self.assertEqual(hdr.end_position, hdr.validity_stop)
        start_aligned, end_aligned = self.is_aligned(hdr.begin_position, hdr.end_position, anx)
        self.assertTrue(start_aligned)
        self.assertTrue(end_aligned)

        hdr = self.parse_product('BIO_RAWS025_10_20210201T002703_20210201T002850_D20210101T000000_10_??????')
        self.assertEqual(hdr.begin_position, hdr.validity_start)
        self.assertEqual(hdr.end_position, hdr.validity_stop)
        start_aligned, end_aligned = self.is_aligned(hdr.begin_position, hdr.end_position, anx)
        self.assertTrue(start_aligned)
        self.assertTrue(end_aligned)

        hdr = self.parse_product('BIO_RAWS025_10_20210201T002838_20210201T002932_D20210101T000000_10_??????')
        self.assertEqual(hdr.begin_position, hdr.validity_start)
        self.assertNotEqual(hdr.end_position, hdr.validity_stop)
        self.assertEqual(hdr.end_position, end)
        start_aligned, end_aligned = self.is_aligned(hdr.begin_position, hdr.end_position, anx)
        self.assertTrue(start_aligned)
        self.assertFalse(end_aligned)
        start_aligned, end_aligned = self.is_aligned(hdr.validity_start, hdr.validity_stop, anx)
        self.assertTrue(start_aligned)
        self.assertTrue(end_aligned)


if __name__ == '__main__':
    unittest.main()

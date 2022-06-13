'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import glob
import os
import shutil
import unittest

from procsim.biomass import constants, main_product_header
from procsim.biomass.raw_product_generator import RAWSxxx_10
from procsim.core.exceptions import ScenarioError

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

    @staticmethod
    def calc_nr_products_in_dir():
        return len([name for name in os.listdir(TEST_DIR) if os.path.isdir(os.path.join(TEST_DIR, name))])

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
            'num_tf': 387200,
            'num_tf_erroneous': 0,
            'num_tf_corrupt': 0,
            'zip_output': False,
            'slice_overlap_start': 5.0,
            'slice_overlap_end': 7.0,
            'slice_minimum_duration': 15.0,
            'data_take_id': 1
        }
        self.anx1 = datetime.datetime(2021, 1, 31, 22, 47, 21, 765000, tzinfo=datetime.timezone.utc)
        self.anx2 = datetime.datetime(2021, 2, 1, 0, 25, 33, 745000, tzinfo=datetime.timezone.utc)

        self.addCleanup(shutil.rmtree, TEST_DIR, ignore_errors=True)
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

    def testNormal(self):
        '''
        Datatake length = 5 minutes.
        Overlaps with ANX. Expect slice 62, aligned to anx#1,
        then slice 1, 2, 3, aligned to anx#2.
        '''
        gen = self.create_class_under_test()

        # Normally we read this from input products, but now we set it by hand.
        begin = datetime.datetime(2021, 2, 1, 0, 24, 32, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2021, 2, 1, 0, 29, 32, 0, tzinfo=datetime.timezone.utc)
        gen._hdr.validity_start = gen._hdr.begin_position = begin
        gen._hdr.validity_stop = gen._hdr.end_position = end

        gen.read_scenario_parameters()
        gen.generate_output()

        # Test output. We expect 4 files.
        self.assertEqual(self.calc_nr_products_in_dir(), 4)

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

    def testMergeShortSlices(self):
        '''
        Datatake from 3.7 seconds before ANX2.
        Expect slice 62 to be merged with slice 1,
        then slice 2, 3.
        '''
        gen = self.create_class_under_test()

        # Normally we read this from input products, but now we set it by hand.
        begin = datetime.datetime(2021, 2, 1, 0, 25, 30, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2021, 2, 1, 0, 30, 23, 0, tzinfo=datetime.timezone.utc)
        gen._hdr.validity_start = gen._hdr.begin_position = begin
        gen._hdr.validity_stop = gen._hdr.end_position = end

        gen.read_scenario_parameters()
        gen.generate_output()

        # Test output.
        self.assertEqual(self.calc_nr_products_in_dir(), 3)

        anx = self.anx2
        hdr = self.parse_product('BIO_RAWS025_10_20210201T002530_20210201T002715_D20210101T000000_10_??????')
        self.assertNotEqual(hdr.begin_position, hdr.validity_start)
        self.assertEqual(hdr.end_position, hdr.validity_stop)
        start_aligned, end_aligned = self.is_aligned(hdr.begin_position, hdr.end_position, anx)
        self.assertFalse(start_aligned)
        self.assertTrue(end_aligned)

        hdr = self.parse_product('BIO_RAWS025_10_20210201T002703_20210201T002850_D20210101T000000_10_??????')
        self.assertEqual(hdr.begin_position, hdr.validity_start)
        self.assertEqual(hdr.end_position, hdr.validity_stop)
        start_aligned, end_aligned = self.is_aligned(hdr.begin_position, hdr.end_position, anx)
        self.assertTrue(start_aligned)
        self.assertTrue(end_aligned)

        hdr = self.parse_product('BIO_RAWS025_10_20210201T002838_20210201T003023_D20210101T000000_10_??????')
        self.assertEqual(hdr.begin_position, hdr.validity_start)
        self.assertNotEqual(hdr.end_position, hdr.validity_stop)
        self.assertEqual(hdr.end_position, end)
        start_aligned, end_aligned = self.is_aligned(hdr.begin_position, hdr.end_position, anx)
        self.assertTrue(start_aligned)
        self.assertFalse(end_aligned)
        start_aligned, end_aligned = self.is_aligned(hdr.validity_start, hdr.validity_stop, anx)
        self.assertTrue(start_aligned)
        self.assertTrue(end_aligned)

    def testMergeToSingleSlice(self):
        '''
        Datatake from 4 seconds before slice #1 to 1 second after slice #1.
        Expect slice 62 and slice 2 to be merged with slice 1.
        '''
        gen = self.create_class_under_test()

        # Normally we read this from input products, but now we set it by hand.
        begin = datetime.datetime(2021, 2, 1, 0, 25, 30, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2021, 2, 1, 0, 27, 9, 0, tzinfo=datetime.timezone.utc)
        gen._hdr.validity_start = gen._hdr.begin_position = begin
        gen._hdr.validity_stop = gen._hdr.end_position = end

        gen.read_scenario_parameters()
        gen.generate_output()

        # Test output.
        self.assertEqual(self.calc_nr_products_in_dir(), 1)
        anx = self.anx2
        hdr = self.parse_product('BIO_RAWS025_10_20210201T002530_20210201T002709_D20210101T000000_10_??????')
        self.assertNotEqual(hdr.begin_position, hdr.validity_start)
        self.assertNotEqual(hdr.end_position, hdr.validity_stop)
        start_aligned, end_aligned = self.is_aligned(hdr.begin_position, hdr.end_position, anx)
        self.assertFalse(start_aligned)
        self.assertFalse(end_aligned)

    def testNoDataTakeInfo(self) -> None:
        '''Production should fail if no data take info is found.'''
        gen = self.create_class_under_test()
        # Remove mandatory data take info.
        del gen._scenario_config['data_take_id']
        gen.read_scenario_parameters()

        # Normally we read this from input products, but now we set it by hand.
        begin = datetime.datetime(2021, 2, 1, 0, 24, 32, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2021, 2, 1, 0, 29, 32, 0, tzinfo=datetime.timezone.utc)
        gen._hdr.validity_start = gen._hdr.begin_position = begin
        gen._hdr.validity_stop = gen._hdr.end_position = end

        with self.assertRaises(ScenarioError):
            gen.generate_output()

    def testMultipleDataTakes(self) -> None:
        '''
        Test that multiple data takes appear in the MPH and that the
        correct products are generated.
        '''
        # Get the start/stop times of the data takes.
        sensing_start = datetime.datetime(2021, 2, 1, 0, 24, 32, 0, tzinfo=datetime.timezone.utc)
        sensing_stop = datetime.datetime(2021, 2, 1, 0, 29, 32, 0, tzinfo=datetime.timezone.utc)
        num_data_takes = 4
        data_take_length = (sensing_stop - sensing_start) / num_data_takes
        data_take_times = [sensing_start + i * data_take_length for i in range(num_data_takes + 1)]
        time_format = '%Y-%m-%dT%H:%M:%S.%fZ'

        gen = self.create_class_under_test()
        gen._scenario_config['enable_slicing'] = False  # Make sure we can count data takes instead of slices in this test.
        gen._scenario_config['data_takes'] = [
            {
                'data_take_id': 12,
                'start': data_take_times[0].strftime(time_format),
                'stop': data_take_times[1].strftime(time_format)
            },
            {
                'data_take_id': 13,
                'start': data_take_times[1].strftime(time_format),
                'stop': data_take_times[2].strftime(time_format)
            },
            {
                'data_take_id': 14,
                'start': data_take_times[2].strftime(time_format),
                'stop': data_take_times[3].strftime(time_format)
            },
            {
                'data_take_id': 15,
                'start': data_take_times[3].strftime(time_format),
                'stop': data_take_times[4].strftime(time_format)
            },
        ]
        gen.read_scenario_parameters()
        gen._hdr.validity_start = gen._hdr.begin_position = sensing_start
        gen._hdr.validity_stop = gen._hdr.end_position = sensing_stop

        gen.generate_output()

        # Check whether enough files were generated, and whether they have the correct data take IDs and sensing times.
        self.assertEqual(self.calc_nr_products_in_dir(), num_data_takes)
        hdr = self.parse_product('BIO_RAWS025_10_20210201T002432_20210201T002547_D20210101T000000_10_??????')
        self.assertEqual(hdr.acquisitions[0].data_take_id, 12)
        self.assertEqual(hdr.begin_position, data_take_times[0])
        self.assertEqual(hdr.end_position, data_take_times[1])
        hdr = self.parse_product('BIO_RAWS025_10_20210201T002547_20210201T002702_D20210101T000000_10_??????')
        self.assertEqual(hdr.acquisitions[0].data_take_id, 13)
        self.assertEqual(hdr.begin_position, data_take_times[1])
        self.assertEqual(hdr.end_position, data_take_times[2])
        hdr = self.parse_product('BIO_RAWS025_10_20210201T002702_20210201T002817_D20210101T000000_10_??????')
        self.assertEqual(hdr.acquisitions[0].data_take_id, 14)
        self.assertEqual(hdr.begin_position, data_take_times[2])
        self.assertEqual(hdr.end_position, data_take_times[3])
        hdr = self.parse_product('BIO_RAWS025_10_20210201T002817_20210201T002932_D20210101T000000_10_??????')
        self.assertEqual(hdr.acquisitions[0].data_take_id, 15)
        self.assertEqual(hdr.begin_position, data_take_times[3])
        self.assertEqual(hdr.end_position, data_take_times[4])


if __name__ == '__main__':
    unittest.main()

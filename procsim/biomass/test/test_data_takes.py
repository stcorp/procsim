'''
Copyright (C) 2022 S[&]T, The Netherlands.
'''
import datetime
import glob
import os
import shutil
import tempfile
import unittest
from typing import Dict, List, Optional

from procsim.biomass.aux_product_generator import Aux
from procsim.biomass.level0_product_generator import AC_RAW__0A, Sx_RAW__0M, Sx_RAW__0x
from procsim.biomass.level1_product_generator import Level1PreProcessor, Level1Stack, Level1Stripmap
from procsim.biomass.main_product_header import MainProductHeader
from procsim.biomass.product_generator import ProductGeneratorBase
from procsim.biomass.raw_product_generator import RAWSxxx_10
from procsim.core.exceptions import ScenarioError

TEST_DIR = tempfile.TemporaryDirectory()


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


class DataTakeTest(unittest.TestCase):

    GENERATORS_TO_TEST = [
        RAWSxxx_10,
        Sx_RAW__0x, Sx_RAW__0M, AC_RAW__0A,
        Level1PreProcessor, Level1Stripmap, Level1Stack,
        Aux  # Only AUX_ATT and AUX_ORB.
    ]

    # This config should contain all mandatory common parameters for all generators to test.
    STANDARD_CONFIG = {
        'output_path': TEST_DIR.name,
        'mission_phase': 'INTERFEROMETRIC',
        'processor_name': 'test_proc',
        'processor_version': '1',
        'baseline': 0,
        'acquisition_date': '2020-01-01T00:00:00.000',
        'acquisition_station': 'SVB',
        'downlink_time': '2020-01-01T00:00:00.000',
        'anx': [
            '2020-01-01T00:00:00.000'
        ],
        'source_L0S': 'test_L0S',
        'source_L0M': 'test_L0M',
        'source_AUX_ORB': 'test_AUX_ORB'
    }

    def tearDown(self) -> None:
        # Remove all files from the test directory between tests.
        for filename in os.listdir(TEST_DIR.name):
            full_path = os.path.join(TEST_DIR.name, filename)
            if os.path.isfile(full_path):
                os.remove(full_path)
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path)
        return super().tearDown()

    def _get_generators(self, config: Optional[Dict] = None) -> List[ProductGeneratorBase]:
        '''
        Generators need specific parameters set. Those are set here and the
        generators are returned.
        '''
        config_to_use = config if config else self.STANDARD_CONFIG
        generators: List[ProductGeneratorBase] = []
        for generator_class in self.GENERATORS_TO_TEST:
            gen_type = generator_class.PRODUCTS[0]
            gen_config = {**config_to_use, 'type': gen_type}
            generators.append(generator_class(_Logger, None, gen_config, gen_config))
        return generators

    def test_no_data_take_info(self):
        '''
        Check whether product generation fails if data take information is
        omitted.
        '''
        for generator in self._get_generators():
            generator.read_scenario_parameters()
            with self.assertRaises(ScenarioError):
                generator.generate_output()

    def test_data_take_info_in_root(self) -> None:
        '''
        Data take information should be readable from root. Check whether this
        is the case.
        '''
        test_scenario = {**self.STANDARD_CONFIG,
                         'begin_position': '2020-01-01T00:00:00.000',
                         'end_position': '2020-01-01T00:01:00.000',
                         'data_take_id': 1}
        for generator in self._get_generators(test_scenario):
            generator.read_scenario_parameters()
            self.assertEqual(generator._hdr.acquisitions[0].data_take_id, 1)
            self.assertEqual(generator._hdr.begin_position, datetime.datetime(2020, 1, 1, 0, 0, 0).replace(tzinfo=datetime.timezone.utc))
            self.assertEqual(generator._hdr.end_position, datetime.datetime(2020, 1, 1, 0, 1, 0).replace(tzinfo=datetime.timezone.utc))
            generator.generate_output()

            print(generator, len(os.listdir(TEST_DIR.name)))

        # All generators generate one product, except for the L1 preprocessor, which generates three in the given sensing time.
        self.assertEqual(len(os.listdir(TEST_DIR.name)), len(self.GENERATORS_TO_TEST) + 2)

        # Check whether data take parameters were set appropriately.
        for filename in glob.glob(TEST_DIR.name + '/*/bio_*.xml'):
            hdr = MainProductHeader()
            hdr.parse(filename)
            self.assertEqual(hdr.acquisitions[0].data_take_id, 1)

    def test_data_take_info_in_list(self) -> None:
        '''Test data take info parsing from data_takes list.'''
        test_scenario = {
            **self.STANDARD_CONFIG,
            'begin_position': '2020-01-01T00:00:00.000',
            'end_position': '2020-01-01T00:01:00.000',
            'data_takes': [
                {
                    'data_take_id': 1,
                    'start': '2020-01-01T00:00:00.000',
                    'stop': '2020-01-01T00:00:20.000',
                    'swath': 'S1'
                },
                {
                    'data_take_id': 2,
                    'start': '2020-01-01T00:00:20.000',
                    'stop': '2020-01-01T00:00:40.000',
                    'swath': 'S2'
                },
                {
                    'data_take_id': 3,
                    'start': '2020-01-01T00:00:40.000',
                    'stop': '2020-01-01T00:01:00.000',
                    'swath': 'AC'
                },
            ]}

        for generator in self._get_generators(test_scenario):
            generator.read_scenario_parameters()
            generator.generate_output()

        # All generators generate one product in the given data takes.
        self.assertEqual(len(os.listdir(TEST_DIR.name)), len(self.GENERATORS_TO_TEST) * 3)

        # Check whether data take parameters were set appropriately. Expect a third of all MPHs to be set to 1, another third to 2 and the rest to 3.
        data_take_counts = {1: 0, 2: 0, 3: 0}
        for filename in glob.glob(TEST_DIR.name + '/*/bio_*.xml'):
            hdr = MainProductHeader()
            hdr.parse(filename)
            if hdr.acquisitions[0].data_take_id:
                data_take_counts[hdr.acquisitions[0].data_take_id] += 1
        for count in data_take_counts.values():
            self.assertEqual(count, (len(os.listdir(TEST_DIR.name)) - 3) / 3)  # Disregard virtual frames, which have no MPH.

    def test_general_info_in_data_takes(self) -> None:
        '''
        Test whether generally required information can be read from data takes.
        '''
        # Three parameters are required at the top level: processor_name, processor_version and anx.
        test_scenario = {
            'processor_name': self.STANDARD_CONFIG['processor_name'],
            'processor_version': self.STANDARD_CONFIG['processor_version'],
            'anx': self.STANDARD_CONFIG['anx'],
            'begin_position': '2020-01-01T00:00:00.000',
            'end_position': '2020-01-01T00:01:00.000',
            'data_takes': [
                {
                    **self.STANDARD_CONFIG,
                    'data_take_id': 1,
                    'start': '2020-01-01T00:00:00.000',
                    'stop': '2020-01-01T00:00:20.000',
                    'swath': 'S1'
                },
                {
                    **self.STANDARD_CONFIG,
                    'data_take_id': 2,
                    'start': '2020-01-01T00:00:20.000',
                    'stop': '2020-01-01T00:00:40.000',
                    'swath': 'S2'
                },
                {
                    **self.STANDARD_CONFIG,
                    'data_take_id': 3,
                    'start': '2020-01-01T00:00:40.000',
                    'stop': '2020-01-01T00:01:00.000',
                    'swath': 'AC'
                },
            ]}

        for generator in self._get_generators(test_scenario):
            generator.read_scenario_parameters()
            generator.generate_output()

        # All generators generate one product in the given data takes.
        self.assertEqual(len(os.listdir(TEST_DIR.name)), len(self.GENERATORS_TO_TEST) * 3)

        # Check whether data take parameters were set appropriately. Expect a third of all MPHs to be set to 1, another third to 2 and the rest to 3.
        data_take_counts = {1: 0, 2: 0, 3: 0}
        for filename in glob.glob(TEST_DIR.name + '/*/bio_*.xml'):
            hdr = MainProductHeader()
            hdr.parse(filename)
            if hdr.acquisitions[0].data_take_id:
                data_take_counts[hdr.acquisitions[0].data_take_id] += 1
        for count in data_take_counts.values():
            self.assertEqual(count, (len(os.listdir(TEST_DIR.name)) - 3) / 3)  # Disregard virtual frames, which have no MPH.


if __name__ == '__main__':
    unittest.main()

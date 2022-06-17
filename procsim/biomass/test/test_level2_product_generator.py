'''
Copyright (C) 2022 S[&]T, The Netherlands.
'''
import datetime
import os
import re
import shutil
import tempfile
import unittest

from procsim.biomass import constants
from procsim.biomass.level2_product_generator import Level2a

TEST_DIR = tempfile.TemporaryDirectory()


class _Logger:
    def __init__(self):
        self.count = 0

    def debug(self, *args, **kwargs):
        # print(*args, **kwargs)
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        print(*args, **kwargs)

    def error(self, *args, **kwargs):
        print(*args, **kwargs)


DATETIME_INPUT_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
ANX = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)


TOMOGRAPHIC_CONFIG = {
    'output_path': TEST_DIR.name,
    'name': 'Level-2a SCS Stack product generation TOM',
    'mission_phase': 'TOMOGRAPHIC',
    'file_name': 'level2a_task1.sh',
    'processor_name': 'l2a_to',
    'processor_version': '01.01',
    'task_name': 'Step1',
    'task_version': '01.01',

    'outputs': [
        {
            'type': 'FP_FH__L2A',
            'metadata_source': '.*S._STA__1S.*'
        },
        {
            'type': 'FP_GN__L2A',
            'metadata_source': '.*S._STA__1S.*'
        }
    ]
}

INTERFEROMETRIC_CONFIG = {
    'output_path': TEST_DIR.name,
    'name': 'Level-2a SCS Stack product generation INT',
    'mission_phase': 'INTERFEROMETRIC',
    'file_name': 'level2a_task1.sh',
    'processor_name': 'l2a_in',
    'processor_version': '01.01',
    'task_name': 'Step1',
    'task_version': '01.01',

    'outputs': [
        {
            'type': 'FP_FD__L2A',
            'metadata_source': '.*S._STA__1S.*'
        },
        {
            'type': 'FP_FH__L2A',
            'metadata_source': '.*S._STA__1S.*'
        },
        {
            'type': 'FP_GN__L2A',
            'metadata_source': '.*S._STA__1S.*'
        }
    ]
}


class Level2AGeneratorTest(unittest.TestCase):
    def tearDown(self) -> None:
        '''Clear temporary directory between tests.'''
        # Only expect directory products in folder.
        for dir in os.listdir(TEST_DIR.name):
            shutil.rmtree(os.path.join(TEST_DIR.name, dir))
        return super().tearDown()

    def test_generate_tomographic_from_scenario(self) -> None:
        '''
        Check whether the L2a generator produces tomographic output under
        nominal conditions, purely from a scenario.
        '''
        # Add necessary parameters to scenario. These are normally read from input products.
        no_inputs_config = {
            **TOMOGRAPHIC_CONFIG,
            'baseline': 1,
            'begin_position': (ANX - constants.SLICE_OVERLAP_START).strftime(DATETIME_INPUT_FORMAT),
            'end_position': (ANX + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END).strftime(DATETIME_INPUT_FORMAT),
        }
        for output_config in no_inputs_config['outputs']:
            self.assertTrue(output_config['type'] in Level2a.PRODUCTS)

            gen = Level2a(_Logger(), None, no_inputs_config, output_config)
            gen.read_scenario_parameters()
            gen.generate_output()

        # Tomographic L2a production should yield two output products of types FP_FH__L2A and FP_GN__L2A.
        products = [os.path.join(TEST_DIR.name, f) for f in os.listdir(TEST_DIR.name)]
        self.assertEqual(len(products), 2)
        for output_pattern in [r'.*FP_FH__L2A.*', r'.*FP_GN__L2A.*']:
            self.assertTrue(any(re.match(output_pattern, f) for f in products))

    def test_generate_interferometric_from_scenario(self) -> None:
        '''
        Check whether the L2a generator produces interferometric output under
        nominal conditions, purely from a scenario.
        '''
        # Add necessary parameters to scenario. These are normally read from input products.
        no_inputs_config = {
            **INTERFEROMETRIC_CONFIG,
            'baseline': 1,
            'begin_position': (ANX - constants.SLICE_OVERLAP_START).strftime(DATETIME_INPUT_FORMAT),
            'end_position': (ANX + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END).strftime(DATETIME_INPUT_FORMAT),
        }
        for output_config in no_inputs_config['outputs']:
            self.assertTrue(output_config['type'] in Level2a.PRODUCTS)

            gen = Level2a(_Logger(), None, no_inputs_config, output_config)
            gen.read_scenario_parameters()
            gen.generate_output()

        # Tomographic L2a production should yield three output products of types FP_FH__L2A, FP_FD__L2A and FP_GN__L2A.
        products = [os.path.join(TEST_DIR.name, f) for f in os.listdir(TEST_DIR.name)]
        self.assertEqual(len(products), 3)
        for output_pattern in [r'.*FP_FH__L2A.*', r'.*FP_FD__L2A.*', r'.*FP_GN__L2A.*']:
            self.assertTrue(any(re.match(output_pattern, f) for f in products))


if __name__ == '__main__':
    unittest.main()

'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex Level 1 product generators,
format according to ESA-EOPG-EOEP-TN-0022
'''
import bisect
import collections
import datetime
import os
from typing import Iterable, List, Tuple, Optional

from . import constants
from procsim.core.exceptions import ScenarioError
from procsim.core.job_order import JobOrderInput

from . import main_product_header, product_generator, product_name

_HDR_PARAMS = [
    ('cycle_number', 'cycle_number', 'str'),
    ('relative_orbit_number', 'relative_orbit_number', 'str'),
]

_ACQ_PARAMS = []


class ProductGeneratorL1(product_generator.ProductGeneratorBase):
    INPUTS = []

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:
        # First copy the metadata from any input product (normally H or V)
        if not super().parse_inputs(input_products, ignore_missing=True):
            return False

        period_types = collections.defaultdict(set)
        for input in input_products:
            if input.file_type in self.INPUTS:
                for file in input.file_names:
                    # Skip non-directory products. These have already been parsed in the superclass.
                    if not os.path.isdir(file):
                        continue
                    file, _ = os.path.splitext(file)    # Remove possible extension
                    gen = product_name.ProductName(self._compact_creation_date_epoch)
                    gen.parse_path(file)
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr = main_product_header.MainProductHeader()
                    hdr.parse(mph_file_name)
                    if hdr.begin_position is None or hdr.end_position is None:
                        raise ScenarioError('begin/end position not set in {}'.format(mph_file_name))
                    start = hdr.begin_position
                    stop = hdr.end_position
                    self._output_period = (start, stop)

        return True


class EO(ProductGeneratorL1):
    INPUTS = [
    ]

    PRODUCTS = [
        'L1B_OBS___',
        'ANC_ROTLOS',
        'ANC_ATTRES',
        'ANC_ORBRES',
    ]

    _ACQ_PARAMS = []

    GENERATOR_PARAMS: List[tuple] = [
        ('orbital_period', '_orbital_period', 'float'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

        self._orbital_period = constants.ORBITAL_PERIOD

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    def generate_output(self):
        super().generate_output()


class CAL(ProductGeneratorL1):
    INPUTS = [
        'L0__DARKNP',
    ]

    PRODUCTS = [
        'RAC_DARKNP',
        'RAC_DARKSR',
        'RAC_DEFDAR',
        'RAC_DEFRTS',
        'RAC_DARKOC',
        'RAC_DRKMTF',
        'RAC_DRKSTR',
        'RAC_SUN___',
        'RAC_DEFSUN',
        'RAC_MOON__',
        'RAC_MOONSL',
        'RAC_LINDES',
        'RAC_CTE___',
        'RAC_CLOUD_',

        'SPC_SPECSD',
        'SPC_SPECEO',
    ]

    _ACQ_PARAMS = [
    ]

    GENERATOR_PARAMS: List[tuple] = [
        ('orbital_period', '_orbital_period', 'float'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

        self._output_period: Optional[[datetime.datetime, datetime.datetime]] = None

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        if self._output_period is None:
            return

        start, stop = self._output_period
        self._logger.debug('Calibration {} from {} to {}'.format(self._hdr.calibration_id, start, stop))

        # Setup MPH fields. Validity time is not changed, should still be the
        # theoretical slice start/end.
        self._hdr.product_type = self._resolve_wildcard_product_type()

        # Create name generator
        name_gen = self._create_name_generator(self._hdr)
        name_gen.downlink_time = datetime.datetime.now()  # TODO


        # Create directory and files
        dir_name = name_gen.generate_path_name()

        self._hdr.initialize_product_list(dir_name)

        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

#        file_path = os.path.join(dir_name, name_gen.generate_binary_file_name())
#        self._add_file_to_product(file_path, self._size_mb // 2)

        file_path = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_path)

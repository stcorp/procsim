'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex Level 1 product generators,
format according to ESA-EOPG-EOEP-TN-0022
'''
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

_ACQ_PARAMS: List[tuple] = []


class EO(product_generator.ProductGeneratorBase):
    """
    This class is responsible for generating the Level 1 EO products.
    """

    PRODUCTS = [
        'L1B_OBS___',
        'ANC_ROTLOS',
        'ANC_ATTRES',
        'ANC_ORBRES',
    ]

    _ACQ_PARAMS: List[tuple] = []

    GENERATOR_PARAMS: List[tuple] = [
        ('orbital_period', '_orbital_period', 'float'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

        self._orbital_period = constants.ORBITAL_PERIOD

        self._output_period: Optional[Tuple[datetime.datetime, datetime.datetime]] = None

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:
        # First copy the metadata from any input product
        if not super()._parse_inputs(input_products, ignore_missing=True):
            return False

        overlapping = set()

        for input in input_products:
            if input.file_type in ('L0__OBS___', 'L0__NAVATT', 'L0__VAU_TM'):
                for file in input.file_names:
                    # Skip non-directory products. These have already been parsed in the superclass.
                    if not os.path.isdir(file):
                        continue
                    file, _ = os.path.splitext(file)    # Remove possible extension
                    gen = product_name.ProductName()
                    gen.parse_path(file)
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr = main_product_header.MainProductHeader()
                    hdr.parse(mph_file_name)
                    if hdr.begin_position is None or hdr.end_position is None:
                        raise ScenarioError('begin/end position not set in {}'.format(mph_file_name))
                    start = hdr.begin_position
                    stop = hdr.end_position

                    # check overlap with joborder TOI (time-of-interest)
                    if self._job_toi_start is not None and self._job_toi_stop is not None:
                        if start <= self._job_toi_start and stop >= self._job_toi_stop:
                            overlapping.add(input.file_type)

        if self._job_toi_start is not None and self._job_toi_stop is not None:
            if len(overlapping) == 3:
                self._output_period = (self._job_toi_start, self._job_toi_stop)

        return True

    def generate_output(self):
        super().generate_output()

        if self._output_period is None:
            return

        start, stop = self._output_period
        self._logger.debug('EO {} from {} to {}'.format(self._hdr.data_take_id, start, stop))
        self._hdr.set_validity_times(start, stop)
        self._hdr.begin_position = start
        self._hdr.end_position = stop

        self._hdr.special_calibration = 'Image_Geo'

        # Setup MPH fields. Validity time is not changed, should still be the
        # theoretical slice start/end.
        self._hdr.product_type = self._resolve_wildcard_product_type()

        # Create name generator
        name_gen = self._create_name_generator(self._hdr)
        name_gen.downlink_time = self._creation_date  # TODO remove
        name_gen.set_creation_date(self._creation_date)

        # Create directory and files
        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)

        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        if self._output_type == 'L1B_OBS___':
            for sensor in ('lres', 'hre1', 'hre2'):
                file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_'+sensor, extension='.nc'))
                self._add_file_to_product(file_path, self._size_mb // 2)
        else:
            file_path = os.path.join(dir_name, name_gen.generate_binary_file_name(extension='.nc'))
            self._add_file_to_product(file_path, self._size_mb // 2)

        file_path = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_path)


class CAL(product_generator.ProductGeneratorBase):

    PRODUCTS = [
        'RAC_DARKNP',
        'RAC_DARKSR',
        'RAC_DEFDAR',
        'RAC_DEFSTR',
        'RAC_DARKOC',
        'RAC_DRKMTF',
        'RAC_DRKSTR',
        'RAC_SUN___',
        'RAC_DEFSUN',
        'RAC_MOON__',
        'RAC_MOONSL',
        'RAC_LINDES',
        'RAC_LINSEA',
        'RAC_LINSUN',
        'RAC_LINDAR',

        'RAC_CTE___',
        'RAC_CLOUD_',

        'SPC_SPECEO',
    ]

    _ACQ_PARAMS: List[tuple] = [
    ]

    GENERATOR_PARAMS: List[tuple] = [
        ('orbital_period', '_orbital_period', 'float'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

        self._output_period: Optional[Tuple[datetime.datetime, datetime.datetime]] = None

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:
        # First copy the metadata from any input product (normally H or V)
        if not super()._parse_inputs(input_products, ignore_missing=True):
            return False

        for input in input_products:
            if input.file_type[4:] == self._output_type[4:]:
                for file in input.file_names:
                    # Skip non-directory products. These have already been parsed in the superclass.
                    if not os.path.isdir(file):
                        continue
                    file, _ = os.path.splitext(file)    # Remove possible extension
                    gen = product_name.ProductName()
                    gen.parse_path(file)
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr = main_product_header.MainProductHeader()
                    hdr.parse(mph_file_name)
                    if hdr.begin_position is None or hdr.end_position is None:
                        raise ScenarioError('begin/end position not set in {}'.format(mph_file_name))
                    start = hdr.begin_position
                    stop = hdr.end_position

                    # check overlap with joborder TOI (time-of-interest)
                    if self._job_toi_start is not None and self._job_toi_stop is not None:
                        overlap_start = max(start, self._job_toi_start)
                        overlap_stop = min(stop, self._job_toi_stop)

                        if overlap_stop > overlap_start:
                            self._output_period = (overlap_start, overlap_stop)

        return True

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
        name_gen.downlink_time = self._creation_date  # TODO remove
        name_gen.set_creation_date(self._creation_date)

        # Create directory and files
        dir_name = name_gen.generate_path_name()

        self._hdr.initialize_product_list(dir_name)

        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        for sensor in ('lres', 'hre1', 'hre2'):
            file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_'+sensor, extension='.nc'))
            self._add_file_to_product(file_path, self._size_mb // 2)

        file_path = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_path)

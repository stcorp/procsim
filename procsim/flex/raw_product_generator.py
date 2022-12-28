'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Biomass raw output product generators, according to BIO-ESA-EOPG-EEGS-TN-0073
'''
import bisect
import datetime
import os
from typing import List, Tuple

from procsim.core.exceptions import ScenarioError

from . import constants, product_generator, product_name

_GENERATOR_PARAMS = [
    ('zip_output', '_zip_output', 'bool')
]
_HDR_PARAMS = [
    ('acquisition_date', 'acquisition_date', 'date'),
    ('acquisition_station', 'acquisition_station', 'str'),
]
_ACQ_PARAMS = []


class RawProductGeneratorBase(product_generator.ProductGeneratorBase):
    '''
    This abstract class is responsible for creating raw products and is used as
    base class for the specific raw product generators.
    '''

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._zip_output = False

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + _GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def _create_raw_product(self, dir_name, name_gen):
        self._logger.info('Create {}'.format(dir_name))
        full_dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(full_dir_name, exist_ok=True)

        bin_file_name = name_gen.generate_binary_file_name()
        full_bin_file_name = os.path.join(full_dir_name, bin_file_name)
        self._add_file_to_product(full_bin_file_name, self._size_mb)

        mph_file_name = name_gen.generate_mph_file_name()
        full_mph_file_name = os.path.join(full_dir_name, mph_file_name)
        self._hdr.write(full_mph_file_name)

        if self._zip_output:
            self.zip_folder(full_dir_name, self._zip_extension)


class UnslicedRawGeneratorBase(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw products generation.
    '''

    HDR_PARAMS = [
        ('begin_position', 'begin_position', 'date'),
        ('end_position', 'end_position', 'date'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen, hdr + self.HDR_PARAMS, acq

    def generate_output(self):
        # Base class is doing part of the setup
        super().generate_output()

        start = self._hdr.begin_position
        stop = self._hdr.end_position

        # Construct product name and set metadata fields
        name_gen = product_name.ProductName(self._compact_creation_date_epoch)
        name_gen.file_type = self._output_type
        name_gen.start_time = start
        name_gen.stop_time = stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(self._creation_date)
        name_gen.downlink_time = self._hdr.acquisition_date

        dir_name = name_gen.generate_path_name()
        self._hdr.product_type = self._output_type
        self._hdr.initialize_product_list(dir_name)
        self._hdr.set_validity_times(start, stop)

        self._create_raw_product(dir_name, name_gen)


class RAW(UnslicedRawGeneratorBase):

    PRODUCTS = [
        'RAW_XS_LR_',
        'RAW_XS_HR1',
        'RAW_XS_HR2',
        'RAW_XS_OBC',
    ]

class RAW_HKTM(UnslicedRawGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    HKTM product generation.
    '''

    PRODUCTS = [
        'RAW___HKTM',
    ]

    HDR_PARAMS = [
        ('num_tf', 'nr_transfer_frames', 'int'),
        ('num_tf_erroneous', 'nr_transfer_frames_erroneous', 'int'),
        ('num_tf_corrupt', 'nr_transfer_frames_corrupt', 'int')
    ]

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen, hdr + self.HDR_PARAMS, acq

class RWS(RawProductGeneratorBase):  # TODO is this really level-0.. what about raw sliced products then?

    PRODUCTS = [
        'RWS_XS_OBS',
        'RWS_XSPOBS',
        'RWS_XS_CAL',
        'RWS_XSPCAL',
        'RWS_XS_ANC',
        'RWS_XSPANC',
    ]

'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import os
import re
import zipfile
from typing import List, Optional

from job_order import JobOrderInput, JobOrderOutput
from logger import Logger
from procsim import IProductGenerator

from biomass import main_product_header, product_name


class ProductGeneratorBase(IProductGenerator):
    '''
    Biomass product generator (abstract) base class. This class is responsible
    for creating Biomass products.
    This base class handles parsing input products to retrieve metadata.
    '''
    ISO_TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'
    HDR_PARAMS = [
        # All but sliced products
        ('validity_start', '_validity_start'),
        ('validity_stop', '_validity_stop'),
        # Raw only
        ('acquisition_date', '_acquisition_date'),
        ('acquisition_station', '_acquisition_station'),
        ('num_isp', '_nr_instrument_source_packets'),
        ('num_isp_erroneous', '_nr_instrument_source_packets_erroneous'),
        ('num_isp_corrupt', '_nr_instrument_source_packets_corrupt'),
        # Level 0 only
        ('num_l0_lines', 'nr_l0_lines'),
        ('num_l0_lines_corrupt', 'nr_l0_lines_corrupt'),
        ('num_l0_lines_missing', 'nr_l0_lines_missing'),
        ('swath', 'sensor_swath'),
        ('operational_mode', 'sensor_mode'),
    ]
    ACQ_PARAMS = [
        # Level 0 only
        ('mission_phase', 'mission_phase'),
        ('data_take_id', 'data_take_id'),
        ('global_coverage_id', 'global_coverage_id'),
        ('major_cycle_id', 'major_cycle_id'),
        ('repeat_cycle_id', 'repeat_cycle_id'),
        ('track_nr', 'track_nr'),
        ('slice_frame_nr', 'slice_frame_nr')
    ]

    def __init__(self, logger: Logger, job_config: JobOrderOutput, scenario_config: dict, output_config: dict):
        self._scenario_config = scenario_config
        self._output_config = output_config
        self._output_path = scenario_config.get('output_path') or output_config.get('output_path') or job_config.dir
        self._baseline_id = int(scenario_config.get('baseline') or output_config.get('baseline') or job_config.baseline)
        self._logger = logger
        self._output_type = output_config['type']
        self._size_mb = int(output_config.get('size', '0'))
        self._meta_data_source: str = output_config.get('metadata_source', '.*')  # default any
        self._create_date: Optional[datetime.datetime] = None
        self.hdr = main_product_header.MainProductHeader()

    def _resolve_wildcard_product_type(self) -> str:
        '''
        Type code can be a 'wildcard' type, such as Sx_RAW__0S.
        In that case, select the correct type using the swath (which must be known now).
        '''
        if self._output_type in ['Sx_RAW__0S', 'Sx_RAWP_0M', 'Sx_RAW__0M',
                                 'Sx_SCS__1S', 'Sx_SCS__1M', 'Sx_DGM__1S']:
            swath = self.hdr.sensor_swath
            if swath is None:
                raise Exception('Swath must be configured to resolve Sx_ type')
            if swath not in ['S1', 'S2', 'S3']:
                raise ValueError('Swath must be S1, S2 or S3')
            return self._output_type.replace('Sx', swath)
        else:
            return self._output_type

    def _time_from_iso_or_none(self, timestr):
        if timestr is None:
            return None
        timestr = timestr[:-1]  # strip 'Z'
        return datetime.datetime.strptime(timestr, self.ISO_TIME_FORMAT)

    def _generate_bin_file(self, file_name, size_mb):
        '''Generate binary file starting with a short ASCII header, followed by
        size (in MB) random data bytes.'''
        CHUNK_SIZE = 2**20
        size = size_mb * 2**20
        file = open(file_name, 'wb')
        hdr = bytes('procsim dummy binary', 'utf-8') + b'\0'
        file.write(hdr)
        size -= len(hdr)
        while size > 0:
            amount = min(size, CHUNK_SIZE)
            file.write(os.urandom(max(amount, 0)))
            size -= amount

    def _unzip(self, archive_name):
        # Sanity check: only raw products should be zipped
        name_gen = product_name.ProductName()
        name_gen.parse_path(archive_name)
        if name_gen.level != 'raw':
            self._logger.warning('{} should not be a zip!'.format(os.path.basename(archive_name)))
        # Unzip and delete archive
        with zipfile.ZipFile(archive_name, mode='r') as zipped:
            self._logger.debug('Unzip archive {}'.format(os.path.basename(archive_name)))
            zipped.extractall()
            os.remove(archive_name)

    def parse_inputs(self, input_products: List[JobOrderInput]) -> bool:
        '''
        For all files:
            - check if it is a (zipped) directory (all biomass products are directories)
            - unzip product if it's a zip archive
            - extract metadata if this product matches self.meta_data_source
        '''
        gen = product_name.ProductName()
        pattern = self._meta_data_source
        mph_is_parsed = False
        for input in input_products:
            for file in input.file_names:
                root, ext = os.path.splitext(file)
                if os.path.isfile(file) and ext == '.zip':
                    self._unzip(file)
                file = root
                if not os.path.isdir(file):
                    self._logger.error('input {} must be a directory'.format(file))
                    return False
                if not mph_is_parsed and re.match(pattern, file):
                    self._logger.debug('Parse {} for {}'.format(os.path.basename(file), self._output_type))
                    gen.parse_path(file)
                    # Derive mph file name from product name, parse header
                    hdr = self.hdr
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr.parse(mph_file_name)
                    mph_is_parsed = True

        if not mph_is_parsed:
            self._logger.error('Cannot find matching product for [{}] to extract metdata from'.format(pattern))
        return mph_is_parsed

    def _read_config_param(self, config: dict, param_name: str, obj: object, hdr_field: str):
        '''
        If param_name is in config, read and set in obj.hdr_field.
        '''
        if config.get(param_name) is None:
            return
        if ('date' in param_name) or ('validity' in param_name):
            val = self._time_from_iso_or_none(config.get(param_name))
        else:
            val = config.get(param_name)
        self._logger.debug('Set header field {} to {}'.format(param_name, val))
        setattr(obj, hdr_field, val)

    def list_scenario_metadata_parameters(self):
        return [param for param, _ in self.HDR_PARAMS + self.ACQ_PARAMS]

    def read_scenario_metadata_parameters(self):
        '''
        Parse metadata parameters from scenario_config (either 'global' or for this output).
        TODO: Also get params from root level
        '''
        for config in self._scenario_config, self._output_config:
            for param, hdr_field in self.HDR_PARAMS:
                self._read_config_param(config, param, self.hdr, hdr_field)
            for param, acq_field in self.ACQ_PARAMS:
                self._read_config_param(config, param, self.hdr.acquisitions[0], acq_field)

    def generate_output(self):
        '''
        Setup mandatory metadata
        '''
        self.hdr.set_processing_parameters(
            self._scenario_config['processor_name'],
            self._scenario_config['processor_version'],
            datetime.datetime.now())

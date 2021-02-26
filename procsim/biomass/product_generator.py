'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import os
import re
from typing import List, Optional

from job_order import JobOrderInput, JobOrderOutput
from procsim import IProductGenerator
from logger import Logger

from biomass import main_product_header, product_name


class ProductGeneratorBase(IProductGenerator):
    '''
    Biomass product generator (abstract) base class. This class is responsible
    for creating Biomass products.
    This base class handles parsing input products to retrieve metadata.
    '''
    ISO_TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'

    def __init__(self, logger: Logger, job_config: JobOrderOutput, scenario_config: dict, output_config: dict):
        self._scenario_config = scenario_config
        self._output_config = output_config
        self._output_path = scenario_config.get('output_path') or output_config.get('output_path') or job_config.dir
        self._baseline_id = int(scenario_config.get('baseline') or output_config.get('baseline') or job_config.baseline)
        self._logger = logger
        self._output_type = output_config['type']
        self._size: int = int(output_config.get('size', '0'))
        self._meta_data_source: str = output_config.get('metadata_source', '.*')  # default any
        self._start: datetime.datetime
        self._stop: datetime.datetime
        self._create_date: datetime.datetime

        # Raw only
        self._acquisition_date: Optional[datetime.datetime] = None
        self._acquisition_station = None
        self._num_isp: Optional[int] = None
        self._num_isp_erroneous: Optional[int] = None
        self._num_isp_corrupt: Optional[int] = None

        # L0 only
        self._num_l0_lines: Optional[str] = None
        self._num_l0_lines_corrupt: Optional[str] = None
        self._num_l0_lines_missing: Optional[str] = None

        self.hdr = main_product_header.MainProductHeader()

    def _time_from_iso_or_none(self, timestr):
        if timestr is None:
            return None
        timestr = timestr[:-1]  # strip 'Z'
        return datetime.datetime.strptime(timestr, self.ISO_TIME_FORMAT)

    def _generate_bin_file(self, file_name, size=0):
        '''Generate binary file starting with a short ASCII header, followed by
        'size' - headersize random data bytes.'''
        CHUNK_SIZE = 2**20
        file = open(file_name, 'wb')
        hdr = bytes('procsim dummy binary', 'utf-8') + b'\0'
        file.write(hdr)
        size -= len(hdr)
        while size > 0:
            amount = min(size, CHUNK_SIZE)
            file.write(os.urandom(max(amount, 0)))
            size -= amount

    def parse_inputs(self, input_products: List[JobOrderInput]) -> bool:
        '''
        Walk over all files, check if it is a directory (all biomass products
        are directories), extract metadata if this product matches
        self.meta_data_source.
        '''
        gen = product_name.ProductName()
        pattern = self._meta_data_source
        mph_is_parsed = False
        for input in input_products:
            for file in input.file_names:
                if not os.path.isdir(file):
                    self._logger.error('input {} must be a directory'.format(file))
                    return False
                if not mph_is_parsed and re.match(pattern, file):
                    self._logger.debug('Parse {} for {}'.format(os.path.basename(file), self._output_type))
                    if gen.parse_path(file):
                        self._start = gen._start_time
                        self._stop = gen._stop_time
                        if (gen.get_level() == 'raw'):
                            self._acquisition_date = gen._downlink_time  # We can also get this from MPH...
                    else:
                        self._logger.error('Filename {} not valid for Biomass'.format(file))
                        return False
                    # Derive mph file name from product name, parse header
                    hdr = self.hdr
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr.parse(mph_file_name)
                    mph_is_parsed = True
        if not mph_is_parsed:
            self._logger.error('Cannot find matching product for [{}] to extract metdata from'.format(pattern))
        return mph_is_parsed

    def _read_cfg(self, name, default):
        # Try to read from either scenario or output
        val = default
        if self._output_config.get(name) is not None:
            return self._output_config.get(name)
        if self._scenario_config.get(name) is not None:
            return self._scenario_config.get(name)

    def read_scenario_metadata_parameters(self):
        '''
        Parse metadata parameters from scenario_config (either 'global' or for this output)
        '''
        scfg = self._scenario_config
        ocfg = self._output_config
        self._start = self._time_from_iso_or_none(ocfg.get('validity_start') or scfg.get('validity_start')) or self._start
        self._stop = self._time_from_iso_or_none(ocfg.get('validity_stop') or scfg.get('validity_stop')) or self._stop
        # Override header parameters
        self._acquisition_date = self._time_from_iso_or_none(ocfg.get('acquisition_date') or scfg.get('acquisition_date')) or self._acquisition_date
        self._acquisition_station = ocfg.get('acquisition_station') or scfg.get('acquisition_station') or self.hdr._acquisition_station
        self._num_isp = self._read_cfg('num_isp', self.hdr._nr_instrument_source_packets)
        self._num_isp_erroneous = self._read_cfg('num_isp_erroneous', self.hdr._nr_instrument_source_packets_erroneous)
        self._num_isp_corrupt = self._read_cfg('num_isp_corrupt', self.hdr._nr_instrument_source_packets_corrupt)
        self._num_l0_lines = self._read_cfg('num_l0_lines', self.hdr.nr_l0_lines)
        self._num_l0_lines_corrupt = self._read_cfg('num_l0_lines_corrupt', self.hdr.nr_l0_lines_corrupt)
        self._num_l0_lines_missing = self._read_cfg('num_l0_lines_missing', self.hdr.nr_l0_lines_missing)

    def generate_output(self):
        '''
        Setup mandatory metadata
        '''
        self.hdr.set_processing_parameters(
            self._scenario_config['processor_name'],
            self._scenario_config['processor_version'],
            datetime.datetime.now())

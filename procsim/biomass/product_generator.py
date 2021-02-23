'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import os
import re
from typing import List

from job_order import JobOrderInput, JobOrderOutput, JobOrderTask
from procsim import IProductGenerator

from biomass import constants, mph, product_name


class ProductGeneratorBase(IProductGenerator):
    '''
    Biomass product generator (abstract) base class. This class is responsible
    for creating Biomass products.
    This base class handles parsing input products to retrieve metadata.
    '''

    def __init__(self, logger, job_config: JobOrderOutput, scenario_config: dict):
        self.output_path = job_config.dir
        self.baseline_id = job_config.baseline
        self.logger = logger
        self.output_type = scenario_config['type']
        self.size: int = int(scenario_config.get('size', '0'))
        self.meta_data_source: str = scenario_config.get('metadata_source', '.*')  # default any
        self.input_type = None
        self.start: datetime.datetime
        self.stop: datetime.datetime
        self.create_date: datetime.datetime
        self.downlink: datetime.datetime
        self.hdr = mph.MainProductHeader()

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
        pattern = self.meta_data_source
        mph_is_parsed = False
        for input in input_products:
            for file in input.file_names:
                if not os.path.isdir(file):
                    self.logger.error('input {} must be a directory'.format(file))
                    return False
                if not mph_is_parsed and re.match(pattern, file):
                    self.logger.debug('Parse {} for {}'.format(os.path.basename(file), self.output_type))
                    if gen.parse_path(file):
                        self.input_type = gen._file_type
                        self.start = gen._start_time
                        self.stop = gen._stop_time
                        if (gen.get_level() == 'raw'):
                            self.downlink = gen._downlink_time
                    else:
                        self.logger.error('Filename {} not valid for Biomass'.format(file))
                        return False
                    # Derive mph file name from product name, parse header
                    hdr = self.hdr
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr.parse(mph_file_name)
                    mph_is_parsed = True
        if not mph_is_parsed:
            self.logger.error('Cannot find matching product for [{}] to extract metdata from'.format(pattern))
        return mph_is_parsed

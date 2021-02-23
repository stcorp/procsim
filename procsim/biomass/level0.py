'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 0 output product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0045
'''
import datetime
import os
import re
from typing import List

from procsim import IProductGenerator, JobOrderInput

from biomass import constants, mph, product_name


class ProductGeneratorBase(IProductGenerator):
    '''Biomass product generator (abstract) base class.'''

    def __init__(self, logger, job_config, scenario_config: dict):
        self.output_path = job_config.dir
        self.baseline_id = job_config.baseline
        self.logger = logger
        self.output_type = scenario_config['type']
        self.size: int = int(scenario_config.get('size', '0'))
        self.meta_data_source: str = scenario_config.get('metadata_source', '.*')  # default any
        self.input_type = None
        self.start: datetime.datetime
        self.stop: datetime.datetime
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
        # Walk over all files, check if it is a directory (all biomass products
        # are directories), extract metadata if this product matches
        # self.meta_data_source.
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
                        self.input_type = gen.file_type
                        self.start = gen.start_time
                        self.stop = gen.stop_time
                        if (gen.get_level() == 'raw'):
                            self.downlink = gen.downlink_time
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


class RAWSxxx_10(ProductGeneratorBase):
    '''Raw slice-based products generation.
    For every slice, the slice validity start/stop times are set.'''
    PRODUCTS = ['RAWS022_10', 'RAWS023_10', 'RAWS024_10', 'RAWS025_10',
                'RAWS026_10', 'RAWS027_10', 'RAWS028_10', 'RAWS035_10',
                'RAWS036_10']

    def __init__(self, logger, job_config, scenario_config: dict):
        super().__init__(logger, job_config, scenario_config)

    def _generate_sliced_output(self, type):
        '''Generate slices for this data take. Slices start and stop on a fixed
        grid, aligned to ANX, so the first and last slice of a data take can be
        truncated.'''

        # TODO: Move to constants
        NON_SLICED_TYPES = ['RAWS022_10', 'RAWS023_10', 'RAWS024_10']

        tstart = self.start
        tend = self.stop
        if (type in NON_SLICED_TYPES):
            slice_size = tend - tstart
        else:
            slice_size = constants.SLICE_DURATION
        while tstart < tend:
            tslice = slice_size
            if tstart + tslice > tend:
                tslice = tend - tstart
            name_gen = product_name.ProductName()
            name_gen.setup(self.output_type, tstart, tstart + tslice, self.downlink, self.baseline_id)
            self.hdr.eop_identifier = name_gen.generate_path()
            self.hdr.validity_start = tstart
            self.hdr.validity_end = tstart + tslice
            self.hdr.downlink_date = self.downlink

            # Create directory and files
            dir_name = os.path.join(self.output_path, self.hdr.eop_identifier)
            os.makedirs(dir_name, exist_ok=True)
            self.logger.info('Create {}'.format(self.hdr.eop_identifier))
            file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
            self.hdr.write(file_name)
            file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
            self._generate_bin_file(file_name, self.size)

            tstart += tslice

    def generate_output(self):
        # Generate sliced versions of the input products
        pattern = 'RAW_[0-9]{3}_[0-9]{2}'
        if re.match(pattern, self.input_type):
            output_type = list(str(self.input_type))
            output_type[3] = 'S'
            self.output_type = ''.join(output_type)
            self._generate_sliced_output(self.output_type)


class Sx_RAW__0x_generator(ProductGeneratorBase):
    '''Level-0 slice based products generation. For all products:
        Copies MPH content, but sets the data_take identifier.
    TODO: Where to get this value from...?'''
    PRODUCTS = ['S1_RAW__0S', 'S1_RAWP_0M', 'S1_RAW__0M',
                'S2_RAW__0S', 'S2_RAWP_0M', 'S2_RAW__0M',
                'S3_RAW__0S', 'S3_RAWP_0M', 'S3_RAW__0M',
                'RO_RAW__0S', 'RO_RAWP_0M',
                'EC_RAW__0S', 'EC_RAWP_0M']

    def __init__(self, logger, job_config, scenario_config: dict):
        super().__init__(logger, job_config, scenario_config)

    def generate_output(self):
        # Level 0 standard product
        name_gen = product_name.ProductName()
        tdownlink = datetime.datetime.now()  # TODO!
        name_gen.setup(self.output_type, self.start, self.stop, tdownlink, self.baseline_id)

        # TODO: Just copy from input MPH!
        self.hdr.eop_identifier = name_gen.generate_path()
        self.hdr.validity_start = self.start
        self.hdr.validity_end = self.stop
        # self.hdr.downlink_date = self.downlink

        # Create directory and files
        dir_name = os.path.join(self.output_path, self.hdr.eop_identifier)
        os.makedirs(dir_name, exist_ok=True)
        self.logger.info('Create {}'.format(self.hdr.eop_identifier))

        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self.hdr.write(file_name)

        # H/V measurement data
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxh'))
        self._generate_bin_file(file_name, self.size//2)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxv'))
        self._generate_bin_file(file_name, self.size//2)

        # Ancillary products, low rate
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxh'))
        self._generate_bin_file(file_name)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxv'))
        self._generate_bin_file(file_name)

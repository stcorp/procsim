'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 0 output product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0045
'''
import datetime
import os
import re

from biomass import constants
from biomass import product_name
from biomass import mph


def _generate_bin_file(file_name, size=0):
    file = open(file_name, 'wb')
    hdr = bytes('procsim dummy binary', 'utf-8') + b'\0'
    file.write(hdr)
    file.write(os.urandom(max(size - len(hdr), 0)))


class RAWSxxx_10():
    '''Raw slice-based products generation. The slice validity start/stop times
    are set.'''
    def __init__(self, output_path, logger, size):
        self.output_path = output_path
        self.logger = logger
        self.size = size
        self.input_type = None
        self.output_type = None
        self.start: datetime.datetime
        self.stop: datetime.datetime
        self.downlink: datetime.datetime
        self.baseline_id = 1
        self.hdr = mph.MainProductHeader()

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
            _generate_bin_file(file_name, self.size)

            tstart += tslice

    def parse_inputs(self, input_files):
        # Extract information from input files.
        # First determine input file type, using the directory name.
        gen = product_name.ProductName()
        for file in input_files:
            if gen.parse_path(file):
                self.input_type = gen.file_type
                self.start = gen.start_time
                self.stop = gen.stop_time
                self.downlink = gen.downlink_time
                self.baseline_id = gen.baseline_identifier
            else:
                self.logger.error('Filename {} not valid for Biomass'.format(file))
                return False
        return True

    def generate_output(self):
        # Generate sliced versions of the input products
        pattern = 'RAW_[0-9]{3}_[0-9]{2}'
        if re.match(pattern, self.input_type):
            output_type = list(str(self.input_type))
            output_type[3] = 'S'
            self.output_type = ''.join(output_type)
            self._generate_sliced_output(self.output_type)


class Sx_RAW__0x_generator():
    '''Level-0 slice based products generation. Produce types:
        - Sx_RAW__0S    Stripmap Standard
        - Sx_RAWP_0M
        - RO_RAW__0S
        - RO_RAWP_0M
        - EC_RAW__0S
        - EC_RAWP_0M
    Copies MPH content, but sets the data_take identifier.
    TODO: Where to get this value from...?'''

    def __init__(self, output_path, logger, output_type, size):
        self.output_path = output_path
        self.logger = logger
        self.input_type = None
        self.start: datetime.datetime
        self.stop: datetime.datetime
        self.downlink: datetime.datetime
        self.baseline_id = 1
        self.hdr = mph.MainProductHeader()
        self.output_type = output_type
        self.size = size

    def parse_inputs(self, input_files) -> bool:
        # Determine input file type, using the directory name.
        gen = product_name.ProductName()
        for file in input_files:
            if gen.parse_path(file):
                self.input_type = gen.file_type
                self.start = gen.start_time
                self.stop = gen.stop_time
                self.baseline_id = gen.baseline_identifier
                if (gen.get_level() == 'raw'):
                    self.downlink = gen.downlink_time
            else:
                self.logger.error('Filename {} not valid for Biomass'.format(file))
                return False
        return True

    def generate_output(self):
        # Level 0 standard product

        # TODO
        output_type = ''
        if self.output_type == 'Sx_RAW__0S':
            output_type = 'S1_RAW__0S'
        elif self.output_type == 'Sx_RAWP_0M':
            output_type = 'S1_RAWP_0M'
        elif self.output_type == 'Sx_RAW__0M':
            output_type = 'S1_RAW__0M'

        name_gen = product_name.ProductName()
        tdownlink = datetime.datetime.now()  # TODO!
        name_gen.setup(output_type, self.start, self.stop, tdownlink, self.baseline_id)

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
        _generate_bin_file(file_name, self.size//2)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxv'))
        _generate_bin_file(file_name, self.size//2)

        # Ancillary products, low rate
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxh'))
        _generate_bin_file(file_name)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxv'))
        _generate_bin_file(file_name)


def OutputGeneratorFactory(path, logger, type, size):
    generator = None
    if type in ['RAWSxxx_10']:
        generator = RAWSxxx_10(path, logger, size)
    elif type in ['Sx_RAW__0S', 'Sx_RAWP_0M', 'Sx_RAW__0M']:
        generator = Sx_RAW__0x_generator(path, logger, type, size)
    else:
        logger.error('No generator for type {} in this plugin'.format(type))
    return generator

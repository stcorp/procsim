'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 0 processor simulator
'''
import datetime
import os
import re

from biomass import constants
from biomass import product_name
from biomass import mph


class Step1():
    '''Raw slice-based products generation. The slice validity start/stop times
    are set.'''
    def __init__(self, output_path, logger):
        self.output_path = output_path
        self.logger = logger
        self.input_type = None
        self.output_type = None
        self.start: datetime.datetime
        self.stop: datetime.datetime
        self.downlink: datetime.datetime
        self.baseline_id = 1
        self.hdr = mph.MainProductHeader()

    def _generate_bin_file(self, file_name):
        file = open(file_name, 'w')
        file.write('test')

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
            file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
            self.hdr.write(file_name)
            file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
            self._generate_bin_file(file_name)
            print('Created directory {}'.format(dir_name))

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

    def generate_outputs(self):
        # Generate sliced versions of the input products
        pattern = 'RAW_[0-9]{3}_[0-9]{2}'
        if re.match(pattern, self.input_type):
            output_type = list(str(self.input_type))
            output_type[3] = 'S'
            self.output_type = ''.join(output_type)
            self._generate_sliced_output(self.output_type)


class Step2():
    '''Level-0 slice based products generation. Produce types:
        - Sx_RAW__0S
        - Sx_RAWP_0M
        - RO_RAW__0S
        - RO_RAWP_0M
        - EC_RAW__0S
        - EC_RAW_0M
    Copies MPH content, but sets the data_take identifier.
    TODO: Where to get this value from...?'''

    def __init__(self, output_path, logger):
        self.output_path = output_path
        self.logger = logger
        self.input_type = None
        self.start
        self.stop
        self.downlink
        self.baseline_id = 1
        self.hdr = mph.MainProductHeader()

    def _generate_bin_file(self, file_name):
        file = open(file_name, 'w')
        file.write('test')

    def parse_inputs(self, input_files) -> bool:
        # Determine input file type, using the directory name.
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

    def generate_outputs(self):
        output_types = ['S1_RAW__0S', 'S1_RAWP_0M']
        name_gen = product_name.ProductName()
        for output_type in output_types:
            # TODO: Add slice nr, mission phase etc.
            name_gen.setup(output_type, self.start, self.stop, self.downlink, self.baseline_id)

            # TODO: Just copy from input MPH!
            self.hdr.eop_identifier = name_gen.generate_path()
            self.hdr.validity_start = self.start
            self.hdr.validity_end = self.stop
            self.hdr.downlink_date = self.downlink

            # Create directory and files
            dir_name = os.path.join(self.output_path, self.hdr.eop_identifier)
            os.makedirs(dir_name, exist_ok=True)
            file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
            self.hdr.write(file_name)
            file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
            self._generate_bin_file(file_name)
            print('Created directory {}'.format(dir_name))


class Step3():
    '''Consolidation of Monitoring products. Produce types:
        - Sx_RAW__0M
        - RO_RAW__0M
        - EC_RAW__0M
    Copies MPH content, no further actions.'''
    def __init__(self, output_path, logger):
        self.output_path = output_path
        self.logger = logger
        self.input_type = None
        self.start: datetime.datetime
        self.stop: datetime.datetime
        self.downlink: datetime.datetime
        self.baseline_id = 1
        self.hdr = mph.MainProductHeader()

    def _generate_bin_file(self, file_name):
        file = open(file_name, 'w')
        file.write('test')

    def parse_inputs(self, input_files) -> bool:
        # Determine input file type, using the directory name.
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

    def generate_outputs(self):
        output_types = ['S1_RAW__0M']
        name_gen = product_name.ProductName()
        for output_type in output_types:
            # TODO: Add slice nr, mission phase etc.
            name_gen.setup(output_type, self.start, self.stop, self.downlink, self.baseline_id)

            # TODO: Just copy from input MPH!
            self.hdr.eop_identifier = name_gen.generate_path()
            self.hdr.validity_start = self.start
            self.hdr.validity_end = self.stop
            self.hdr.downlink_date = self.downlink

            # Create directory and files
            dir_name = os.path.join(self.output_path, self.hdr.eop_identifier)
            os.makedirs(dir_name, exist_ok=True)
            file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
            self.hdr.write(file_name)
            file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
            self._generate_bin_file(file_name)
            print('Created directory {}'.format(dir_name))

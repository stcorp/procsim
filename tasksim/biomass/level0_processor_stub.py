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
    '''Raw products are cut into slices'''
    def __init__(self, output_path):
        self.output_path = output_path
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
        grid, so the first and last slice of a data take can be truncated.'''
        tstart = self.start
        tend = self.stop
        while tstart < tend:
            tslice = constants.SLICE_DURATION
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

    def generate_outputs(self):
        # Generate sliced versions of the input products
        pattern = 'RAW_[0-9]{3}_[0-9]{2}'
        if re.match(pattern, self.input_type):
            output_type = list(str(self.input_type))
            output_type[3] = 'S'
            self.output_type = ''.join(output_type)
            self._generate_sliced_output(self.output_type)

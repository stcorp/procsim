'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 0 processor simulator
'''
import datetime
import re
from biomass import constants
from biomass import product_name


def generate_slices(self, tstart, tend):
    '''Generate slices for this data take. Slices start and stop on a fixed
    grid, so the first and last slice of a data take can be truncated.'''
    while tstart < tend:
        tslice = constants.SLICE_DURATION
        if tstart + tslice > tend:
            tslice = tend - tstart
        print('TODO: Generate slice from {} len {}'.format(tstart, tslice))
        tstart += tslice


class Step1():
    '''Raw products are cut into slices'''
    def __init__(self):
        self.input_type = None
        self.output_type = None
        self.start: datetime.datetime
        self.stop: datetime.datetime

    def _generate_sliced_output(self, type):
        '''Generate slices for this data take. Slices start and stop on a fixed
        grid, so the first and last slice of a data take can be truncated.'''
        tstart = self.start
        tend = self.stop
        while tstart < tend:
            tslice = constants.SLICE_DURATION
            if tstart + tslice > tend:
                tslice = tend - tstart
            print('Generate slice from {} len {}'.format(tstart, tslice))
            tstart += tslice
            pass

    def parse_inputs(self, input_files):
        # Extract information from input files.
        # First determine input file type, using the directory name.
        gen = product_name.ProductName()
        for file in input_files:
            if gen.parse_path(file):
                self.input_type = gen.file_type
                self.start = gen.start_time
                self.stop = gen.stop_time

    def generate_outputs(self):
        # Generate sliced versions of the input products
        pattern = 'RAW_[0-9]{3}_[0-9]{2}'
        if re.match(pattern, self.input_type):
            output_type = list(str(self.input_type))
            output_type[3] = 'S'
            self.output_type = ''.join(output_type)
            self._generate_sliced_output(self.output_type)

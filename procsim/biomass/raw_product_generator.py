'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw output product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0073
'''
import datetime
import os

from biomass import constants, product_name
from biomass import product_generator

ISO_TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'
ISO_TIME_FORMAT_SHORT = '%Y-%m-%d %H:%M:%S'


def _time_from_iso(timestr):
    timestr = timestr[:-1]  # strip 'Z'
    return datetime.datetime.strptime(timestr, ISO_TIME_FORMAT)


class RAWSxxx_10(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    the raw slice-based products generation.

    Slicing is done using a slice grid aligned to ANX.
    For every slice, the following metadata is set:
    - validTime start/stop times
    - wrsLatitudeGrid, the slice number.
    '''

    PRODUCTS = ['RAWS022_10', 'RAWS023_10', 'RAWS024_10', 'RAWS025_10',
                'RAWS026_10', 'RAWS027_10', 'RAWS028_10', 'RAWS035_10',
                'RAWS036_10']

    def __init__(self, logger, job_config, scenario_config: dict):
        super().__init__(logger, job_config, scenario_config)
        self.anx = _time_from_iso(scenario_config.get('anx'))
        self.enable_slicing = scenario_config.get('enable_slicing', True)

    def _generate_sliced_output(self, type):
        self.create_date = self.hdr.begin_position   # HACK: fill in current date!
        tstart = self.hdr.begin_position
        tend = self.hdr.end_position
        slice_nr = 1
        if self.enable_slicing:
            slice_size = constants.SLICE_DURATION - (tstart - self.anx) % constants.SLICE_DURATION
        else:
            slice_size = tend - tstart

        while tstart < tend:
            tslice = slice_size
            if tstart + tslice > tend:
                tslice = tend - tstart
            slice_size = constants.SLICE_DURATION

            # Construct product name and set metadata fields
            name_gen = product_name.ProductName()
            name_gen.setup(self.output_type, tstart, tstart + tslice, self.baseline_id, self.create_date, self.downlink)
            self.hdr.set_product_type(self.output_type)
            self.hdr.eop_identifier = name_gen.generate_path_name()
            self.hdr.validity_start = tstart
            self.hdr.validity_end = tstart + tslice
            self.hdr.acquisitions[0].slice_frame_nr = slice_nr
            slice_nr = slice_nr + 1

            # Create directory with files
            dir_name = os.path.join(self.output_path, self.hdr.eop_identifier)
            os.makedirs(dir_name, exist_ok=True)
            self.logger.info('Create {}'.format(self.hdr.eop_identifier))
            file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
            self.hdr.write(file_name)
            file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
            self._generate_bin_file(file_name, self.size)

            tstart += tslice

    def generate_output(self):
        self._generate_sliced_output(self.output_type)

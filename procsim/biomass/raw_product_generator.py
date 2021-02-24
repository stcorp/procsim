'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw output product generators, according to BIO-ESA-EOPG-EEGS-TN-0073
'''
import bisect
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

    Slicing is done using a slice grid, aligned to ANX.
    '''

    PRODUCTS = ['RAWS022_10', 'RAWS023_10', 'RAWS024_10', 'RAWS025_10',
                'RAWS026_10', 'RAWS027_10', 'RAWS028_10', 'RAWS035_10',
                'RAWS036_10']

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        # Get anx list from config. Can be located at either scenario or product level
        anx_list = output_config.get('anx') or scenario_config.get('anx')
        if anx_list is None:
            raise Exception('ANX must be configured for RAWSxxx_10 product')
        self.anx_list = [_time_from_iso(anx) for anx in anx_list]
        self.anx_list.sort()
        self.enable_slicing = output_config.get('enable_slicing', True)

    def generate_output(self):
        self.create_date = self.start   # HACK: fill in current date?
        if self.enable_slicing:
            self._generate_sliced_output()
        else:
            self._create_product(self.start, self.stop, None)

    def _create_product(self, tstart, tend, slice_nr):
        # Construct product name and set metadata fields
        name_gen = product_name.ProductName()
        name_gen.setup(self.output_type, tstart, tend, self.baseline_id, self.create_date, self.downlink)
        dir_name = name_gen.generate_path_name()
        self.hdr.set_product_type(self.output_type, self.baseline_id)
        self.hdr.set_product_filename(dir_name)
        self.hdr.set_validity_times(tstart, tend)
        self.hdr.set_slice_nr(slice_nr)

        # create directory with files
        # self.logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self.output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)
        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self.hdr.write(file_name)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
        self._generate_bin_file(file_name, self.size)

    def _get_anx(self, t):
        # Returns the latest ANX before the given time
        idx = bisect.bisect(self.anx_list, t) - 1  # anx_list[idx-1] <= tstart
        return self.anx_list[min(max(idx, 0), len(self.anx_list) - 1)]

    def _generate_sliced_output(self):
        acq_start, acq_end = self.hdr.get_phenomenon_times()
        slice_start = acq_start
        end_overlapped = acq_start
        anx = self._get_anx(slice_start)
        while end_overlapped < acq_end:
            # Calculate slice size and slice nr.
            slice_size = constants.SLICE_GRID_SPACING - (slice_start - anx) % constants.SLICE_GRID_SPACING
            slice_nr = 1 + ((slice_start - anx) // constants.SLICE_GRID_SPACING) % constants.SLICES_PER_ORBIT

            # Add start/end overlap, but clamp to acquisition start/stop
            start_overlapped = max(slice_start - constants.SLICE_OVERLAP_START, acq_start)
            end_overlapped = min(slice_start + slice_size + constants.SLICE_OVERLAP_END, acq_end)

            # Generate product
            self._create_product(start_overlapped, end_overlapped, slice_nr)

            # Align start of next slice to the grid.
            # If the end of the previous slice (including overlap) falls after a
            # 'new' ANX, use that ANX to align the start of this slice.
            # This ensures that slice #1 is aligned to the 'new' ANX, while
            # slice #62 was aligned to the 'old' ANX.
            anx = self._get_anx(end_overlapped)
            n = ((end_overlapped - anx) // constants.SLICE_GRID_SPACING)
            slice_start = anx + n * constants.SLICE_GRID_SPACING

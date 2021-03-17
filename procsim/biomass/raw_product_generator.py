'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw output product generators, according to BIO-ESA-EOPG-EEGS-TN-0073
'''
import bisect
import datetime
import os
import shutil
import zipfile
from typing import List

from exceptions import ScenarioError
from biomass import constants, product_generator, product_name


class RawProductGeneratorBase(product_generator.ProductGeneratorBase):

    def _create_raw_product(self, dir_name, name_gen):
        self._logger.debug('Output directory is {}'.format(self._output_path))
        self._logger.info('Create {}'.format(dir_name))
        full_dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(full_dir_name, exist_ok=True)
        mph_file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        full_mph_file_name = os.path.join(self._output_path, mph_file_name)
        self.hdr.write(full_mph_file_name)
        bin_file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
        full_bin_file_name = os.path.join(self._output_path, bin_file_name)
        self._generate_bin_file(full_bin_file_name, self._size_mb)
        # TODO: Zip optional?
        self._zip_directory(full_dir_name, [full_mph_file_name, full_bin_file_name], [mph_file_name, bin_file_name])

    def _zip_directory(self, dir_name: str, filenames: List[str], arcnames: List[str]):
        # Note: Deletes input files afterwards
        self._logger.debug('Archive to .zip')
        with zipfile.ZipFile(dir_name + '.zip', 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            for filename, arcname in zip(filenames, arcnames):
                zipped.write(filename, arcname)
            zipped.close()
            shutil.rmtree(dir_name)


class RAW_xxx_10(RawProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    the raw products generation.
    '''
    PRODUCTS = ['RAW_022_10', 'RAW_023_10', 'RAW_024_10', 'RAW_025_10',
                'RAW_026_10', 'RAW_027_10', 'RAW_028_10', 'RAW_035_10',
                'RAW_036_10']

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

    def generate_output(self):
        # Base class is doing part of the setup
        super(RAW_xxx_10, self).generate_output()

        create_date = self.hdr.validity_start   # HACK: fill in current date?
        start = self.hdr.validity_start
        stop = self.hdr.validity_stop

        # Construct product name and set metadata fields
        name_gen = product_name.ProductName()
        name_gen.file_type = self._output_type
        name_gen.start_time = start
        name_gen.stop_time = stop
        name_gen.baseline_identifier = self.hdr.product_baseline
        name_gen.set_creation_date(create_date)
        name_gen.downlink_time = self.hdr.acquisition_date

        dir_name = name_gen.generate_path_name()
        self.hdr.product_type = self._output_type
        self.hdr.set_product_filename(dir_name)
        self.hdr.set_phenomenon_times(start, stop)

        self._create_raw_product(dir_name, name_gen)


class RAWSxxx_10(RawProductGeneratorBase):
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
            raise ScenarioError('ANX must be configured for RAWSxxx_10 product')
        self.anx_list = [self._time_from_iso(anx) for anx in anx_list]
        self.anx_list.sort()
        self.enable_slicing = output_config.get('enable_slicing', True)

    def generate_output(self):
        super(RAWSxxx_10, self).generate_output()

        self._create_date = self.hdr.validity_start   # HACK: fill in current date?
        if self.enable_slicing:
            self._generate_sliced_output()
        else:
            self._create_product(self.hdr.validity_start, self.hdr.validity_stop, None)

    def _create_product(self, tstart, tstop, slice_nr):
        # Construct product name and set metadata fields
        name_gen = product_name.ProductName()
        name_gen.file_type = self._output_type
        name_gen.start_time = tstart
        name_gen.stop_time = tstop
        name_gen.baseline_identifier = self.hdr.product_baseline
        name_gen.set_creation_date(self._create_date)
        name_gen.downlink_time = self.hdr.acquisition_date

        dir_name = name_gen.generate_path_name()
        self.hdr.product_type = self._output_type
        self.hdr.set_product_filename(dir_name)
        self.hdr.set_validity_times(tstart, tstop)

        self._create_raw_product(dir_name, name_gen)

    def _get_anx(self, t):
        # Returns the latest ANX before the given time
        idx = bisect.bisect(self.anx_list, t) - 1  # anx_list[idx-1] <= tstart
        return self.anx_list[min(max(idx, 0), len(self.anx_list) - 1)]

    def _generate_sliced_output(self):
        acq_start = self.hdr.begin_position
        acq_end = self.hdr.end_position
        if acq_start is None or acq_end is None:
            self._logger.error('Phenomenon begin/end must be known')
            return
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

            # Generate product.
            # Assumption: start/stop validity times are WITHOUT overlap. The
            # overlap is only in the raw data.
            end_non_overlapped = min(slice_start + slice_size, acq_end)
            self._create_product(slice_start, end_non_overlapped, slice_nr)
            self._logger.debug('Create product {}-{}'.format(slice_start, end_non_overlapped))

            # Align start of next slice to the grid.
            # If the end of the previous slice (including overlap) falls after a
            # 'new' ANX, use that ANX to align the start of this slice.
            # This ensures that slice #1 is aligned to the 'new' ANX, while
            # slice #62 was aligned to the 'old' ANX.
            anx = self._get_anx(end_overlapped)
            n = ((end_overlapped - anx) // constants.SLICE_GRID_SPACING)
            slice_start = anx + n * constants.SLICE_GRID_SPACING

'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw output product generators, according to BIO-ESA-EOPG-EEGS-TN-0073
'''
import bisect
from datetime import timedelta
import os
import shutil
import zipfile
from typing import List

from procsim.core.exceptions import ScenarioError

from . import constants, product_generator, product_name

_GENERATOR_PARAMS = [
    ('zip_output', '_zip_output', 'bool')
]
_HDR_PARAMS = [
    ('acquisition_date', 'acquisition_date', 'date'),
    ('acquisition_station', 'acquisition_station', 'str'),
    ('num_isp', 'nr_instrument_source_packets', 'int'),
    ('num_isp_erroneous', 'nr_instrument_source_packets_erroneous', 'int'),
    ('num_isp_corrupt', 'nr_instrument_source_packets_corrupt', 'int')
]
_ACQ_PARAMS = []


class RawProductGeneratorBase(product_generator.ProductGeneratorBase):
    '''
    This abstract class is responsible for creating raw products and is used as
    base class for the specific raw product generators.
    '''
    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._zip_output = False

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + _GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def _create_raw_product(self, dir_name, name_gen):
        self._logger.info('Create {}'.format(dir_name))
        full_dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(full_dir_name, exist_ok=True)

        bin_file_name = name_gen.generate_binary_file_name()
        full_bin_file_name = os.path.join(full_dir_name, bin_file_name)
        self._add_file_to_product(full_bin_file_name, self._size_mb)
        
        mph_file_name = name_gen.generate_mph_file_name()
        full_mph_file_name = os.path.join(full_dir_name, mph_file_name)
        self._hdr.write(full_mph_file_name)

        if self._zip_output:
            arc_mph_file_name = os.path.join(dir_name, mph_file_name)
            arc_bin_file_name = os.path.join(dir_name, bin_file_name)
            self._zip_directory(full_dir_name, [full_mph_file_name, full_bin_file_name], [arc_mph_file_name, arc_bin_file_name])

    def _zip_directory(self, dir_name: str, filenames: List[str], arcnames: List[str]):
        # Note: Deletes input files afterwards
        self._logger.debug('Archive to zip, extension {}'.format(self._zip_extension))
        with zipfile.ZipFile(dir_name + self._zip_extension, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            for filename, arcname in zip(filenames, arcnames):
                zipped.write(filename, arcname)
            zipped.close()
            shutil.rmtree(dir_name)


class RAW_xxx_10(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw products generation.
    '''
    PRODUCTS = ['RAW_022_10', 'RAW_023_10', 'RAW_024_10', 'RAW_025_10',
                'RAW_026_10', 'RAW_027_10', 'RAW_028_10', 'RAW_035_10',
                'RAW_036_10']

    HDR_PARAMS = [
        ('begin_position', 'begin_position', 'date'),
        ('end_position', 'end_position', 'date'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen, hdr + self.HDR_PARAMS, acq

    def generate_output(self):
        # Base class is doing part of the setup
        super().generate_output()

        start = self._hdr.begin_position
        stop = self._hdr.end_position

        # Construct product name and set metadata fields
        name_gen = product_name.ProductName(self._compact_creation_date_epoch)
        name_gen.file_type = self._output_type
        name_gen.start_time = start
        name_gen.stop_time = stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(self._creation_date)
        name_gen.downlink_time = self._hdr.acquisition_date

        dir_name = name_gen.generate_path_name()
        self._hdr.product_type = self._output_type
        self._hdr.set_product_filename(dir_name)
        self._hdr.set_validity_times(start, stop)

        self._create_raw_product(dir_name, name_gen)


class RAWSxxx_10(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw slice-based products generation.

    The acquisition period (phenomenon begin/end times) of the metadata_source
    (i.e. a RAW_xxx_10 product) is sliced. The slice grid is aligned to ANX.
    An array "anx" with one or more ANX times must be specified in the scenario.
    For example:

      "anx": [
        "2021-02-01T00:25:33.745Z",
        "2021-02-01T02:03:43.725Z"
      ],

    'Special' cases:
    - ANX falls within an acquisition. Slice 62 ends at the grid defined by
        the 'old' ANX, slice 1 starts at the 'new' ANX.
    - Acquisition starts with Tstart <= slice_minimum_duration before the end of
        slice n. The first slice will be slice n+1, with the acquisition
        starting at Tstart.
    - Acquisition ends with Tend <= slice_minimum_duration after the end of
        slice n. Slice n ends at Tend.

    The generator adjusts the following metadata:
    - phenomenonTime, acquisition begin/end times.
    - validTime, theoretical slice begin/end times (including overlap).
    - wrsLatitudeGrid, aka the slice_frame_nr.
    '''

    PRODUCTS = ['RAWS022_10', 'RAWS023_10', 'RAWS024_10', 'RAWS025_10',
                'RAWS026_10', 'RAWS027_10', 'RAWS028_10', 'RAWS035_10',
                'RAWS036_10']

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool'),
        ('slice_grid_spacing', '_slice_grid_spacing', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
        ('slice_minimum_duration', '_slice_minimum_duration', 'float'),
        ('orbital_period', '_orbital_period', 'float')
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        # Get anx list from config. Can be located at either scenario or product level
        anx_list = output_config.get('anx') or scenario_config.get('anx')
        if anx_list is None:
            raise ScenarioError('ANX must be configured for RAWSxxx_10 product')
        self._anx_list = [self._time_from_iso(anx) for anx in anx_list]
        self._anx_list.sort()
        self._enable_slicing = True
        self._slice_grid_spacing = constants.SLICE_GRID_SPACING
        self._slice_overlap_start = constants.SLICE_OVERLAP_START
        self._slice_overlap_end = constants.SLICE_OVERLAP_END
        self._slice_minimum_duration = constants.SLICE_MINIMUM_DURATION
        self._orbital_period = constants.ORBITAL_PERIOD

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr, acq

    def generate_output(self):
        super(RAWSxxx_10, self).generate_output()

        if self._enable_slicing:
            self._generate_sliced_output()
        else:
            self._create_product(self._hdr.begin_position, self._hdr.end_position)

    def _create_product(self, acq_start, acq_stop):
        # Construct product name and set metadata fields
        name_gen = product_name.ProductName(self._compact_creation_date_epoch)
        name_gen.file_type = self._output_type
        name_gen.start_time = acq_start
        name_gen.stop_time = acq_stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(self._creation_date)
        name_gen.downlink_time = self._hdr.acquisition_date

        dir_name = name_gen.generate_path_name()
        self._hdr.product_type = self._output_type
        self._hdr.set_product_filename(dir_name)
        self._hdr.set_phenomenon_times(acq_start, acq_stop)

        self._create_raw_product(dir_name, name_gen)

    def _get_anx(self, t):
        # Returns the latest ANX before the given time
        idx = bisect.bisect(self._anx_list, t) - 1
        return self._anx_list[min(max(idx, 0), len(self._anx_list) - 1)]

    def _generate_sliced_output(self):
        segment_start = self._hdr.begin_position
        segment_end = self._hdr.end_position
        if segment_start is None or segment_end is None:
            self._logger.error('Phenomenon begin/end times must be known')
            return

        start = segment_start
        sigma = timedelta(0, 1.0)   # Just a small time delta (wrt to the slice duration)
        slices_per_orbit = int(round(self._orbital_period / self._slice_grid_spacing))
        while start < segment_end:
            # Find slice nr for this start time
            anx = self._get_anx(start + sigma)
            n = (start + sigma - anx) // self._slice_grid_spacing

            # Calculate slice start/end, phenomenon start/end (aka acquisition start/end)
            # and validity start/end, which is the slice start/end time with the lead/trail
            # overlap times added.
            slice_start = anx + n * self._slice_grid_spacing
            slice_end = anx + (n + 1) * self._slice_grid_spacing
            validity_start = slice_start - self._slice_overlap_start
            validity_end = slice_end + self._slice_overlap_end
            acq_start = max(validity_start, segment_start)
            acq_end = min(validity_end, segment_end)

            # Additional rule:
            # "Two consecutive slices of the same product type shall be merged into a single one
            # if the sensing duration of one of them is lower than a configurable threshold.
            # The requirement only applies to consecutive slices at the beginning and at the end
            # of a data take or in case of incomplete slices."

            # Merge with next slice if too short and first slice.
            acq_duration = acq_end - acq_start
            if acq_duration < self._slice_minimum_duration and acq_start != validity_start:
                # Find slice nr for the next slice
                previous_n = n
                anx = self._get_anx(slice_end + sigma)
                n = (slice_end + sigma - anx) // self._slice_grid_spacing
                slice_end = anx + (n + 1) * self._slice_grid_spacing
                validity_end = slice_end + self._slice_overlap_end
                acq_end = min(validity_end, segment_end)
                self._logger.debug('First slice #{} ({}s) is shorter than {}s, merged to #{}.'.format(
                    previous_n + 1,
                    acq_duration.seconds,
                    self._slice_minimum_duration.seconds,
                    n + 1
                ))

            # Is this the last slice? If not, check if next slice will be too short,
            # merge with this slice in that case.
            if segment_end > slice_end:
                next_anx = self._get_anx(slice_end + sigma)
                next_n = (slice_end + sigma - next_anx) // self._slice_grid_spacing
                next_slice_start = next_anx + next_n * self._slice_grid_spacing
                next_slice_end = next_anx + (next_n + 1) * self._slice_grid_spacing
                next_validity_start = next_slice_start - self._slice_overlap_start
                next_validity_end = next_slice_end + self._slice_overlap_end
                next_acq_start = max(next_validity_start, segment_start)
                next_acq_end = min(next_validity_end, segment_end)
                next_slice_duration = next_acq_end - next_acq_start
                if next_slice_duration < self._slice_minimum_duration and next_acq_end != next_slice_end:
                    slice_end = next_slice_end
                    validity_end = next_validity_end
                    acq_end = next_acq_end
                    self._logger.debug('Last slice #{} ({}s) is shorter than {}s, merged with {}.'.format(
                        next_n + 1,
                        next_slice_duration.seconds,
                        self._slice_minimum_duration.seconds,
                        n + 1
                    ))

            slice_nr = (n % slices_per_orbit) + 1
            self._hdr.acquisitions[0].slice_frame_nr = slice_nr
            self._hdr.set_validity_times(validity_start, validity_end)
            self._logger.debug('Create slice #{}, acq {}-{}, validity {}-{} anx {}'.format(
                slice_nr,
                acq_start.strftime("%Y-%m-%d %H:%M:%S"),
                acq_end.strftime("%Y-%m-%d %H:%M:%S"),
                validity_start.strftime("%Y-%m-%d %H:%M:%S"),
                validity_end.strftime("%Y-%m-%d %H:%M:%S"),
                anx.strftime("%Y-%m-%d %H:%M:%S")
            ))
            self._create_product(acq_start, acq_end)

            start = slice_end

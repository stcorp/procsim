'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw output product generators, according to BIO-ESA-EOPG-EEGS-TN-0073
'''
import bisect
import datetime
import os
from typing import List, Tuple

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
            self.zip_folder(full_dir_name, self._zip_extension)


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
        self._hdr.initialize_product_list(dir_name)
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
        scenario_anx_list = output_config.get('anx', []) or scenario_config.get('anx', [])
        self._anx_list.extend([self._time_from_iso(anx) for anx in scenario_anx_list])
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
        self._hdr.initialize_product_list(dir_name)
        self._hdr.set_phenomenon_times(acq_start, acq_stop)

        self._create_raw_product(dir_name, name_gen)

    def _get_slice_edges(self, segment_start: datetime.datetime, segment_end: datetime.datetime) -> List[Tuple[datetime.datetime, datetime.datetime]]:
        # If insufficient ANX are specified, infer the others.
        anx_list = self._anx_list.copy()
        while segment_start < anx_list[0]:
            anx_list.insert(0, anx_list[0] - self._orbital_period)
        while segment_end > anx_list[-1]:
            anx_list.append(anx_list[-1] + self._orbital_period)

        # Find ANX list that covers the segment duration.
        anx_idx_start = bisect.bisect_right(anx_list, segment_start) - 1
        anx_idx_end = bisect.bisect_left(anx_list, segment_end) + 1

        # Determine the slices that make up the space between ANX.
        slice_edges = []
        slices_per_orbit = int(round(self._orbital_period / self._slice_grid_spacing))
        for anx in anx_list[anx_idx_start:anx_idx_end - 1]:
            new_slice_edges = [(anx + i * self._slice_grid_spacing, anx + (i + 1) * self._slice_grid_spacing) for i in range(slices_per_orbit)]
            slice_edges.extend(new_slice_edges)

        # Only keep the slices that overlap the segment.
        slice_edges = [slice for slice in slice_edges if slice[1] >= segment_start and slice[0] <= segment_end]

        # Merge the first and last slice with their neighbour if they are going to be too short.
        if slice_edges[0][1] - segment_start < self._slice_minimum_duration:
            slice_edges[1] = (slice_edges[0][0], slice_edges[1][1])
            del slice_edges[0]
        if segment_end - slice_edges[-1][0] < self._slice_minimum_duration:
            slice_edges[-2] = (slice_edges[-2][0], slice_edges[-1][1])
            del slice_edges[-1]

        return slice_edges

    def _generate_sliced_output(self) -> None:
        segment_start = self._hdr.begin_position
        segment_end = self._hdr.end_position
        if segment_start is None or segment_end is None:
            raise ScenarioError('Phenomenon begin/end times must be known')

        if not self._anx_list:
            raise ScenarioError('ANX must be configured for RAWSxxx_10 product, either in the scenario or orbit prediction file')

        slice_edges = self._get_slice_edges(segment_start, segment_end)

        for slice_start, slice_end in slice_edges:
            # Get the ANX and slice number from the middle of the slice to treat merged slices accurately.
            slice_middle = slice_start + (slice_end - slice_start) / 2
            anx = self._get_anx(slice_middle)
            slice_nr = self._get_slice_frame_nr(slice_middle, self._slice_grid_spacing)
            if anx is None or slice_nr is None:
                continue
            validity_start = slice_start - self._slice_overlap_start
            validity_end = slice_end + self._slice_overlap_end
            acq_start = max(validity_start, segment_start)
            acq_end = min(validity_end, segment_end)
            self._hdr.acquisitions[0].slice_frame_nr = slice_nr
            self._hdr.set_validity_times(validity_start, validity_end)
            self._logger.debug((f'Create slice #{slice_nr}\n'
                                f'  acq {acq_start}  -  {acq_end}\n'
                                f'  validity {validity_start}  -  {validity_end}\n'
                                f'  anx {anx}'))
            self._create_product(acq_start, acq_end)

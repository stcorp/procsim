'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex raw output product generators, according to ESA-EOPG-EOEP-TN-0027
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
    ('cycle_number', 'cycle_number', 'str'),
    ('relative_orbit_number', 'relative_orbit_number', 'str'),
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

        if self._output_type != 'RAW___HKTM':
            mph_file_name = name_gen.generate_mph_file_name()
            full_mph_file_name = os.path.join(full_dir_name, mph_file_name)
            self._hdr.write(full_mph_file_name)

        if self._zip_output:
            self.zip_folder(full_dir_name, self._zip_extension)

    def _create_name_generator(self, acq_start, acq_stop):
        name_gen = product_name.ProductName(self._compact_creation_date_epoch)

        name_gen.file_type = self._output_type
        name_gen.start_time = acq_start
        name_gen.stop_time = acq_stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(self._creation_date)
        name_gen.downlink_time = self._hdr.acquisition_date
        name_gen.cycle_number = self._hdr.cycle_number
        name_gen.relative_orbit_number = self._hdr.relative_orbit_number

        return name_gen


class UnslicedRawGeneratorBase(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw products generation.
    '''

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
        name_gen.sensor = 'HR1'  # TODO

        dir_name = name_gen.generate_path_name()
        self._hdr.product_type = self._output_type
        self._hdr.initialize_product_list(dir_name)
        self._hdr.set_validity_times(start, stop)

        self._create_raw_product(dir_name, name_gen)


class RAW(UnslicedRawGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    raw non-HKTM product generation.
    '''
    PRODUCTS = [
        'RAW_XS_LR_',
        'RAW_XS_HR1',
        'RAW_XS_HR2',
        'RAW_XS_OBC',
    ]

    HDR_PARAMS = [
        ('num_isp', 'nr_instrument_source_packets', 'int'),
        ('num_isp_erroneous', 'nr_instrument_source_packets_erroneous', 'int'),
        ('num_isp_corrupt', 'nr_instrument_source_packets_corrupt', 'int')
    ]

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen, hdr + self.HDR_PARAMS, acq


class RAW_HKTM(UnslicedRawGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    HKTM product generation.
    '''

    PRODUCTS = [
        'RAW___HKTM',
    ]

    HDR_PARAMS = [
        ('num_tf', 'nr_transfer_frames', 'int'),
        ('num_tf_erroneous', 'nr_transfer_frames_erroneous', 'int'),
        ('num_tf_corrupt', 'nr_transfer_frames_corrupt', 'int')
    ]

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen, hdr + self.HDR_PARAMS, acq


class RWS_EO(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw slice-based products generation.

    The acquisition period (phenomenon begin/end times) of the metadata_source
    (i.e. a RWS product) is sliced. The slice grid is aligned to ANX.
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

    An array "data_takes" with one or more data take objects can be specified
    in the scenario. Each data take object must contain at least the ID and
    start/stop times, and can contain other metadata fields. For example:

      "data_takes": [
        {
          "data_take_id": 15,
          "start": "2021-02-01T00:24:32.000Z",
          "stop": "2021-02-01T00:29:32.000Z",
          "swath": "S1",
          "operational_mode": "SM"  // example of an optional field
        },
    '''

    PRODUCTS = [
        'RWS_XS_OBS',
        'RWS_XSPOBS',
        'RWS_XSIOBS',
    ]

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool'),
        ('slice_grid_spacing', '_slice_grid_spacing', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
        ('slice_minimum_duration', '_slice_minimum_duration', 'float'),
        ('orbital_period', '_orbital_period', 'float'),
    ]

    HDR_PARAMS = [
        ('num_isp', 'nr_instrument_source_packets', 'int'),
        ('num_isp_erroneous', 'nr_instrument_source_packets_erroneous', 'int'),
        ('num_isp_corrupt', 'nr_instrument_source_packets_corrupt', 'int')
    ]

    ACQ_PARAMS = []

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._enable_slicing = True
        self._slice_grid_spacing = constants.SLICE_GRID_SPACING
        self._slice_overlap_start = constants.SLICE_OVERLAP_START
        self._slice_overlap_end = constants.SLICE_OVERLAP_END
        self._slice_minimum_duration = constants.SLICE_MINIMUM_DURATION
        self._orbital_period = constants.ORBITAL_PERIOD

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + self.HDR_PARAMS, acq + self.ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        data_takes_with_bounds = self._get_data_takes_with_bounds()
        for data_take_config, data_take_start, data_take_stop in data_takes_with_bounds:
            self.read_scenario_parameters(data_take_config)
            if self._enable_slicing:
                self._generate_sliced_output(data_take_config, data_take_start, data_take_stop)
            else:
                self._create_products(data_take_start, data_take_stop, True)  # TODO complete?

    def _create_products(self, acq_start: datetime.datetime, acq_stop: datetime.datetime, complete):
        name_gen = self._create_name_generator(acq_start, acq_stop)

        for sensor in ('LRES', 'HRE1', 'HRE2'):
            name_gen.sensor = sensor
            dir_name = name_gen.generate_path_name()
            self._hdr.product_type = self._output_type
            self._hdr.initialize_product_list(dir_name)
            self._hdr.set_phenomenon_times(acq_start, acq_stop)
            self._hdr.sensor_detector = {'LRES': 'LR', 'HRE1': 'HR1', 'HRE2': 'HR2'}[sensor]
            self._hdr.apid = self._scenario_config['apid']

            anx = self._get_anx(acq_start)
            if anx is not None:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = (acq_start - anx).total_seconds()
            else:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = 0  # TODO

            if complete:
                self._hdr.completeness_assesment = 'complete'
            else:
                self._hdr.completeness_assesment = 'partial'

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

    def _generate_sliced_output(self, data_take_config: dict, segment_start: datetime.datetime, segment_end: datetime.datetime) -> None:
        if segment_start is None or segment_end is None:
            raise ScenarioError('Phenomenon begin/end times must be known')

        if not self._anx_list:
            raise ScenarioError('ANX must be configured for RWS product, either in the scenario or orbit prediction file')

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
            self._hdr.set_validity_times(validity_start, validity_end)

            self._hdr.data_take_id = data_take_config['data_take_id']
            self._hdr.slice_frame_nr = slice_nr
            self._hdr.along_track_coordinate = int(self._slice_grid_spacing.seconds * (slice_nr-1))

            self._hdr.slice_start_position = 'on_grid'
            self._hdr.slice_stop_position = 'on_grid'

            self._logger.debug((f'Create slice #{slice_nr}\n'
                                f'  acq {acq_start}  -  {acq_end}\n'
                                f'  validity {validity_start}  -  {validity_end}\n'
                                f'  anx {anx}'))

            complete = (segment_start <= slice_start and slice_end <= segment_end)

            if complete:
                if self._output_type == 'RWS_XS_OBS':
                    self._create_products(slice_start, slice_end, complete)
            else:
                intermediate = data_take_config['intermediate']

                if segment_start > slice_start:
                    if intermediate:
                        self._hdr.slice_start_position = 'undetermined'  # TODO 'inside_SA'?
                    else:
                        self._hdr.slice_start_position = 'begin_of_SA'

                if segment_end < slice_end:
                    if intermediate:
                        self._hdr.slice_stop_position = 'undetermined'  # TODO 'inside_SA'?
                    else:
                        self._hdr.slice_stop_position = 'end_of_SA'

                if ((not intermediate and self._output_type == 'RWS_XSPOBS') or
                    (intermediate and self._output_type == 'RWS_XSIOBS')):
                    self._create_products(max(slice_start, segment_start), min(slice_end, segment_end), complete)


class RWS_CAL(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw slice-based products generation.

    The acquisition period (phenomenon begin/end times) of the metadata_source
    (i.e. a RWS product) is sliced. The slice grid is aligned to ANX.
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

    An array "data_takes" with one or more data take objects can be specified
    in the scenario. Each data take object must contain at least the ID and
    start/stop times, and can contain other metadata fields. For example:

      "data_takes": [
        {
          "data_take_id": 15,
          "start": "2021-02-01T00:24:32.000Z",
          "stop": "2021-02-01T00:29:32.000Z",
          "swath": "S1",
          "operational_mode": "SM"  // example of an optional field
        },
    '''

    PRODUCTS = [
        'RWS_XS_CAL',
        'RWS_XSPCAL',
        'RWS_XSICAL',
    ]

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool'),
        ('slice_grid_spacing', '_slice_grid_spacing', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
        ('slice_minimum_duration', '_slice_minimum_duration', 'float'),
        ('orbital_period', '_orbital_period', 'float'),
    ]

    HDR_PARAMS = [
        ('num_isp', 'nr_instrument_source_packets', 'int'),
        ('num_isp_erroneous', 'nr_instrument_source_packets_erroneous', 'int'),
        ('num_isp_corrupt', 'nr_instrument_source_packets_corrupt', 'int')
    ]

    ACQ_PARAMS = []

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._enable_slicing = True
        self._slice_grid_spacing = constants.SLICE_GRID_SPACING
        self._slice_overlap_start = constants.SLICE_OVERLAP_START
        self._slice_overlap_end = constants.SLICE_OVERLAP_END
        self._slice_minimum_duration = constants.SLICE_MINIMUM_DURATION
        self._orbital_period = constants.ORBITAL_PERIOD

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + self.HDR_PARAMS, acq + self.ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        for calibration_config in self._scenario_config['calibration_events']:
            self.read_scenario_parameters(calibration_config)
            cal_start = self._time_from_iso(calibration_config['start'])
            cal_stop = self._time_from_iso(calibration_config['stop'])

            begin_pos = self._hdr.begin_position
            end_pos = self._hdr.end_position
            if begin_pos is None or end_pos is None:
                raise ScenarioError('no begin_position or end_position')

            complete = (cal_start >= begin_pos and cal_stop <= end_pos)

            slice_start_position = 'begin_of_SA'
            slice_stop_position = 'end_of_SA'

            if complete:
                if self._output_type == 'RWS_XS_CAL':
                    self._create_products(calibration_config, cal_start, cal_stop, complete, slice_start_position, slice_stop_position)

            else:
                intermediate = calibration_config['intermediate']

                if cal_start > begin_pos:
                    if intermediate:
                        slice_start_position = 'undetermined'
                    slice_end_position = 'inside_SA'

                if cal_stop > end_pos:
                    if intermediate:
                        slice_stop_position = 'undetermined'
                    slice_start_position = 'inside_SA'

                cal_start = max(cal_start, begin_pos)
                cal_stop = min(cal_stop, end_pos)

                if ((not intermediate and self._output_type == 'RWS_XSPCAL') or
                    (intermediate and self._output_type == 'RWS_XSICAL')):
                    self._create_products(calibration_config, cal_start, cal_stop, complete, slice_start_position, slice_stop_position)

    def _create_products(self, calibration_config: dict, acq_start: datetime.datetime, acq_stop: datetime.datetime,
                         complete, slice_start_position, slice_stop_position):
        name_gen = self._create_name_generator(acq_start, acq_stop)

        for sensor in ('LRES', 'HRE1', 'HRE2'):
            name_gen.sensor = sensor
            dir_name = name_gen.generate_path_name()
            self._hdr.product_type = self._output_type
            self._hdr.initialize_product_list(dir_name)
            self._hdr.set_phenomenon_times(acq_start, acq_stop)
            self._hdr.set_validity_times(acq_start, acq_stop)
            self._hdr.acquisition_type = 'CALIBRATION'
            if complete:
                self._hdr.completeness_assesment = 'complete'
            else:
                self._hdr.completeness_assesment = 'partial'
            self._hdr.slice_start_position = slice_start_position
            self._hdr.slice_stop_position = slice_stop_position
            self._hdr.calibration_id = calibration_config['calibration_id']
            self._hdr.sensor_detector = {'LRES': 'LR', 'HRE1': 'HR1', 'HRE2': 'HR2'}[sensor]
            self._hdr.apid = self._scenario_config['apid']

            anx = self._get_anx(acq_start)
            if anx is not None:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = (acq_start - anx).total_seconds()
            else:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = 0  # TODO

            self._create_raw_product(dir_name, name_gen)


class RWS_ANC(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw slice-based products generation.

    The acquisition period (phenomenon begin/end times) of the metadata_source
    (i.e. a RWS product) is sliced. The slice grid is aligned to ANX.
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

    An array "data_takes" with one or more data take objects can be specified
    in the scenario. Each data take object must contain at least the ID and
    start/stop times, and can contain other metadata fields. For example:

      "data_takes": [
        {
          "data_take_id": 15,
          "start": "2021-02-01T00:24:32.000Z",
          "stop": "2021-02-01T00:29:32.000Z",
          "swath": "S1",
          "operational_mode": "SM"  // example of an optional field
        },
    '''

    PRODUCTS = [
        'RWS_XS_ANC',
        'RWS_XSPANC',
    ]

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool'),
        ('slice_grid_spacing', '_slice_grid_spacing', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
        ('slice_minimum_duration', '_slice_minimum_duration', 'float'),
        ('orbital_period', '_orbital_period', 'float'),
    ]

    HDR_PARAMS = [
        ('num_isp', 'nr_instrument_source_packets', 'int'),
        ('num_isp_erroneous', 'nr_instrument_source_packets_erroneous', 'int'),
        ('num_isp_corrupt', 'nr_instrument_source_packets_corrupt', 'int')
    ]

    ACQ_PARAMS = []

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._enable_slicing = True
        self._slice_grid_spacing = constants.SLICE_GRID_SPACING
        self._slice_overlap_start = constants.SLICE_OVERLAP_START
        self._slice_overlap_end = constants.SLICE_OVERLAP_END
        self._slice_minimum_duration = constants.SLICE_MINIMUM_DURATION
        self._orbital_period = constants.ORBITAL_PERIOD

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + self.HDR_PARAMS, acq + self.ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        anx = [self._time_from_iso(a) for a in self._scenario_config['anx']]

        for event in self._scenario_config['anc_events']:
            apid = event['apid']
            start = self._time_from_iso(event['start'])
            stop = self._time_from_iso(event['stop'])

            for i in range(len(anx)-1):
                # complete overlap of anx-to-anx window
                if start <= anx[i] and stop >= anx[i+1] and self._output_type == 'RWS_XS_ANC':
                    self._create_products(apid, anx[i], anx[i+1], True, 'anx', 'anx')

                # partial overlap of anx-to-anx window
                elif anx[i] <= start <= anx[i+1] and self._output_type == 'RWS_XSPANC':
                    self._create_products(apid, start, anx[i+1], False, 'inside_orb', 'anx')

                elif anx[i] <= stop <= anx[i+1] and self._output_type == 'RWS_XSPANC':
                    self._create_products(apid, anx[i], stop, False, 'anx', 'inside_orb')

    def _create_products(self, apid, acq_start: datetime.datetime, acq_stop: datetime.datetime, complete, slice_start_position, slice_stop_position):
        name_gen = self._create_name_generator(acq_start, acq_stop)

        for sensor in ('LRES', 'HRE1', 'HRE2'):
            name_gen.sensor = sensor
            dir_name = name_gen.generate_path_name()
            self._hdr.product_type = self._output_type
            self._hdr.initialize_product_list(dir_name)
            self._hdr.set_phenomenon_times(acq_start, acq_stop)
            self._hdr.set_validity_times(acq_start, acq_stop)
            self._hdr.acquisition_type = 'OTHER'
            if complete:
                self._hdr.completeness_assesment = 'complete'
            else:
                self._hdr.completeness_assesment = 'partial'
            self._hdr.slice_start_position = slice_start_position
            self._hdr.slice_stop_position = slice_stop_position
            self._hdr.sensor_detector = {'LRES': 'LR', 'HRE1': 'HR1', 'HRE2': 'HR2'}[sensor]
            self._hdr.apid = apid

            anx = self._get_anx(acq_start)
            if anx is not None:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = (acq_start - anx).total_seconds()
            else:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = 0  # TODO

            self._create_raw_product(dir_name, name_gen)

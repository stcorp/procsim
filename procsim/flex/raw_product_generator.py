'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex raw output product generators, according to ESA-EOPG-EOEP-TN-0027
'''
import bisect
import collections
import datetime
import os
from typing import List, Tuple, Iterable

from procsim.core.exceptions import ScenarioError
from procsim.core.job_order import JobOrderInput

from . import main_product_header, constants, product_generator, product_name

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

    An array "data_takes" with one or more entries can be specified
    in the scenario. Each data entry must contain at least the ID,
    start/stop times and 'intermediate' flag.

      "data_takes": [
        {
          "data_take_id": 15,
          "start": "2021-02-01T00:24:32.000Z",
          "stop": "2021-02-01T00:29:32.000Z",
          "intermediate": false,
        },
        ..
      ]

    For each data take, the configured raw data is sliced into three types of
    slices, along the FLEX slicing grid:

    -complete slice: one for each completery overlapped grid frame
    -partial slice: one for each partially overlapped grid frame
    -intermediate slice: similar to partial slice, but it is unclear if
        data take actually started/ended here (as data take may be
        distributed over multiple raw data products)

    There are separate slice products for the three different sensors, so this
    gives 9 product types in total.

    '''

    PRODUCTS = [
        'RWS_LR_OBS',
        'RWS_LRPOBS',
        'RWS_LRIOBS',
        'RWS_H1_OBS',
        'RWS_H1POBS',
        'RWS_H1IOBS',
        'RWS_H2_OBS',
        'RWS_H2POBS',
        'RWS_H2IOBS',
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
        self._key_periods = None

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + self.HDR_PARAMS, acq + self.ACQ_PARAMS

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:  # TODO merge/superclassify with CAL/ANC
        if not super().parse_inputs(input_products):
            return False

        INPUTS = ['RWS_H1POBS', 'RWS_H2POBS', 'RWS_LRPOBS']

        key_periods = collections.defaultdict(list)

        for input in input_products:
            if input.file_type in INPUTS:
                for file in input.file_names:
                    # Skip non-directory products. These have already been parsed in the superclass.
                    if not os.path.isdir(file):
                        continue
                    file, _ = os.path.splitext(file)    # Remove possible extension
                    gen = product_name.ProductName(self._compact_creation_date_epoch)
                    gen.parse_path(file)
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr = main_product_header.MainProductHeader()
                    hdr.parse(mph_file_name)
                    if hdr.begin_position is None or hdr.end_position is None:
                        raise ScenarioError('begin/end position not set in {}'.format(mph_file_name))
                    key = (hdr.data_take_id, hdr.sensor_detector, hdr.slice_frame_nr)
                    start = hdr.begin_position
                    stop = hdr.end_position
                    start_pos = hdr.slice_start_position
                    stop_pos = hdr.slice_stop_position
                    key_periods[key].append((start, stop, start_pos, stop_pos))

        # check completeness for periods per (cal_id, sensor)
        for key, periods in key_periods.items():
            periods = sorted(periods)

            if len(periods) > 1 and periods[0][2] == 'on_grid' and periods[-1][3] == 'on_grid':
                overlap = True

                for i in range(len(periods)-1):
                    period_end = periods[i][1]
                    next_period_start = periods[i+1][0]
                    if next_period_start > period_end:
                        overlap = False
                        break

                if overlap:
                    if self._key_periods is None:
                        self._key_periods = {}
                    self._key_periods[key] = (periods[0][0], periods[-1][1])

        return True

    def generate_output(self):
        super().generate_output()

        if self._key_periods is not None:
            for key, period in self._key_periods.items():
                self._hdr.data_take_id, sensor, self._hdr.slice_frame_nr = key
                self._hdr.slice_start_position = self._hdr.slice_stop_position = 'on_grid'

                self._create_product(period[0], period[1], True, sensor)
            return

        if 'data_takes' not in self._scenario_config:
            return

        data_takes_with_bounds = self._get_data_takes_with_bounds()
        for data_take_config, data_take_start, data_take_stop in data_takes_with_bounds:
            self.read_scenario_parameters(data_take_config)
            if self._enable_slicing:
                self._generate_sliced_output(data_take_config, data_take_start, data_take_stop)
            else:
                self._create_product(data_take_start, data_take_stop, True)  # TODO complete?

    def _create_product(self, acq_start: datetime.datetime, acq_stop: datetime.datetime, complete, for_sensor=None):
        name_gen = self._create_name_generator(acq_start, acq_stop)
        if for_sensor is not None:
            name_gen.downlink_time = acq_start  # TODO why needed for merged partial?

        for sensor in ('LR', 'HR1', 'HR2'):
            if for_sensor is not None and sensor != for_sensor:
                continue

            anx = self._get_anx(acq_start)
            if anx is not None:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = (acq_start - anx).total_seconds()
            else:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = 0  # TODO

            dir_name = name_gen.generate_path_name()

            self._hdr.product_type = self._output_type
            self._hdr.initialize_product_list(dir_name)
            self._hdr.set_phenomenon_times(acq_start, acq_stop)
            self._hdr.sensor_detector = sensor

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
                if self._output_type.endswith('_OBS'):
                    self._create_product(slice_start, slice_end, complete)
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

                if ((not intermediate and self._output_type.endswith('POBS')) or
                        (intermediate and self._output_type.endswith('IOBS'))):
                    self._create_product(max(slice_start, segment_start), min(slice_end, segment_end), complete)


class RWS_CAL(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw slice-based products generation.

    An array "data_takes" with one or more entries can be specified
    in the scenario. Each entry must contain at least the ID,
    start/stop times and 'intermediate' flag.

    "calibration_events": [
      {
        "calibration_id": "15",
        "start": "2017-01-01T06:01:31.394000Z",
        "stop": "2017-01-01T06:03:44.504000Z",
        "intermediate": false
      },
      ..
    ]

    For each event, the configured raw data is sliced into three types of
    slices:

    -complete slice: one for each completery overlapped event
    -partial slice: one for each partially overlapped event
    -intermediate slice: similar to partial slice, but it is unclear if
        event actually started/ended here (as event take may be
        distributed over multiple raw data products)

    There are separate slice products for the three different sensors, so this
    gives 9 product types in total.
    '''

    PRODUCTS = [
        'RWS_LR_CAL',
        'RWS_LRPCAL',
        'RWS_LRICAL',
        'RWS_H1_CAL',
        'RWS_H1PCAL',
        'RWS_H1ICAL',
        'RWS_H2_CAL',
        'RWS_H2PCAL',
        'RWS_H2ICAL',
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
        self._key_periods = None

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + self.HDR_PARAMS, acq + self.ACQ_PARAMS

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:
        # First copy the metadata from any input product (normally H or V)
        if not super().parse_inputs(input_products):
            return False

        INPUTS = ['RWS_H1PCAL', 'RWS_H2PCAL', 'RWS_LRPCAL']

        key_periods = collections.defaultdict(list)

        for input in input_products:
            if input.file_type in INPUTS:
                for file in input.file_names:
                    # Skip non-directory products. These have already been parsed in the superclass.
                    if not os.path.isdir(file):
                        continue
                    file, _ = os.path.splitext(file)    # Remove possible extension
                    gen = product_name.ProductName(self._compact_creation_date_epoch)
                    gen.parse_path(file)
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr = main_product_header.MainProductHeader()
                    hdr.parse(mph_file_name)
                    if hdr.begin_position is None or hdr.end_position is None:
                        raise ScenarioError('begin/end position not set in {}'.format(mph_file_name))
                    key = (hdr.calibration_id, hdr.sensor_detector)
                    start = hdr.begin_position
                    stop = hdr.end_position
                    start_pos = hdr.slice_start_position
                    stop_pos = hdr.slice_stop_position
                    key_periods[key].append((start, stop, start_pos, stop_pos))

        # check completeness for periods per (cal_id, sensor)
        for key, periods in key_periods.items():
            periods = sorted(periods)
            if len(periods) > 1 and periods[0][2] == 'begin_of_SA' and periods[-1][3] == 'end_of_SA':
                overlap = True
                for i in range(len(periods)-1):
                    period_end = periods[i][1]
                    next_period_start = periods[i+1][0]
                    if next_period_start > period_end:
                        overlap = False
                        break

                if overlap:
                    if self._key_periods is None:
                        self._key_periods = {}
                    self._key_periods[key] = (periods[0][0], periods[-1][1])

        return True

    def generate_output(self):
        super().generate_output()

        if self._key_periods is not None:
            for key, period in self._key_periods.items():
                cal_id, sensor = key
                self._create_product(cal_id, period[0], period[1], True, 'begin_of_SA', 'end_of_SA', sensor)
            return

        if 'calibration_events' not in self._scenario_config:
            return

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

            cal_id = calibration_config['calibration_id']

            if complete:
                if self._output_type.endswith('_CAL'):
                    self._create_product(cal_id, cal_start, cal_stop, complete, slice_start_position, slice_stop_position)

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

                if ((not intermediate and self._output_type.endswith('PCAL')) or
                        (intermediate and self._output_type.endswith('ICAL'))):
                    self._create_product(cal_id, cal_start, cal_stop, complete, slice_start_position, slice_stop_position)

    def _create_product(self, cal_id: int, acq_start: datetime.datetime, acq_stop: datetime.datetime,
                        complete, slice_start_position, slice_stop_position, for_sensor=None):
        name_gen = self._create_name_generator(acq_start, acq_stop)
        if for_sensor is not None:
            name_gen.downlink_time = acq_start  # TODO why needed for merged partial?

        for sensor in ('LR', 'HR1', 'HR2'):
            if for_sensor is not None and sensor != for_sensor:
                continue

            if self._hdr.anx_elapsed is None:
                anx = self._get_anx(acq_start)
                if anx is not None:
                    self._hdr.anx_elapsed = name_gen.anx_elapsed = (acq_start - anx).total_seconds()
                else:
                    self._hdr.anx_elapsed = name_gen.anx_elapsed = 0  # TODO

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
            self._hdr.calibration_id = cal_id
            self._hdr.sensor_detector = sensor

            self._create_raw_product(dir_name, name_gen)


class RWS_ANC(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw slice-based products generation.

    An array "anc_events" with one or more entries can be specified
    in the scenario. Each entry must contain at least the ID,
    start/stop times and 'intermediate' flag.

    "anc_events": [
        {
            "apid": "4321",
            "start": "2017-01-01T05:51:31.394000Z",
            "stop": "2017-01-01T08:20:44.504000Z",
            "intermediate": false
        },
        ..
      ]

    For each event, the configured raw data is sliced into three types of
    slices, along an ANX-to-ANX grid:

    -complete slice: one for each completery overlapped grid frame
    -partial slice: one for each partially overlapped event
    -intermediate slice: similar to partial slice, but it is unclear if
        event actually started/ended here (as event take may be
        distributed over multiple raw data products)

    There are separate slice products for the three different sensors, so this
    gives 9 product types in total.
    '''

    PRODUCTS = [
        'RWS_LR_VAU',
        'RWS_LRPVAU',
        'RWS_H1_VAU',
        'RWS_H1PVAU',
        'RWS_H2_VAU',
        'RWS_H2PVAU',

        'RWS_XS_ITM',
        'RWS_XSPITM',

        'RWS_XS_OBC',
        'RWS_XSPOBC',
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
        self._key_periods = None

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + self.HDR_PARAMS, acq + self.ACQ_PARAMS

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:  # TODO merge with CAL, OE parse_inputs when done
        # First copy the metadata from any input product (normally H or V)
        if not super().parse_inputs(input_products):
            return False

        INPUTS = ['RWS_H1PVAU', 'RWS_H2PVAU', 'RWS_LRPVAU']  # TODO use as key instead of just sensor for multi types?

        key_periods = collections.defaultdict(list)

        for input in input_products:
            if input.file_type in INPUTS:
                for file in input.file_names:
                    # Skip non-directory products. These have already been parsed in the superclass.
                    if not os.path.isdir(file):
                        continue
                    file, _ = os.path.splitext(file)    # Remove possible extension
                    gen = product_name.ProductName(self._compact_creation_date_epoch)
                    gen.parse_path(file)
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr = main_product_header.MainProductHeader()
                    hdr.parse(mph_file_name)
                    if hdr.begin_position is None or hdr.end_position is None:
                        raise ScenarioError('begin/end position not set in {}'.format(mph_file_name))
                    key = (hdr.apid, hdr.sensor_detector)
                    start = hdr.begin_position
                    stop = hdr.end_position
                    start_pos = hdr.slice_start_position
                    stop_pos = hdr.slice_stop_position
                    key_periods[key].append((start, stop, start_pos, stop_pos))

        # check completeness for periods per (apid, sensor) TODO where to get absorbit?
        for key, periods in key_periods.items():
            periods = sorted(periods)
            if len(periods) > 1 and periods[0][2] == 'anx' and periods[-1][3] == 'anx':
                overlap = True
                for i in range(len(periods)-1):
                    period_end = periods[i][1]
                    next_period_start = periods[i+1][0]
                    if next_period_start > period_end:
                        overlap = False
                        break

                if overlap:
                    if self._key_periods is None:
                        self._key_periods = {}
                    self._key_periods[key] = (periods[0][0], periods[-1][1])

        return True

    def generate_output(self):
        super().generate_output()

        if self._key_periods is not None:
            for key, period in self._key_periods.items():
                apid, sensor = key
                self._create_product(apid, period[0], period[1], True, 'anx', 'anx', sensor)
            return

        if 'anc_events' not in self._scenario_config:
            return

        anx = [self._time_from_iso(a) for a in self._scenario_config['anx']]

        for event in self._scenario_config['anc_events']:
            apid = event['apid']
            start = self._time_from_iso(event['start'])
            stop = self._time_from_iso(event['stop'])

            for i in range(len(anx)-1):
                # complete overlap of anx-to-anx window
                if start <= anx[i] and stop >= anx[i+1] and self._output_type[-4] == '_':
                    self._create_product(apid, anx[i], anx[i+1], True, 'anx', 'anx')

                # partial overlap of anx-to-anx window
                elif anx[i] <= start <= anx[i+1] and self._output_type[-4] == 'P':
                    self._create_product(apid, start, anx[i+1], False, 'inside_orb', 'anx')

                elif anx[i] <= stop <= anx[i+1] and self._output_type[-4] == 'P':
                    self._create_product(apid, anx[i], stop, False, 'anx', 'inside_orb')

    def _create_product(self, apid, acq_start: datetime.datetime, acq_stop: datetime.datetime, complete,
                        slice_start_position, slice_stop_position, for_sensor=None):
        name_gen = self._create_name_generator(acq_start, acq_stop)
        if for_sensor is not None:
            name_gen.downlink_time = acq_start  # TODO why needed for merged partial?

        for sensor in ('LR', 'HR1', 'HR2'):
            if for_sensor is not None and sensor != for_sensor:
                continue

            if self._hdr.anx_elapsed is None:
                anx = self._get_anx(acq_start)
                if anx is not None:
                    self._hdr.anx_elapsed = name_gen.anx_elapsed = (acq_start - anx).total_seconds()
                else:
                    self._hdr.anx_elapsed = name_gen.anx_elapsed = 0  # TODO

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
            self._hdr.sensor_detector = sensor
            self._hdr.apid = apid

            self._create_raw_product(dir_name, name_gen)

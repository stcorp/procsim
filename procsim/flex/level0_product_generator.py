'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex Level 0 product generators,
format according to ESA-EOPG-EOEP-TN-0022
'''
import bisect
import collections
import datetime
import os
from typing import Iterable, List, Tuple, Optional

from . import constants
from procsim.core.exceptions import ScenarioError
from procsim.core.job_order import JobOrderInput

from . import main_product_header, product_generator, product_name

_HDR_PARAMS: List[tuple] = [
    ('cycle_number', 'cycle_number', 'str'),
    ('relative_orbit_number', 'relative_orbit_number', 'str'),
]

_ACQ_PARAMS: List[tuple] = []


class ProductGeneratorL0(product_generator.ProductGeneratorBase):
    '''
    Locate combinations of three complete slices (one for each sensor) for the same period.
    '''  # TODO unique datatake_id, cal_id, event_id?

    INPUTS: List[str] = []

    ID_FIELD = ''

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

        self._output_periods: Optional[List[Tuple[int, datetime.datetime, datetime.datetime]]] = None

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:
        # First copy the metadata from any input product (normally H or V)
        if not super()._parse_inputs(input_products, ignore_missing=True):
            return False

        period_types = collections.defaultdict(set)
        for input in input_products:
            if input.file_type in self.INPUTS:
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
                    data_take_id = getattr(hdr, self.ID_FIELD)
                    start = hdr.begin_position
                    stop = hdr.end_position
                    period_types[data_take_id, start, stop].add(input.file_type)
        self._output_periods = []
        for period, filetypes in period_types.items():
            if len(set(filetypes)) == len(self.INPUTS):  # all inputs available (eg three sensors)
                self._output_periods.append(period)

        return True


class EO(ProductGeneratorL0):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 slice based products.

    Input is a set of (incomplete) RWS slices.

    An array "data_takes" with one or more entries can also be
    specified in the scenario. Each entry must contain at least the ID
    and start/stop times, and can contain other metadata fields. For example:

      "data_takes": [
        {
          "data_take_id": 15,
          "start": "2021-02-01T00:24:32.000Z",
          "stop": "2021-02-01T00:29:32.000Z",
          "intermediate": false,
        },
        ..
      ]

    A L0 product is generated for each set of 'complete' slices along the
    FLEX slicing grid (meaning one complete slice for each of three sensors).

    '''

    INPUTS = [
        'RWS_H1_OBS',
        'RWS_H2_OBS',
        'RWS_LR_OBS'
    ]

    ID_FIELD = 'data_take_id'

    PRODUCTS = [
        'L0__OBS___',
        'L0__OBSMON',
    ]

    _ACQ_PARAMS: List[tuple] = []

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool'),
        ('slice_grid_spacing', '_slice_grid_spacing', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
        ('slice_minimum_duration', '_slice_minimum_duration', 'float'),
        ('orbital_period', '_orbital_period', 'float'),
        ('zip_output', '_zip_output', 'bool'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

        self._enable_slicing = True
        self._slice_grid_spacing = constants.SLICE_GRID_SPACING
        self._slice_overlap_start = constants.SLICE_OVERLAP_START
        self._slice_overlap_end = constants.SLICE_OVERLAP_END
        self._slice_minimum_duration = constants.SLICE_MINIMUM_DURATION
        self._orbital_period = constants.ORBITAL_PERIOD
        self._zip_output = False
        self._output_periods: Optional[List[Tuple[int, datetime.datetime, datetime.datetime]]] = None

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        # generate output from inputs
        if self._output_periods is not None:
            for data_take_id, start, stop in self._output_periods:
                self._hdr.data_take_id = data_take_id
                self._hdr.product_baseline = self._scenario_config['baseline']
                self._generate_product(start, stop)

        # generate output from scenario config
#        else:
#            data_takes_with_bounds = self._get_data_takes_with_bounds()
#            for data_take_config, data_take_start, data_take_stop in data_takes_with_bounds:
#                self.read_scenario_parameters(data_take_config)
#                if self._enable_slicing:
#                    self._generate_sliced_output(data_take_config, data_take_start, data_take_stop)
#                else:
#                    assert False  # TODO

    def _generate_product(self, start, stop):
        if self._hdr.data_take_id is None:
            raise ScenarioError('data_take_id field is mandatory')

        self._logger.debug('Datatake {} from {} to {}'.format(self._hdr.data_take_id, start, stop))

        self._hdr.sensor_mode = 'EO'

        # Setup MPH fields. Validity time is not changed, should still be the
        # theoretical slice start/end.
        self._hdr.product_type = self._resolve_wildcard_product_type()
        self._hdr.set_phenomenon_times(start, stop)

        # Determine and set the slice number if not set already.
        if self._hdr.slice_frame_nr is None:
            # Get slice number from middle of slice to deal with merged slices.
            middle = start + (stop - start) / 2
            self._hdr.slice_frame_nr = self._get_slice_frame_nr(middle, constants.SLICE_GRID_SPACING)

        # Create name generator
        name_gen = self._create_name_generator(self._hdr)
        name_gen.downlink_time = self._creation_date  # TODO remove
        name_gen.set_creation_date(self._creation_date)

        if self._hdr.anx_elapsed is None:
            anx, orbitnum = self._get_anx_orbit(start)
            if anx is not None:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = (start - anx).total_seconds()
            else:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = 0  # TODO

        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)

        # Create directory and files
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        for sensor in ('lres', 'hre1', 'hre2'):
            file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_'+sensor))
            self._add_file_to_product(file_path, self._size_mb // 2)

        file_path = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_path)

        if self._zip_output:
            self.zip_folder(dir_name, self._zip_extension)

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
            anx, orbitnum = self._get_anx_orbit(slice_middle)
            slice_nr = self._get_slice_frame_nr(slice_middle, self._slice_grid_spacing)
            if anx is None or slice_nr is None:
                continue
            validity_start = slice_start - self._slice_overlap_start
            validity_end = slice_end + self._slice_overlap_end
            acq_start = max(validity_start, segment_start)
            acq_end = min(validity_end, segment_end)
            self._hdr.slice_frame_nr = slice_nr
            self._hdr.set_validity_times(validity_start, validity_end)

            self._hdr.data_take_id = data_take_config['data_take_id']
            self._hdr.slice_frame_nr = slice_nr
            self._hdr.along_track_coordinate = int(self._slice_grid_spacing.seconds * (slice_nr-1))

            self._logger.debug((f'Create slice #{slice_nr}\n'
                                f'  acq {acq_start}  -  {acq_end}\n'
                                f'  validity {validity_start}  -  {validity_end}\n'
                                f'  anx {anx}'))

            if segment_start <= slice_start and slice_end <= segment_end:
                self._generate_product(slice_start, slice_end)  # acq_start, acq_end) TODO


class CAL(ProductGeneratorL0):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 slice based products.

    Input is a set of (incomplete) RWS slices.

    An array "calibration_events" with one or more entries can also be
    specified in the scenario. Each entry must contain at least the ID
    and start/stop times, and can contain other metadata fields. For example:

    "calibration_events": [
      {
        "calibration_id": "15",
        "start": "2017-01-01T06:01:31.394000Z",
        "stop": "2017-01-01T06:03:44.504000Z",
        "intermediate": false
      },
      ..
    ]

    A L0 product is generated for each set of 'complete' slices (meaning
    a complete slice for each of three sensors), in other words for a complete
    calibration event.
    '''

    INPUTS = [
        'RWS_H1_CAL',
        'RWS_H2_CAL',
        'RWS_LR_CAL'
    ]

    ID_FIELD = 'calibration_id'

    PRODUCTS = [
        'L0__DARKNP',
        'L0__DARKSR',
        'L0__DEFDAR',
        'L0__DARKOC',
        'L0__DRKMTF',
        'L0__DRKSTR',
        'L0__SUN___',
        'L0__DEFSUN',
        'L0__MOON__',
        'L0__MOONSL',
        'L0__LINDES',
        'L0__LINSEA',
        'L0__LINSUN',
        'L0__LINDAR',
        'L0__CTE___',
        'L0__CLOUD_',
    ]

    ACQ_SUBTYPE = {
        'L0__DARKNP': 'Dark_CU_NAPoint_NOM',
        'L0__DARKSR': 'Dark_CU_SunPoint_Rad',
        'L0__DEFDAR': 'Dark_defpixel',
        'L0__DARKOC': 'DarkSea_NAPoint',
        'L0__DRKMTF': 'Dark_CU_MoonPoint_MTF',
        'L0__DRKSTR': 'Dark_CU_MoonPoint_Stray',
        'L0__SUN___': 'Radiometric_SunPoint',
        'L0__DEFSUN': 'Radiometric_SunPoint_DefPixels',
        'L0__MOON__': 'Radiometric_MTF_MoonPoint',
        'L0__MOONSL': 'Straylight_MoonPoint',
        'L0__LINDES': 'Linearity_NaPoint_Desert',
        'L0__LINSEA': 'Linearity_NaPoint_Sea',
        'L0__LINSUN': 'Linearity_SunPoint',
        'L0__LINDAR': 'Linearity_Dark',
        'L0__CTE___': 'CTE_monitoring',
        'L0__CLOUD_': 'Radiometric_NaPoint_Cloud',
    }

    _ACQ_PARAMS: List[tuple] = [
    ]

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool'),
        ('slice_grid_spacing', '_slice_grid_spacing', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
        ('slice_minimum_duration', '_slice_minimum_duration', 'float'),
        ('orbital_period', '_orbital_period', 'float'),
        ('zip_output', '_zip_output', 'bool'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

        self._enable_slicing = True
        self._slice_grid_spacing = constants.SLICE_GRID_SPACING
        self._slice_overlap_start = constants.SLICE_OVERLAP_START
        self._slice_overlap_end = constants.SLICE_OVERLAP_END
        self._slice_minimum_duration = constants.SLICE_MINIMUM_DURATION
        self._orbital_period = constants.ORBITAL_PERIOD
        self._zip_output = False
        self._output_periods: Optional[List[Tuple[int, datetime.datetime, datetime.datetime]]] = None

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        # generate output from inputs
        if self._output_periods is not None:
            if self._hdr.acquisition_subtype != self.ACQ_SUBTYPE[self._output_type]:
                return

            self._hdr.product_baseline = self._scenario_config['baseline']
            for cal_id, start, stop in self._output_periods:
                self._generate_output(cal_id, start, stop)

        # generate output from scenario config
#        else:
#            for calibration_config in self._scenario_config['calibration_events']:
#                self.read_scenario_parameters(calibration_config)
#                cal_start = self._time_from_iso(calibration_config['start'])
#                cal_stop = self._time_from_iso(calibration_config['stop'])
#
#                begin_pos = self._hdr.begin_position
#                end_pos = self._hdr.end_position
#                if begin_pos is None or end_pos is None:
#                    raise ScenarioError('no begin_position or end_position')
#
#                complete = (cal_start >= begin_pos and cal_stop <= end_pos)
#                if complete:
#                    self._generate_output(calibration_config['calibration_id'], cal_start, cal_stop)

    def _generate_output(self, calibration_id: int, start, stop):
        self._logger.debug('Calibration {} from {} to {}'.format(self._hdr.calibration_id, start, stop))

        # Setup MPH fields. Validity time is not changed, should still be the
        # theoretical slice start/end.
        self._hdr.product_type = self._resolve_wildcard_product_type()
        self._hdr.set_phenomenon_times(start, stop)

        self._hdr.set_validity_times(start, stop)
        self._hdr.acquisition_type = 'CALIBRATION'
        self._hdr.sensor_mode = 'CAL'

        # self._hdr.calibration_id = calibration_id

        # Create name generator
        name_gen = self._create_name_generator(self._hdr)
        name_gen.downlink_time = self._creation_date  # TODO remove
        name_gen.set_creation_date(self._creation_date)

        if self._hdr.anx_elapsed is None:
            anx, orbitnum = self._get_anx_orbit(start)
            if anx is not None:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = (start - anx).total_seconds()
            else:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = 0  # TODO

        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)

        # Create directory and files
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        for sensor in ('lres', 'hre1', 'hre2'):
            file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_'+sensor))
            self._add_file_to_product(file_path, self._size_mb // 2)

        file_path = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_path)

        if self._zip_output:
            self.zip_folder(dir_name, self._zip_extension)


class ANC(ProductGeneratorL0):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 slice based products.

    Input is a set of (incomplete) RWS slices.

    An array "anc_events" with one or more entries can also be
    specified in the scenario. Each entry must contain at least the ID
    and start/stop times, and can contain other metadata fields. For example:

    "anc_events": [
      {
          "apid": "4321",
          "start": "2017-01-01T05:51:31.394000Z",
           "stop": "2017-01-01T08:20:44.504000Z",
           "intermediate": false
      },
      ..
    ]

    A L0 product is generated for each 'complete' slice, that is for a full
    ANX-to-ANX frame.

    For L0__VAU_TM, L0__TST___ and L0__WRN___ products, a 'complete' slice
    means a set of complete slices for each of three sensors.
    '''

    INPUTS = [
        'RWS_LR_VAU',
        'RWS_H1_VAU',
        'RWS_H2_VAU',
    ]

    PRODUCTS = [
        'L0__VAU_TM',
        'L0__TST___',
        'L0__WRN___',

    ]

    ID_FIELD = 'apid'

    _ACQ_PARAMS: List[tuple] = []

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool'),
        ('slice_grid_spacing', '_slice_grid_spacing', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
        ('slice_minimum_duration', '_slice_minimum_duration', 'float'),
        ('orbital_period', '_orbital_period', 'float'),
        ('zip_output', '_zip_output', 'bool'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

        self._enable_slicing = True
        self._slice_grid_spacing = constants.SLICE_GRID_SPACING
        self._slice_overlap_start = constants.SLICE_OVERLAP_START
        self._slice_overlap_end = constants.SLICE_OVERLAP_END
        self._slice_minimum_duration = constants.SLICE_MINIMUM_DURATION
        self._orbital_period = constants.ORBITAL_PERIOD
        self._zip_output = False
        self._output_periods: Optional[List[Tuple[int, datetime.datetime, datetime.datetime]]] = None

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        # generate output from inputs
        if self._output_periods is not None:
            self._hdr.product_baseline = self._scenario_config['baseline']
            for apid, start, stop in self._output_periods:
                self._generate_output(apid, start, stop)

        # generate output from scenario config
#        else:
#            anx = [self._time_from_iso(a) for a in self._scenario_config['anx']]
#
#            for event in self._scenario_config['anc_events']:
#                apid = event['apid']
#                start = self._time_from_iso(event['start'])
#                stop = self._time_from_iso(event['stop'])
#
#                for i in range(len(anx)-1):
#                    # complete overlap of anx-to-anx window
#                    if start <= anx[i] and stop >= anx[i+1]:
#                        self._generate_output(apid, anx[i], anx[i+1])

    def _generate_output(self, apid: int, start, stop):
        self._logger.debug(f'Ancillary {apid} from {start} to {stop}')

        # Setup MPH fields. Validity time is not changed, should still be the
        # theoretical slice start/end.
        self._hdr.product_type = self._resolve_wildcard_product_type()
        self._hdr.set_phenomenon_times(start, stop)

        self._hdr.set_validity_times(start, stop)
        self._hdr.acquisition_type = 'OTHER'
        self._hdr.sensor_mode = 'ANC'

        # Create name generator
        name_gen = self._create_name_generator(self._hdr)
        name_gen.downlink_time = self._creation_date  # TODO remove
        name_gen.set_creation_date(self._creation_date)

#        if not self._output_type.endswith('___'):
#            name_gen.use_short_name = True

        if self._hdr.anx_elapsed is None:
            anx, orbitnum = self._get_anx_orbit(start)  # TODO copy-pasting
            if anx is not None:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = (start - anx).total_seconds()
            else:
                self._hdr.anx_elapsed = name_gen.anx_elapsed = 0  # TODO

        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)

        # Create directory and files
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        if self._output_type in ('L0__VAU_TM', 'L0__TST___', 'L0__WRN___'):
            for sensor in ('lres', 'hre1', 'hre2'):
                file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_'+sensor))
                self._add_file_to_product(file_path, self._size_mb // 2)
        else:
            file_path = os.path.join(dir_name, name_gen.generate_binary_file_name())
            self._add_file_to_product(file_path, self._size_mb // 2)

        file_path = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_path)

        if self._zip_output:
            self.zip_folder(dir_name, self._zip_extension)


class ANC_INSTTM(ANC):
    INPUTS = [
        'RWS_XS_ITM',
    ]

    PRODUCTS = [
        'L0__INSTTM',
    ]


class ANC_OBC(ANC):
    INPUTS = [
        'RWS_XS_OBC',
    ]

    PRODUCTS = [
        'L0__SAT_TM',
        'L0__NAVATT',
        'L0__PDHUTM',
        'L0__ICUDTM',
    ]

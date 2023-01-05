'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex Level 0 product generators,
format according to ESA-EOPG-EOEP-TN-0022
'''
import bisect
import datetime
import os
from typing import Iterable, List, Tuple

from . import constants
from procsim.core.exceptions import ScenarioError
from procsim.core.job_order import JobOrderInput

from . import main_product_header, product_generator, product_name

_HDR_PARAMS = [
    # Level 0 only
    ('num_l0_lines', 'nr_l0_lines', 'str'),
    ('num_l0_lines_corrupt', 'nr_l0_lines_corrupt', 'str'),
    ('num_l0_lines_missing', 'nr_l0_lines_missing', 'str'),
    ('swath', 'sensor_swath', 'str'),
    ('operational_mode', 'sensor_mode', 'str'),
]

_ACQ_PARAMS = [
    # Level 0, 1, 2a only
    ('mission_phase', 'mission_phase', 'str'),
    ('data_take_id', 'data_take_id', 'int'),
    ('global_coverage_id', 'global_coverage_id', 'str'),
    ('major_cycle_id', 'major_cycle_id', 'str'),
    ('repeat_cycle_id', 'repeat_cycle_id', 'str'),
    ('track_nr', 'track_nr', 'str'),
]


class EO(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 slice based products.

    Input is a set of (incomplete) RWS slices.
    If one or more slices are incomplete due to dump transitions, they are
    merged. The output is a single product, or multiple if there are data take
    transitions within the slice period.

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

    The generator adjusts the following metadata:
    - phenomenonTime (the acquisition begin/end times), modifed in case of merge/split.
    - isPartial, set if slice is partial (slice with DT start/end)
    - isMerged, set if slice is merged (slice with DT start/end)
    - dataTakeID (copied from data_takes section in scenario)
    - swathIdentifier (copied from scenario, either root, output section or
      data_takes section)
    '''

    PRODUCTS = [
        'L0__OBS___',
    ]

    _ACQ_PARAMS = [
        ('slice_frame_nr', 'slice_frame_nr', 'int')
    ]

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool'),
        ('slice_grid_spacing', '_slice_grid_spacing', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
        ('slice_minimum_duration', '_slice_minimum_duration', 'float'),
        ('orbital_period', '_orbital_period', 'float'),
    ]

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
        return gen + self.GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    # TODO parse inputs?? focus on delivering just products for now

    def _generate_product(self, start, stop):
        if self._hdr.acquisitions[0].data_take_id is None:
            raise ScenarioError('data_take_id field is mandatory')

        self._logger.debug('Datatake {} from {} to {}'.format(self._hdr.acquisitions[0].data_take_id, start, stop))

        # Setup MPH fields. Validity time is not changed, should still be the
        # theoretical slice start/end.
        self._hdr.product_type = self._resolve_wildcard_product_type()
        self._hdr.set_phenomenon_times(start, stop)
        self._hdr.is_incomplete = False  # TODO!
#        self._hdr.is_partial = self._is_partial_slice(self._hdr.validity_start, self._hdr.validity_stop, start, stop)
#        self._hdr.is_merged = self._is_merged_slice(self._hdr.validity_start, self._hdr.validity_stop, start, stop)

        # Determine and set the slice number if not set already.
        if self._hdr.acquisitions[0].slice_frame_nr is None:
            # Get slice number from middle of slice to deal with merged slices.
            middle = start + (stop - start) / 2
            self._hdr.acquisitions[0].slice_frame_nr = self._get_slice_frame_nr(middle, constants.SLICE_GRID_SPACING)

        # Create name generator
        name_gen = self._create_name_generator(self._hdr)
        name_gen.downlink_time = datetime.datetime.now()  # TODO

        name_gen.relative_orbit_number = '011'  # TODO these probably should be elsewhere.. and what is it? slicing?
        name_gen.cycle_number = '045'

        name_gen.duration = '0128'  # TODO calculate
        name_gen.anx_elapsed = '2826'

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

    def generate_output(self):
        super().generate_output()

        data_takes_with_bounds = self._get_data_takes_with_bounds()
        for data_take_config, data_take_start, data_take_stop in data_takes_with_bounds:
            self.read_scenario_parameters(data_take_config)
            if self._enable_slicing:
                self._generate_sliced_output(data_take_config, data_take_start, data_take_stop)
            else:
                assert False  # TODO

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
            self._hdr.acquisitions[0].slice_frame_nr = slice_nr
            self._hdr.set_validity_times(validity_start, validity_end)
            self._hdr.sensor_mode = 'EO'
            self._hdr.data_take_id = data_take_config['data_take_id']

            self._logger.debug((f'Create slice #{slice_nr}\n'
                                f'  acq {acq_start}  -  {acq_end}\n'
                                f'  validity {validity_start}  -  {validity_end}\n'
                                f'  anx {anx}'))

            if segment_start <= slice_start and slice_end <= segment_end:
                self._generate_product(slice_start, slice_end)  # acq_start, acq_end) TODO


class CAL(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 slice based products.

    Input is a set of (incomplete) RWS slices.
    If one or more slices are incomplete due to dump transitions, they are
    merged. The output is a single product, or multiple if there are data take
    transitions within the slice period.

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

    The generator adjusts the following metadata:
    - phenomenonTime (the acquisition begin/end times), modifed in case of merge/split.
    - isPartial, set if slice is partial (slice with DT start/end)
    - isMerged, set if slice is merged (slice with DT start/end)
    - dataTakeID (copied from data_takes section in scenario)
    - swathIdentifier (copied from scenario, either root, output section or
      data_takes section)
    '''

    PRODUCTS = [
        'L0_DARKNP',
        'L0_DARKSR',
        'L0_DARKSS',
        'L0_DEFDAR',
        'L0_DARKOC',
        'L0_DRKMTF',
        'L0_DRKSTR',
        'L0_SPECSD',
        'L0_SUN___',
        'L0_DEFSUN',
        'L0_MOON__',
        'L0_MOONSL',
        'L0_LINDES',
        'L0_LINSEA',
        'L0_LINSUN',
        'L0_LINDAR',
        'L0_CTE___',
        'L0_SCNVAL',
        'L0_COREG_',
        'L0_SPECEO',
        'L0_CLOUD_',
    ]

    ACQ_SUBTYPE = {
        'L0_DARKNP': 'Dark_CU_NAPoint_NOM',
        'L0_DARKSR': 'Dark_CU_SunPoint_Rad',
        'L0_DARKSS': 'Dark_CU_SunPoint_SpectrSun',
        'L0_DEFDAR': 'Dark_defpixel',
        'L0_DARKOC': 'DarkSea_NAPoint',
        'L0_DRKMTF': 'Dark_CU_MoonPoint_MTF',
        'L0_DRKSTR': 'Dark_CU_MoonPoint_Stray',
        'L0_SPECSD': 'Spectr_SunPoint',
        'L0_SUN___': 'RadioMetric_SunPoint',
        'L0_DEFSUN': 'RadioMetric_SunPoint_DefPixels',
        'L0_MOON__': 'Radiometric_MTF_MoonPoint',
        'L0_MOONSL': 'Straylight_MoonPoint',
        'L0_LINDES': 'Linearity_NaPoint_Desert',
        'L0_LINSEA': 'Linearity_NaPoint_Sea',
        'L0_LINSUN': 'Linearity_SunPoint',
        'L0_LINDAR': 'Linearity_Dark',
        'L0_CTE___': 'CTE_Monitoring',
        'L0_SCNVAL': 'Image_Geo',
        'L0_COREG_': 'Image_coreg',
        'L0_SPECEO': 'Spectral_NaPoint_Bin',
        'L0_CLOUD_': 'Radiometric_NaPoint_Cloud',
    }

    _ACQ_PARAMS = [
        ('slice_frame_nr', 'slice_frame_nr', 'int')
    ]

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool'),
        ('slice_grid_spacing', '_slice_grid_spacing', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
        ('slice_minimum_duration', '_slice_minimum_duration', 'float'),
        ('orbital_period', '_orbital_period', 'float'),
    ]

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
        return gen + self.GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    # TODO parse inputs?? focus on delivering just products for now

    def generate_output(self):
        super().generate_output()

        data_takes_with_bounds = self._get_data_takes_with_bounds()  # TODO separate calibration_events in config? and add separate raw data for that?
        for data_take_config, data_take_start, data_take_stop in data_takes_with_bounds:
            self.read_scenario_parameters(data_take_config)
            self._generate_output(data_take_start, data_take_stop)

    def _generate_output(self, start, stop):
        #        if self._hdr.acquisitions[0].calibration_id is None:
        #            raise ScenarioError('calibration_id field is mandatory')
        #
        #        self._logger.debug('Datatake {} from {} to {}'.format(self._hdr.acquisitions[0].data_take_id, start, stop))
        self._logger.debug('Calibration {} from {} to {}'.format(self._hdr.acquisitions[0].calibration_id, start, stop))

        # Setup MPH fields. Validity time is not changed, should still be the
        # theoretical slice start/end.
        self._hdr.product_type = self._resolve_wildcard_product_type()
        self._hdr.set_phenomenon_times(start, stop)
        self._hdr.is_incomplete = False  # TODO!
        #        self._hdr.is_partial = self._is_partial_slice(self._hdr.validity_start, self._hdr.validity_stop, start, stop)
        #        self._hdr.is_merged = self._is_merged_slice(self._hdr.validity_start, self._hdr.validity_stop, start, stop)

        # Determine and set the slice number if not set already.
        #        if self._hdr.acquisitions[0].slice_frame_nr is None:
        #            # Get slice number from middle of slice to deal with merged slices.
        #            middle = start + (stop - start) / 2
        #            self._hdr.acquisitions[0].slice_frame_nr = self._get_slice_frame_nr(middle, constants.SLICE_GRID_SPACING)

        self._hdr.set_validity_times(start, stop)
        self._hdr.acquisition_type = 'CALIBRATION'
        self._hdr.acquisition_subtype = self.ACQ_SUBTYPE[self._output_type]
        self._hdr.sensor_mode = 'CAL'

        # Create name generator
        name_gen = self._create_name_generator(self._hdr)
        name_gen.downlink_time = datetime.datetime.now()  # TODO

        name_gen.relative_orbit_number = '011'  # TODO these probably should be elsewhere.. and what is it? slicing?
        name_gen.cycle_number = '045'

        name_gen.duration = '0128'  # TODO calculate
        name_gen.anx_elapsed = '2826'

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


class ANC(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 slice based products.

    Input is a set of (incomplete) RWS slices.
    If one or more slices are incomplete due to dump transitions, they are
    merged. The output is a single product, or multiple if there are data take
    transitions within the slice period.

    The generator adjusts the following metadata:
    - phenomenonTime (the acquisition begin/end times), modifed in case of merge/split.
    - isPartial, set if slice is partial (slice with DT start/end)
    - isMerged, set if slice is merged (slice with DT start/end)
    - dataTakeID (copied from data_takes section in scenario)
    - swathIdentifier (copied from scenario, either root, output section or
      data_takes section)
    '''

    PRODUCTS = [
        'L0_SAT_TM',
        'L0_NAVATT',
        'L0_PDHUTM',
        'L0_ICUDTM',
        'L0_VAU_TM',
        'L0_INSTTM',
        'L0_TST___',
        'L0_UNK___',
    ]

    _ACQ_PARAMS = [
        ('slice_frame_nr', 'slice_frame_nr', 'int')
    ]

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool'),
        ('slice_grid_spacing', '_slice_grid_spacing', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
        ('slice_minimum_duration', '_slice_minimum_duration', 'float'),
        ('orbital_period', '_orbital_period', 'float'),
    ]

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
        return gen + self.GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    # TODO parse inputs?? focus on delivering just products for now

    def generate_output(self):
        super().generate_output()

        anx = [self._time_from_iso(a) for a in self._scenario_config['anx']]

        for event in self._scenario_config['anc_events']:
            apid = event['apid']
            start = self._time_from_iso(event['start'])
            stop = self._time_from_iso(event['stop'])

            for i in range(len(anx)-1):
                # complete overlap of anx-to-anx window
                if start <= anx[i] and stop >= anx[i+1]:
                    self._generate_output(apid, anx[i], anx[i+1])

    def _generate_output(self, apid, start, stop):
        #        if self._hdr.acquisitions[0].calibration_id is None:
        #            raise ScenarioError('calibration_id field is mandatory')
        #
        #        self._logger.debug('Datatake {} from {} to {}'.format(self._hdr.acquisitions[0].data_take_id, start, stop))
        self._logger.debug('Ancillary {} from {} to {}'.format(apid, start, stop))

        # Setup MPH fields. Validity time is not changed, should still be the
        # theoretical slice start/end.
        self._hdr.product_type = self._resolve_wildcard_product_type()
        self._hdr.set_phenomenon_times(start, stop)
        self._hdr.is_incomplete = False  # TODO!
        #        self._hdr.is_partial = self._is_partial_slice(self._hdr.validity_start, self._hdr.validity_stop, start, stop)
        #        self._hdr.is_merged = self._is_merged_slice(self._hdr.validity_start, self._hdr.validity_stop, start, stop)

        # Determine and set the slice number if not set already.
        #        if self._hdr.acquisitions[0].slice_frame_nr is None:
        #            # Get slice number from middle of slice to deal with merged slices.
        #            middle = start + (stop - start) / 2
        #            self._hdr.acquisitions[0].slice_frame_nr = self._get_slice_frame_nr(middle, constants.SLICE_GRID_SPACING)

        self._hdr.set_validity_times(start, stop)
        self._hdr.acquisition_type = 'OTHER'
        self._hdr.sensor_mode = 'ANC'

        # Create name generator
        name_gen = self._create_name_generator(self._hdr)
        name_gen.downlink_time = datetime.datetime.now()  # TODO

        name_gen.relative_orbit_number = '011'  # TODO these probably should be elsewhere.. and what is it? slicing?
        name_gen.cycle_number = '045'

        name_gen.duration = '0128'  # TODO calculate
        name_gen.anx_elapsed = '2826'

        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)

        # Create directory and files
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        if self._output_type in ('L0_VAU_TM', 'L0_TST___'):
            for sensor in ('lres', 'hre1', 'hre2'):
                file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_'+sensor))
                self._add_file_to_product(file_path, self._size_mb // 2)
        else:
            file_path = os.path.join(dir_name, name_gen.generate_binary_file_name())
            self._add_file_to_product(file_path, self._size_mb // 2)

        file_path = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_path)

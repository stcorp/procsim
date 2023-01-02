'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex Level 0 product generators,
format according to ESA-EOPG-EOEP-TN-0022
'''
import datetime
import os
from typing import Iterable

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
    ('relative_orbit_number', 'relative_orbit_number', 'str'),
    ('cycle_number', 'cycle_number', 'str'),
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

    Input is a set of (incomplete) RAWSxxx_10 slices.
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

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

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
        name_gen.downlink_time = datetime.datetime.now() # TODO

        name_gen.relative_orbit_number = '011' # TODO these probably should be elsewhere.. and what is it? slicing?
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
        # H/V measurement data
            file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_'+sensor))
            self._add_file_to_product(file_path, self._size_mb // 2)

        file_path = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_path)

    def generate_output(self):
        super().generate_output()

        # Sanity check
        if self._hdr.begin_position is None or self._hdr.end_position is None:
            raise ScenarioError('begin/end position must be set')

        # If not read from an input product, set validity time to slice bounds.
        # Get slice bounds from middle of slice to deal with merged slices.
        middle_position = self._hdr.begin_position + (self._hdr.end_position - self._hdr.begin_position) / 2
        slice_bounds = self._get_slice_frame_interval(middle_position, constants.SLICE_GRID_SPACING)
        if self._hdr.validity_start is None:
            if slice_bounds is None:
                self._logger.warning(
                    f'Could not find slice bounds for central position {middle_position}. Using {self._hdr.begin_position} as validity start.')
                self._hdr.validity_start = self._hdr.begin_position
            else:
                self._logger.debug(f'Use slice start {slice_bounds[0]} as input for validity start time')
                self._hdr.validity_start = slice_bounds[0] - constants.SLICE_OVERLAP_START
        if self._hdr.validity_stop is None:
            if slice_bounds is None:
                self._logger.warning(
                    f'Could not find slice bounds for central position {middle_position}. Using {self._hdr.end_position} as validity end.')
                self._hdr.validity_stop = self._hdr.end_position
            else:
                self._logger.debug(f'Use slice end {slice_bounds[1]} as input for validity stop time')
                self._hdr.validity_stop = slice_bounds[1] + constants.SLICE_OVERLAP_END

        data_takes_with_bounds = self._get_data_takes_with_bounds()
        for data_take_config, data_take_start, data_take_stop in data_takes_with_bounds:
            self.read_scenario_parameters(data_take_config)
            self._generate_product(data_take_start, data_take_stop)

        if len(data_takes_with_bounds) == 0:
            self._logger.info('No products generated, start/stop outside data takes?')

class CAL(product_generator.ProductGeneratorBase):
    PRODUCTS = [
        'L0_DARKNP',
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


class ANC(product_generator.ProductGeneratorBase):
    PRODUCTS = [
        'L0_SAT_TM',
        'L0_NAVATT',
        'L0_PDHUTM',
        'L0_ICUDTM',
        'L0_VAU_TM',
        'L0_INSTTM',

        'L0_TST___',  # TODO ?
        'L0_UNK___',
    ]

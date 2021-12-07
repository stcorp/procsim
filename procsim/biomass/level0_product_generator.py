'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 0 product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0073
'''
import datetime
import os
from typing import Iterable

from procsim.biomass import constants
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


class Sx_RAW__0x(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 slice based products.

    Input is a set of (incomplete) RAWSxxx_10 slices.
    If one or more slices are incomplete due to dump transitions, they are
    merged. The output is a single product, or multiple if there are data take
    transitions within the slice period.

    An array "data_takes" with one or more data take objects must be specified
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
    - partialSlice, set if slice is partial (slice with DT start/end)
    - dataTakeID (copied from data_takes section in scenario)
    - swathIdentifier (copied from scenario, either root, output section or
      data_takes section)
    '''
    PRODUCTS = ['S1_RAW__0S', 'S2_RAW__0S', 'S3_RAW__0S', 'Sx_RAW__0S',
                'S1_RAWP_0M', 'S2_RAWP_0M', 'S3_RAWP_0M', 'Sx_RAWP_0M',
                'RO_RAW__0S', 'RO_RAWP_0M',
                'EC_RAWP_0M', 'EC_RAWP_0S'
                ]

    _ACQ_PARAMS = [
        ('slice_frame_nr', 'slice_frame_nr', 'int')
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS + self._ACQ_PARAMS

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:
        # First copy the metadata from any input product (normally H or V)
        if not super().parse_inputs(input_products):
            return False

        start = self._hdr.begin_position
        stop = self._hdr.end_position
        if start is None or stop is None:
            self._logger.info('Cannot "merge" incomplete H or V slices, no data from input files available. Set metadata_source in output section.')
            return True

        # 'Merge' incomplete H or V slices. If either H or V (or both?) consists
        # of multiple parts, then use the overall time as period for the output.
        #
        # TODO: Check if validity times of the different parts also match?
        # These should match (belonging to the same slice #).
        if self._output_type in [
                'S1_RAW__0S', 'S2_RAW__0S', 'S3_RAW__0S', 'Sx_RAW__0S',
                'S1_RAWP_0M', 'S2_RAWP_0M', 'S3_RAWP_0M', 'Sx_RAWP_0M']:
            hv_products = ['RAWS025_10', 'RAWS026_10']
        elif self._output_type in ['RO_RAW__0S', 'RO_RAWP_0M']:
            hv_products = ['RAWS027_10', 'RAWS028_10']
        else:
            hv_products = ['RAWS035_10', 'RAWS036_10']

        nr_hv_found = [0, 0]
        for input in input_products:
            if input.file_type in hv_products:
                for file in input.file_names:
                    file, _ = os.path.splitext(file)    # Remove possible extension
                    gen = product_name.ProductName(self._compact_creation_date_epoch)
                    gen.parse_path(file)
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr = main_product_header.MainProductHeader()
                    hdr.parse(mph_file_name)
                    if hdr.begin_position is None or hdr.end_position is None:
                        raise ScenarioError('begin/end position not set in {}'.format(mph_file_name))
                    start = min(start, hdr.begin_position)
                    stop = max(stop, hdr.end_position)
                    # Diagnostics
                    idx = hv_products.index(input.file_type)
                    nr_hv_found[idx] += 1
        self._hdr.begin_position = start
        self._hdr.end_position = stop
        self._logger.debug('Merged {} H, V input products of type {}'.format(
            nr_hv_found, hv_products)
        )
        return True

    def _is_partial_slice(self, valid_start, valid_end, acq_start, acq_end):
        '''
        Compare validatity and acquisition times
        '''
        start_is_aligned = valid_start == acq_start
        end_is_aligned = valid_end == acq_end
        if not start_is_aligned and not end_is_aligned:
            self._logger.debug('Incomplete slice, start and end unaligned')
        elif not start_is_aligned:
            self._logger.debug('Incomplete slice, start unaligned')
        elif not end_is_aligned:
            self._logger.debug('Incomplete slice, end unaligned')
        return not start_is_aligned or not end_is_aligned

    def _generate_product(self, start, stop, data_take_config):
        if data_take_config.get('data_take_id') is None:
            raise ScenarioError('data_take_id field is mandatory in data_take section')

        _, hdr_params, acq_params = self.get_params()
        for param, hdr_field, ptype in hdr_params:
            self._read_config_param(data_take_config, param, self._hdr, hdr_field, ptype)
        for param, acq_field, ptype in acq_params:
            self._read_config_param(data_take_config, param, self._hdr.acquisitions[0], acq_field, ptype)

        self._logger.debug('Datatake {} from {} to {}'.format(self._hdr.acquisitions[0].data_take_id, start, stop))

        # Setup MPH fields. Validity time is not changed, should still be the
        # theoretical slice start/end.
        self._hdr.product_type = self._resolve_wildcard_product_type()
        self._hdr.set_phenomenon_times(start, stop)
        self._hdr.incomplete_l0_slice = False  # TODO!
        self._hdr.partial_l0_slice = self._is_partial_slice(
            self._hdr.validity_start,
            self._hdr.validity_stop,
            start,
            stop
        )

        # Determine and set the slice number if not set already.
        if self._hdr.acquisitions[0].slice_frame_nr is None:
            # Get slice number from middle of slice to deal with merged slices.
            middle = start + (stop - start) / 2
            self._hdr.acquisitions[0].slice_frame_nr = self._get_slice_frame_nr(middle, constants.SLICE_GRID_SPACING)

        # Create name generator
        name_gen = self._create_name_generator(self._hdr)
        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)

        # Create directory and files
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        # H/V measurement data
        file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxh'))
        self._add_file_to_product(file_path, self._size_mb // 2)
        file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxv'))
        self._add_file_to_product(file_path, self._size_mb // 2)

        # Ancillary products, low rate
        file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxh'))
        self._add_file_to_product(file_path, 0)
        file_path = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxv'))
        self._add_file_to_product(file_path, 0)

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
                self._logger.warning(f'Could not find slice bounds. Using {self._hdr.begin_position} as validity start.')
                self._hdr.validity_start = self._hdr.begin_position
            else:
                self._logger.debug(f'Use slice start {slice_bounds[0]} as input for validity start time')
                self._hdr.validity_start = slice_bounds[0] - constants.SLICE_OVERLAP_START
        if self._hdr.validity_stop is None:
            if slice_bounds is None:
                self._logger.warning(f'Could not find slice bounds. Using {self._hdr.end_position} as validity end.')
                self._hdr.validity_stop = self._hdr.end_position
            else:
                self._logger.debug(f'Use slice end {slice_bounds[1]} as input for validity stop time')
                self._hdr.validity_stop = slice_bounds[1] + constants.SLICE_OVERLAP_END

        # Find data take(s) in this slice and create products for each segment.
        data_takes = self._scenario_config.get('data_takes')
        if not data_takes:
            raise ScenarioError('Missing "data_takes" section in scenario')
        if any([dt.get('start') is None or dt.get('stop') is None for dt in data_takes]):
            raise ScenarioError('data_take in config should contain start/stop elements')
        data_takes.sort(key=lambda dt: self._time_from_iso(dt['start']))

        # Select the data takes that fall within the begin and end position.
        data_takes = [dt for dt in data_takes if self._time_from_iso(dt['start']) <= self._hdr.end_position
                      and self._time_from_iso(dt['stop']) >= self._hdr.begin_position]

        start = self._hdr.begin_position
        stop = self._hdr.end_position
        if data_takes and start < self._time_from_iso(data_takes[0]['start']):
            self._logger.warning('Start time outside data takes: using first data take start time')
        for dt in data_takes:
            dt_start = self._time_from_iso(dt['start'])
            dt_stop = self._time_from_iso(dt['stop'])
            self._generate_product(max(start, dt_start), min(dt_stop, stop), dt)

        if len(data_takes) == 0:
            self._logger.info('No products generated, start/stop outside data takes?')


class Sx_RAW__0M(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level0 Monitoring products.

    Input is a set of sliced monitoring products.
    The product:
    - removes overlaps between adjacent monitoring products
    - stitches the resulting products

    The generator adjusts the following metadata:
    - wrsLatitudeGrid, aka the slice_frame_nr, to '___'
    - partialSlice, set to false
    - incompleteSlice, set to false
    - phenomenonTime (the acquisition begin/end times)
    - validTime
    '''

    PRODUCTS = ['S1_RAW__0M', 'S2_RAW__0M', 'S3_RAW__0M', 'Sx_RAW__0M',
                'RO_RAW__0M', 'EC_RAW__0M', 'EC_RAW__0S']

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:
        # Retrieves the metadata
        if not super().parse_inputs(input_products):
            return False

        start = self._hdr.begin_position
        stop = self._hdr.end_position
        if start is None or stop is None:
            self._logger.info('Cannot "merge" incomplete H or V slices, no data from input files available. Set metadata_source in output section.')
            return True

        # The final product should cover the complete data take.
        id = self._hdr.acquisitions[0].data_take_id
        for input in input_products:
            for file in input.file_names:
                gen = product_name.ProductName(self._compact_creation_date_epoch)
                gen.parse_path(file)
                # Derive mph file name from product name, parse header
                hdr = self._hdr
                mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                hdr.parse(mph_file_name)
                if hdr.begin_position is None or hdr.end_position is None:
                    raise ScenarioError('begin/end position not set in {}'.format(mph_file_name))
                input_id = hdr.acquisitions[0].data_take_id
                # Sanity check: do all products belong to the same data take?
                if input_id != id:
                    self._logger.warning('Data take ID {} differs from {} in {}, product ignored'.format(input_id, os.path.basename(file), id))
                    continue
                self._logger.debug('Data take id {} of {} matches'.format(input_id, os.path.basename(file)))
                start = min(start, hdr.begin_position)
                stop = max(stop, hdr.end_position)
        if start != self._hdr.begin_position or stop != self._hdr.end_position:
            self._logger.debug('Adjust begin/end times to {} - {}'.format(start, stop))
        self._hdr.begin_position = start
        self._hdr.end_position = stop
        return True

    def generate_output(self):
        super().generate_output()

        # Sanity check
        if self._hdr.begin_position is None or self._hdr.end_position is None:
            raise ScenarioError('begin/end position must be set')

        # If not read from an input product, use begin/end position as starting point
        if self._hdr.validity_start is None:
            self._hdr.validity_start = self._hdr.begin_position
            self._logger.debug('Use begin_position as input for validity start time')
        if self._hdr.validity_stop is None:
            self._hdr.validity_stop = self._hdr.end_position
            self._logger.debug('Use end_position as input for validity stop time')

        # Setup all fields mandatory for a level0 product.
        self._hdr.product_type = self._resolve_wildcard_product_type()
        self._hdr.incomplete_l0_slice = False
        self._hdr.partial_l0_slice = False
        self._hdr.acquisitions[0].slice_frame_nr = None

        name_gen = self._create_name_generator(self._hdr)
        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)

        # Create directory and files
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        # H/V measurement data
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxh'))
        self._add_file_to_product(file_name, self._size_mb // 2)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxv'))
        self._add_file_to_product(file_name, self._size_mb // 2)

        # Ancillary products, low rate
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxh'))
        self._add_file_to_product(file_name, 0)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxv'))
        self._add_file_to_product(file_name, 0)

        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_name)


class AC_RAW__0A(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 ancillary products.

    Inputs are a Sx_RAW__0M monitoring product and all RAWS022_10 products
    belonging to the same data take.
    The output takes the begin/end times of the monitoring product and adds the
    leading/trailing margins as specified in the job order or the scenario.
    (defaults is 16/0 seconds).

    The generator adjusts the following metadata:
    - wrsLatitudeGrid, aka the slice_frame_nr, to '___'
    - partialSlice, set to false
    - incompleteSlice, set to false
    - phenomenonTime (the acquisition begin/end times)
    - validTime
    '''

    PRODUCTS = ['AC_RAW__0A']
    DEFAULT_LEADING_MARGIN = 16.0
    DEFAULT_TRAILING_MARGIN = 0.0

    _GENERATOR_PARAMS = [
        ('leading_margin', '_leading_margin', 'float'),
        ('trailing_margin', '_trailing_margin', 'float')
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        # TODO: read lead time from JobOrder (processing parameters)
        self._leading_margin = self.DEFAULT_LEADING_MARGIN
        self._trailing_margin = self.DEFAULT_TRAILING_MARGIN

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self._GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        # Sanity check
        if self._hdr.begin_position is None or self._hdr.end_position is None:
            raise ScenarioError('Begin/end position must be set')

        # Adjust start/stop times, add margins
        self._hdr.begin_position -= datetime.timedelta(0, self._leading_margin)
        self._hdr.end_position += datetime.timedelta(0, self._trailing_margin)

        # If not read from an input product, use begin/end position as starting point
        if self._hdr.validity_start is None:
            self._hdr.validity_start = self._hdr.begin_position
            self._logger.debug('Use begin_position as input for validity start time')
        if self._hdr.validity_stop is None:
            self._hdr.validity_stop = self._hdr.end_position
            self._logger.debug('Use end_position as input for validity stop time')

        # Setup other MPH fields
        self._hdr.product_type = self._output_type
        self._hdr.incomplete_l0_slice = False
        self._hdr.partial_l0_slice = False
        self._hdr.acquisitions[0].slice_frame_nr = None

        name_gen = self._create_name_generator(self._hdr)
        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)

        # Create directory and files
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        file_path = os.path.join(dir_name, name_gen.generate_binary_file_name())
        self._add_file_to_product(file_path, self._size_mb)
        file_path = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_path)

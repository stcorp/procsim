'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 1 product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0044
'''
import datetime
import os
from typing import List, Tuple

from procsim.core.exceptions import GeneratorError, ScenarioError
from procsim.core.job_order import JobOrderInput
from . import main_product_header

from . import constants, product_generator, product_name, product_types

_GENERATOR_PARAMS = [
    ('output_path', '_output_path', 'str'),
]
_HDR_PARAMS = [
    ('baseline', 'product_baseline', 'int'),
    ('begin_position', 'begin_position', 'date'),
    ('end_position', 'end_position', 'date'),
    # L0 + L1
    ('swath', 'sensor_swath', 'str'),
    ('operational_mode', 'sensor_mode', 'str'),
    # L1 only
    ('footprint_polygon', 'footprint_polygon', 'str'),
    ('center_points', 'center_points', 'str'),
    ('browse_ref_id', 'browse_ref_id', 'str'),
    ('browse_image_filename', 'browse_image_filename', 'str')
]
_ACQ_PARAMS = [
    # L0 + L1
    ('mission_phase', 'mission_phase', 'str'),
    ('data_take_id', 'data_take_id', 'int'),
    ('global_coverage_id', 'global_coverage_id', 'str'),
    ('major_cycle_id', 'major_cycle_id', 'str'),
    ('repeat_cycle_id', 'repeat_cycle_id', 'str'),
    ('track_nr', 'track_nr', 'int'),
    # ('slice_frame_nr', 'slice_frame_nr', 'int')
]


class Level1Stripmap(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating dummy Biomass Level-1a Single-look Complex Slant (SCS) and
    the Level-1b Detected Ground Multi-look (DGM) products.

    Input are a single Sx_RAW__0S, Sx_RAW__0M, AUX_ORB___, AUX_ATT___, ...
    product. Output is a series of frames.

    The generator adjusts the following metadata:
    - phenomenonTime, acquisition begin/end times.
    - validTime, theoretical frame begin/end times (including overlap).
    - wrsLatitudeGrid, aka the slice_frame_nr.
    '''
    PRODUCTS = ['S1_SCS__1S', 'S2_SCS__1S', 'S3_SCS__1S', 'Sx_SCS__1S',
                'S1_SCS__1M', 'S2_SCS__1M', 'S3_SCS__1M', 'Sx_SCS__1M',
                'S1_DGM__1S', 'S2_DGM__1S', 'S3_DGM__1S', 'Sx_DGM__1S',
                'RO_SCS__1S']

    _GENERATOR_PARAMS: List[tuple] = [
        ('enable_framing', '_enable_framing', 'bool')
        # ('frame_grid_spacing', '_frame_grid_spacing', 'float'),
        # ('frame_overlap', '_frame_overlap', 'float'),
        # ('frame_lower_bound', '_frame_lower_bound', 'float'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._enable_framing = True
        self._frame_grid_spacing = constants.FRAME_GRID_SPACING
        self._frame_overlap = constants.FRAME_OVERLAP
        self._frame_lower_bound = constants.FRAME_LOWER_BOUND

    def get_params(self) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        return _GENERATOR_PARAMS + self._GENERATOR_PARAMS, _HDR_PARAMS, _ACQ_PARAMS

    def _generate_product(self):
        # Setup MPH
        acq = self._hdr.acquisitions[0]

        name_gen = product_name.ProductName()
        name_gen.file_type = self._hdr.product_type
        name_gen.start_time = self._hdr.validity_start
        name_gen.stop_time = self._hdr.validity_stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(self._create_date)
        name_gen.mission_phase = acq.mission_phase
        name_gen.global_coverage_id = acq.global_coverage_id
        name_gen.major_cycle_id = acq.major_cycle_id
        name_gen.repeat_cycle_id = acq.repeat_cycle_id
        name_gen.track_nr = acq.track_nr
        name_gen.frame_slice_nr = acq.slice_frame_nr

        dir_name = name_gen.generate_path_name()
        self._hdr.set_product_filename(dir_name)
        self._logger.info('Create {}'.format(dir_name))

        # List with files: array of directory, suffix, extension
        files = [
            (['annotation'], 'annot', 'xml'),
            (['annotation', 'calibration'], 'cal', 'xml'),
            (['annotation', 'calibration'], 'ant', 'dat'),
            (['annotation', 'calibration'], 'noise', 'dat'),
            (['annotation', 'navigation'], 'orb', 'xml'),
            (['annotation', 'navigation'], 'att', 'xml'),
            (['annotation', 'geometry'], 'geoloc', 'tiff'),

            (['preview'], 'map', 'kml'),
            (['preview'], 'ql', 'png'),

            (['measurement', 'rfi'], 'rfi', 'tbd'),
            (['measurement', 'ionosphere'], 'iono', 'tiff'),

            (['schema'], 'Annotation', 'xsd'),
            (['schema'], 'Orbit', 'xsd'),
            (['schema'], 'Attitude', 'xsd')
        ]
        if self._hdr.product_type in product_types.L1S_PRODUCTS:
            files += [
                (['measurement'], 'i_hh', 'tiff'),
                (['measurement'], 'i_hv', 'tiff'),
                (['measurement'], 'i_vh', 'tiff'),
                (['measurement'], 'i_vv', 'tiff')
            ]

        # Create MPH
        base_path = os.path.join(self._output_path, dir_name)
        os.makedirs(base_path, exist_ok=True)
        file_name = os.path.join(base_path, name_gen.generate_mph_file_name())
        self._hdr.write(file_name)

        # Create other product files
        XML = ['xml', 'xsd']
        nr_binfiles = len([ext for _, _, ext in files if ext in XML])
        for dirs, suffix, ext in files:
            path = os.path.join(base_path, *dirs)
            os.makedirs(path, exist_ok=True)
            file_name = os.path.join(path, name_gen.generate_binary_file_name('_' + suffix, ext))
            size = 0 if ext in XML else self._size_mb // nr_binfiles
            self._generate_bin_file(file_name, size)

    def generate_output(self):
        super().generate_output()

        self._create_date = self._hdr.end_position   # HACK: fill in current date?
        self._hdr.product_type = self._resolve_wildcard_product_type()

        if not self._enable_framing:
            self._hdr.acquisitions[0].slice_frame_nr = None
            self._hdr.partial_l1_frame = False
            self._generate_product()
        else:
            self._do_framing()

    def _do_framing(self):
        # Perform framing. Input is a slice. A frame overlap is added at the end.
        acq_start, acq_end = self._hdr.begin_position, self._hdr.end_position
        slice_start, slice_end = self._hdr.validity_start, self._hdr.validity_stop
        if slice_start is None or slice_end is None or acq_start is None or acq_end is None:
            raise ScenarioError('Start/stop times must be known here!')

        if slice_start != acq_start:
            pass  # First slice of a data take (partial)
        if slice_end != acq_end:
            pass  # Last slice of a data take (partial)

        # Subtract slice overlaps to get the exact slice grid nodes
        slice_start += constants.SLICE_OVERLAP_START
        slice_end -= constants.SLICE_OVERLAP_END
        slice_nr = self._hdr.acquisitions[0].slice_frame_nr

        # Sanity checks
        if slice_nr is None:
            raise ScenarioError('Cannot perform framing, slice nr. is not known')
        delta = (slice_end - slice_start) - constants.FRAME_GRID_SPACING * 5
        if delta < -datetime.timedelta(0, 0.01) or delta > datetime.timedelta(0, 0.01):
            raise GeneratorError('Cannot perform framing, slice length != 5x frame length ({} != {})'.format(
                slice_end - slice_start, constants.FRAME_GRID_SPACING * 5))

        for n in range(5):
            frame_nr = 1 + n + (slice_nr - 1) * 5
            frame_start = slice_start + n * constants.FRAME_GRID_SPACING
            frame_end = frame_start + constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP
            start = min(frame_start, acq_start)
            end = max(frame_end, acq_end)
            if end - start < self._frame_lower_bound:
                self._logger.debug('Drop frame {}'.format(frame_nr))
            else:
                is_partial = (acq_start > frame_start) or (acq_end < frame_end)
                self._hdr.acquisitions[0].slice_frame_nr = frame_nr
                self._hdr.partial_l1_frame = is_partial
                self._hdr.set_phenomenon_times(start, end)
                self._hdr.set_validity_times(frame_start, frame_end)
                if is_partial:
                    self._logger.debug('Frame {} is partial'.format(frame_nr))
                self._generate_product()


class Level1Stack(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating dummy Biomass Level-1c Stack Products.

    Inputs are an AUX_PPS___ product, and 2 or more L1a SCS products from
    different repeat cycles, with the same framenr, swath ID, major cycle ID,
    global coverage ID and mission phase.
    Outputs are a Sx_STA_1S and Sx_STA_1M product for every input SCS product.

    Inputs are checked and warnings are produced if
    - not enough input products are available.
    - framenr, swath, major cycle ID, global coverage ID, mission phase differ.
    - repeat cycle IDs do not differ.

    The generator adjusts the following metadata:
    - None
    '''
    PRODUCTS = ['S1_STA__1S', 'S2_STA__1S', 'S3_STA__1S', 'Sx_STA__1S',
                'S1_STA__1M', 'S2_STA__1M', 'S3_STA__1M', 'Sx_STA__1M']

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

    def get_params(self) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        return _GENERATOR_PARAMS, _HDR_PARAMS, _ACQ_PARAMS

    def _check_sanity(self, file, hdr):
        # Compare metadata fields, test if they suit the input requirements for
        # a stacked product.
        acq = self._hdr.acquisitions[0]
        swath = self._hdr.sensor_swath
        frame_nr = acq.slice_frame_nr
        major_cycle_id = acq.major_cycle_id
        global_coverage_id = acq.global_coverage_id
        mission_phase = acq.mission_phase
        repeat_cycle_id = acq.repeat_cycle_id

        file_base = os.path.basename(file)
        acq = hdr.acquisitions[0]
        if swath != hdr.sensor_swath:
            self._logger.warning('Swath {} of {} does not match {}'.format(
                hdr.sensor_swath, file_base, swath))
        if frame_nr != acq.slice_frame_nr:
            self._logger.warning('Framenr {} of {} does not match {}'.format(
                acq.slice_frame_nr, file_base, frame_nr))
        if major_cycle_id != acq.major_cycle_id:
            self._logger.warning('Major cycle id {} of {} does not match {}'.format(
                acq.major_cycle_id, file_base, major_cycle_id))
        if global_coverage_id != acq.global_coverage_id:
            self._logger.warning('Global coverage id {} of {} does not match {}'.format(
                acq.global_coverage_id, file_base, global_coverage_id))
        if mission_phase != acq.mission_phase:
            self._logger.warning('Mission phase {} of {} does not match {}'.format(
                acq.mission_phase, file_base, mission_phase))
        if repeat_cycle_id == acq.repeat_cycle_id:
            self._logger.warning('Repeat cycle ID {} of {} is the same'.format(
                repeat_cycle_id, file_base))

    def parse_inputs(self, inputs: List[JobOrderInput]) -> bool:
        if not super().parse_inputs(inputs):
            return False

        L1_SCS_PRODUCTS = ['S1_SCS__1S', 'S2_SCS__1S', 'S3_SCS__1S']

        # Do sanity checks on input data.
        if self._hdr.product_type not in L1_SCS_PRODUCTS:
            self._logger.warning('Metadata source of Stack product should be an Sx_SCS__1S product.')
            return True
        count = 1
        for input in inputs:
            for file in input.file_names:
                file, _ = os.path.splitext(file)    # Remove possible '.zip'
                # Skip the our metadata source reference
                if self._meta_data_source_file == file:
                    continue
                gen = product_name.ProductName()
                gen.parse_path(file)
                mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                hdr = main_product_header.MainProductHeader()
                hdr.parse(mph_file_name)
                if hdr.product_type not in L1_SCS_PRODUCTS:
                    continue
                self._check_sanity(file, hdr)
                count += 1
        phase = self._hdr.acquisitions[0].mission_phase
        if count < 2:
            self._logger.warning('At least two Sx_SCS__1S products should be input to generate the Stack')
        elif phase == 'TOMOGRAPHIC' and count > 7:
            self._logger.warning('{} inputs, max 7 input products in Tomographic phase'.format(count))
        elif phase == 'INTERFEROMETRIC' and count > 3:
            self._logger.warning('{} inputs, max 3 input products in Interferometric phase'.format(count))
        else:
            self._logger.debug('{} SCS products input to generate the Stack'.format(count))
        return True

    def generate_output(self):
        super().generate_output()

        self._create_date = self._hdr.end_position   # HACK: fill in current date?
        self._hdr.product_type = self._resolve_wildcard_product_type()

        # Setup MPH
        acq = self._hdr.acquisitions[0]
        name_gen = product_name.ProductName()
        name_gen.file_type = self._hdr.product_type
        name_gen.start_time = self._hdr.validity_start
        name_gen.stop_time = self._hdr.validity_stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(self._create_date)
        name_gen.mission_phase = acq.mission_phase
        name_gen.global_coverage_id = acq.global_coverage_id
        name_gen.major_cycle_id = acq.major_cycle_id
        name_gen.repeat_cycle_id = acq.repeat_cycle_id
        name_gen.track_nr = acq.track_nr
        name_gen.frame_slice_nr = acq.slice_frame_nr

        dir_name = name_gen.generate_path_name()
        self._hdr.set_product_filename(dir_name)
        self._logger.info('Create {}'.format(dir_name))

        # List with files: array of directory, suffix, extension
        files = [
            (['master_annotation'], 'annot', 'xml'),
            (['master_annotation', 'navigation'], 'orb', 'xml'),
            (['master_annotation', 'navigation'], 'att', 'xml'),
            (['master_annotation', 'geometry'], 'geoloc', 'tiff'),

            (['annotation'], 'annot', 'xml'),
            (['annotation', 'calibration'], 'cal', 'xml'),
            (['annotation', 'calibration'], 'noise', 'dat'),
            (['annotation', 'navigation'], 'orb', 'xml'),
            (['annotation', 'navigation'], 'att', 'xml'),

            (['coregistration'], 'shift', 'tiff'),

            (['InSAR'], 'delta_iono', 'tiff'),
            (['InSAR'], 'rfi_impact', 'tiff'),
            (['InSAR'], 'ground_cal', 'tiff'),

            (['preview'], 'map', 'kml'),
            (['preview'], 'ql', 'png'),

            (['schema'], 'Annotation', 'xsd'),
            (['schema'], 'Orbit', 'xsd'),
            (['schema'], 'Attitude', 'xsd')
        ]
        if self._hdr.product_type in product_types.L1S_PRODUCTS:
            files += [
                (['measurement'], 'i_hh', 'tiff'),
                (['measurement'], 'i_hv', 'tiff'),
                (['measurement'], 'i_vh', 'tiff'),
                (['measurement'], 'i_vv', 'tiff')
            ]

        # Create MPH
        base_path = os.path.join(self._output_path, dir_name)
        os.makedirs(base_path, exist_ok=True)
        file_name = os.path.join(base_path, name_gen.generate_mph_file_name())
        self._hdr.write(file_name)

        # Create other product files
        XML = ['xml', 'xsd']
        nr_binfiles = len([ext for _, _, ext in files if ext in XML])
        for dirs, suffix, ext in files:
            path = os.path.join(base_path, *dirs)
            os.makedirs(path, exist_ok=True)
            file_name = os.path.join(path, name_gen.generate_binary_file_name('_' + suffix, ext))
            size = 0 if ext in XML else self._size_mb // nr_binfiles
            self._generate_bin_file(file_name, size)

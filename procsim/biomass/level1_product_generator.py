'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 1 product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0044
'''
import datetime
import os
from typing import Iterable, List, Tuple

from procsim.core.exceptions import GeneratorError, ScenarioError
from procsim.core.job_order import JobOrderInput

from . import (constants, main_product_header, product_generator, product_name,
               product_types)

_L1_SCS_PRODUCTS = ['S1_SCS__1S', 'S2_SCS__1S', 'S3_SCS__1S']

_HDR_PARAMS = [
    # L0 + L1
    ('validity_start', 'validity_start', 'date'),
    ('validity_stop', 'validity_stop', 'date'),
    ('swath', 'sensor_swath', 'str'),
    ('operational_mode', 'sensor_mode', 'str'),
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
    ('track_nr', 'track_nr', 'str'),
    ('slice_frame_nr', 'slice_frame_nr', 'int')
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
        ('enable_framing', '_enable_framing', 'bool'),
        ('frame_grid_spacing', '_frame_grid_spacing', 'float'),
        ('frame_overlap', '_frame_overlap', 'float'),
        ('frame_lower_bound', '_frame_lower_bound', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float')
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._enable_framing = True
        self._frame_grid_spacing = constants.FRAME_GRID_SPACING
        self._frame_overlap = constants.FRAME_OVERLAP
        self._frame_lower_bound = constants.FRAME_LOWER_BOUND
        self._slice_overlap_start = constants.SLICE_OVERLAP_START
        self._slice_overlap_end = constants.SLICE_OVERLAP_END

    def get_params(self) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        gen, hdr, acq = super().get_params()
        return gen + self._GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def _generate_product(self):
        name_gen = self._create_name_generator(self._hdr)
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

        # Sanity check
        if self._hdr.begin_position is None or self._hdr.end_position is None:
            raise ScenarioError('Begin/end position must be set')

        # If not read from an input product, use begin/end position as starting point
        if self._hdr.validity_start is None:
            self._hdr.validity_start = self._hdr.begin_position
            self._logger.debug('Use begin_position as input for validity start time')
        if self._hdr.validity_stop is None:
            self._hdr.validity_stop = self._hdr.end_position
            self._logger.debug('Use end_position as input for validity stop time')

        self._hdr.product_type = self._resolve_wildcard_product_type()

        if not self._enable_framing:
            self._hdr.acquisitions[0].slice_frame_nr = None
            self._hdr.partial_l1_frame = False
            self._generate_product()
        else:
            self._generate_frames()

    def _generate_frames(self):
        # Input is a slice. A frame overlap is added at the end of each frame.
        acq_start, acq_end = self._hdr.begin_position, self._hdr.end_position
        slice_start, slice_end = self._hdr.validity_start, self._hdr.validity_stop
        if slice_start is None or slice_end is None or acq_start is None or acq_end is None:
            raise ScenarioError('Start/stop times must be known here!')

        if slice_start != acq_start:
            pass  # First slice of a data take (partial)
        if slice_end != acq_end:
            pass  # Last slice of a data take (partial)

        # Slice start/end are the 'grid nodes', but with slice overlap.
        # Subtract overlaps to get the exact slice grid nodes
        slice_start += self._slice_overlap_start
        slice_end -= self._slice_overlap_end
        slice_nr = self._hdr.acquisitions[0].slice_frame_nr

        print('{} {} {} {}'.format(slice_start, slice_end, self._slice_overlap_start, self._slice_overlap_end))

        # Sanity checks
        if slice_nr is None:
            raise ScenarioError('Cannot perform framing, slice nr. is not known')
        delta = (slice_end - slice_start) - self._frame_grid_spacing * 5
        if delta < -datetime.timedelta(0, 0.01) or delta > datetime.timedelta(0, 0.01):
            raise GeneratorError('Cannot perform framing, slice length (without overlaps) != 5x frame length ({} != 5x{})'.format(
                slice_end - slice_start, self._frame_grid_spacing))
        for n in range(5):
            frame_nr = 1 + n + (slice_nr - 1) * 5
            frame_start = slice_start + n * self._frame_grid_spacing
            frame_end = frame_start + self._frame_grid_spacing + self._frame_overlap
            start = max(frame_start, acq_start)
            end = min(frame_end, acq_end)
            if end - start < self._frame_lower_bound:
                self._logger.debug('Do not generate frame {}, not enough data'.format(frame_nr))
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
    track nr, global coverage ID and mission phase.
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
        self._hdrs = []   # Metadata for all output products
        list()

    def get_params(self) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        gen, hdr, acq = super().get_params()
        return gen, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def _check_sanity(self, file, hdr) -> bool:
        # Compare metadata fields, test if they suit the input requirements for
        # a stacked product. Log only the first warning! Returns True if ok.
        acq = self._hdr.acquisitions[0]
        swath = self._hdr.sensor_swath
        frame_nr = acq.slice_frame_nr
        track_nr = acq.track_nr
        major_cycle_id = acq.major_cycle_id
        global_coverage_id = acq.global_coverage_id
        mission_phase = acq.mission_phase
        repeat_cycle_id = acq.repeat_cycle_id

        file_base = os.path.basename(file)
        acq = hdr.acquisitions[0]
        is_ok = False
        if swath != hdr.sensor_swath:
            self._logger.warning('Swath {} of {} does not match {}'.format(
                hdr.sensor_swath, file_base, swath))
        elif frame_nr != acq.slice_frame_nr:
            self._logger.warning('Framenr {} of {} does not match {}'.format(
                acq.slice_frame_nr, file_base, frame_nr))
        elif track_nr != acq.track_nr:
            self._logger.warning('Tracknr {} of {} does not match {}'.format(
                acq.track_nr, file_base, track_nr))
        elif major_cycle_id != acq.major_cycle_id:
            self._logger.warning('Major cycle id {} of {} does not match {}'.format(
                acq.major_cycle_id, file_base, major_cycle_id))
        elif global_coverage_id != acq.global_coverage_id:
            self._logger.warning('Global coverage id {} of {} does not match {}'.format(
                acq.global_coverage_id, file_base, global_coverage_id))
        elif mission_phase != acq.mission_phase:
            self._logger.warning('Mission phase {} of {} does not match {}'.format(
                acq.mission_phase, file_base, mission_phase))
        elif repeat_cycle_id == acq.repeat_cycle_id:
            self._logger.warning('Repeat cycle ID {} of {} is the same'.format(
                repeat_cycle_id, file_base))
        else:
            is_ok = True
        return is_ok

    def parse_inputs(self, inputs: Iterable[JobOrderInput]) -> bool:
        '''
        We generate products for every input SCS input product, so we need
        metadata from all Sx_SCS input products instead of from a single
        metadata source.
        '''
        if not super().parse_inputs(inputs):
            return False

        if self._meta_data_source:
            if self._hdr.product_type not in _L1_SCS_PRODUCTS:
                self._logger.error('metadata_source of Stack product must be an Sx_SCS__1S product.')
                return True
            self._hdrs.append(self._hdr)

        # Here we store the meta data for every output product. Start with the
        # 'metadata source' (the first Sx_SCS product)

        # Go again over the list with input products. For every other SCS
        # product, do a sanity check and store meta data if ok.
        for input in inputs:
            for file in input.file_names:
                file, _ = os.path.splitext(file)    # Remove possible extension
                # Skip the our metadata source reference
                if self._meta_data_source_file == file:
                    continue
                gen = product_name.ProductName(self._compact_creation_date_epoch)
                gen.parse_path(file)
                mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                hdr = main_product_header.MainProductHeader()
                hdr.parse(mph_file_name)
                if hdr.product_type not in _L1_SCS_PRODUCTS:
                    continue
                if self._check_sanity(file, hdr):
                    self._hdrs.append(hdr)
        phase = self._hdr.acquisitions[0].mission_phase
        count = len(self._hdrs)
        if count < 2:
            self._logger.warning('At least two Sx_SCS__1S products needed to generate the Stack')
        elif phase == 'TOMOGRAPHIC' and count > 7:
            self._logger.warning('{} inputs, max 7 input products in Tomographic phase'.format(count))
        elif phase == 'INTERFEROMETRIC' and count > 3:
            self._logger.warning('{} inputs, max 3 input products in Interferometric phase'.format(count))
        else:
            self._logger.debug('{} SCS products input to generate the Stack'.format(count))
        return True

    def generate_output(self):
        super().generate_output()

        if not self._hdrs:
            self._logger.debug('No metadata from input products, generate stacked product using scenario parameters')
            self._hdrs.append(self._hdr)

        for hdr in self._hdrs:
            self._generate_level1_stacked_product(hdr)

    def _generate_level1_stacked_product(self, hdr: main_product_header.MainProductHeader):

        # Sanity check
        if hdr.begin_position is None or hdr.end_position is None:
            raise ScenarioError('Begin/end position must be set')

        # If not read from an input product, use begin/end position as starting point
        if hdr.validity_start is None:
            hdr.validity_start = hdr.begin_position
        if self._hdr.validity_stop is None:
            hdr.validity_stop = hdr.end_position

        hdr.product_type = self._resolve_wildcard_product_type()
        hdr.processing_date = self._creation_date

        # Setup MPH
        name_gen = self._create_name_generator(hdr)
        dir_name = name_gen.generate_path_name()
        hdr.set_product_filename(dir_name)
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
        if hdr.product_type in product_types.L1S_PRODUCTS:
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
        hdr.write(file_name)

        # Create other product files
        XML = ['xml', 'xsd']
        nr_binfiles = len([ext for _, _, ext in files if ext in XML])
        for dirs, suffix, ext in files:
            path = os.path.join(base_path, *dirs)
            os.makedirs(path, exist_ok=True)
            file_name = os.path.join(path, name_gen.generate_binary_file_name('_' + suffix, ext))
            size = 0 if ext in XML else self._size_mb // nr_binfiles
            self._generate_bin_file(file_name, size)

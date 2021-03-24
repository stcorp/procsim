'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 1 product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0044
'''
import datetime
import os
from typing import List, Tuple

from biomass import product_generator, product_name, constants, product_types


_GENERATOR_PARAMS = [
    ('output_path', '_output_path', 'str'),
]
_HDR_PARAMS = [
    # All
    ('baseline', 'product_baseline', 'int'),
    # All but sliced products
    ('begin_position', 'begin_position', 'date'),
    ('end_position', 'end_position', 'date'),
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
    ('track_nr', 'track_nr', 'int'),
    ('slice_frame_nr', 'slice_frame_nr', 'int')
]


class Sx_SCS__1S(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating dummy Biomass Level-1a Single-look Complex Slant (SCS) and
    the Level-1b Detected Ground Multi-look (DGM) products.

    Input are a single Sx_RAW__0S, Sx_RAW__0M, AUX_ORB___, AUX_ATT___, ...
    product. Output is a series of frames.

    '''

    _GENERATOR_PARAMS: List[tuple] = [
        ('enable_framing', '_enable_framing', 'bool')
        # ('frame_grid_spacing', '_frame_grid_spacing', 'float'),
        # ('frame_overlap', '_frame_overlap', 'float'),
        # ('frame_lower_bound', '_frame_lower_bound', 'float'),
    ]

    PRODUCTS = ['S1_SCS__1S', 'S2_SCS__1S', 'S3_SCS__1S', 'Sx_SCS__1S',
                'S1_SCS__1M', 'S2_SCS__1M', 'S3_SCS__1M', 'Sx_SCS__1M',
                'S1_DGM__1S', 'S2_DGM__1S', 'S3_DGM__1S', 'Sx_DGM__1S']

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
        self._hdr.incomplete_l1_frame = False
        self._hdr.partial_l1_frame = False
        self._hdr.footprint_polygon = '-8.015716 -63.764648 -6.809171 -63.251038 -6.967323 -62.789612 -8.176149 -63.278503 -8.015716 -63.764648'
        self._hdr.center_points = '-7.492090 -63.27095'
        self._hdr.browse_ref_id = 'EPSG:4326'
        self._hdr.browse_image_filename = './preview/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_ql.png'

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
            raise Exception('Start/stop times must be known here!')

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
            raise Exception('Cannot perform framing, slice nr. is not known')
        delta = (slice_end - slice_start) - constants.FRAME_GRID_SPACING * 5
        if delta < -datetime.timedelta(0, 0.01) or delta > datetime.timedelta(0, 0.01):
            raise Exception('Cannot perform framing, slice length != 5x frame length ({} != {})'.format(
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
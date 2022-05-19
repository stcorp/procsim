'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 1 product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0044
'''
import datetime
from enum import Enum
import os
from typing import Iterable, List, Tuple
from textwrap import dedent
from xml.etree import ElementTree as et
import xml.dom.minidom as md

from procsim.biomass.constants import NUM_FRAMES_PER_SLICE, ORBITAL_PERIOD, SLICE_GRID_SPACING
from procsim.core.exceptions import GeneratorError, ScenarioError
from procsim.core.job_order import JobOrderInput

from . import constants, main_product_header, product_generator, product_name, product_types
from .product_generator import GeneratedFile

_L1_SCS_PRODUCTS = ['S1_SCS__1S', 'S2_SCS__1S', 'S3_SCS__1S']


FILENAME_DATETIME_FORMAT = '%Y%m%dT%H%M%S'
FIELD_DATETIME_FORMAT = 'UTC=%Y-%m-%dT%H:%M:%S'
FIELD_DATETIME_FORMAT_MICROSECONDS = 'UTC=%Y-%m-%dT%H:%M:%S.%f'


_HDR_PARAMS = [
    # L0 + L1
    ('validity_start', 'validity_start', 'date'),
    ('validity_stop', 'validity_stop', 'date'),
    ('swath', 'sensor_swath', 'str'),
    ('operational_mode', 'sensor_mode', 'str'),
    ('footprint_polygon', 'footprint_polygon', 'str'),
    ('center_points', 'center_points', 'str'),
    ('browse_ref_id', 'browse_ref_id', 'str'),
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


class FrameStatus(str, Enum):
    NOMINAL = 'NOMINAL'
    PARTIAL = 'PARTIAL'
    MERGED = 'MERGED'


class Frame:
    def __init__(self, id: int,
                 validity_start: datetime.datetime, validity_stop: datetime.datetime,
                 sensing_start: datetime.datetime, sensing_stop: datetime.datetime,
                 status: str = ''):
        self.id = id
        self.validity_start = validity_start
        self.validity_stop = validity_stop
        self.sensing_start = sensing_start
        self.sensing_stop = sensing_stop
        self.status = status

    def __str__(self):
        return f'{self.id} {self.sensing_start} {self.sensing_stop} {self.status}'


class Level1PreProcessor(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating virtual frames for the Level 1 processor.

    As input, it takes an L0 Monitoring product, an L0 standard product and an
    auxiliary orbit product (L0M, L0S, AUX_ORB).

    It outputs a Virtual Frame product for each L1 Frame contained in the L0S,
    each of them containing the framing parameters (mainly frame index and
    start-stop times) of a single frame.
    '''
    PRODUCTS = ['CPF_L1VFRA']

    _GENERATOR_PARAMS: List[tuple] = [
        ('file_class', '_file_class', 'str'),
        ('enable_framing', '_enable_framing', 'bool'),
        ('frame_grid_spacing', '_frame_grid_spacing', 'float'),
        ('frame_overlap', '_frame_overlap', 'float'),
        ('frame_lower_bound', '_frame_lower_bound', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict) -> None:
        super().__init__(logger, job_config, scenario_config, output_config)
        self._enable_framing = True
        self._frame_grid_spacing = constants.FRAME_GRID_SPACING
        self._frame_overlap = constants.FRAME_OVERLAP
        self._frame_lower_bound = constants.FRAME_MINIMUM_DURATION
        self._slice_overlap_start = constants.SLICE_OVERLAP_START
        self._slice_overlap_end = constants.SLICE_OVERLAP_END

        self._frame_status = None
        self._file_class = 'TEST'
        self._version_nr = 1
        self._hdr.product_baseline = 0  # This is the default for VFRA
        self._zip_output = False
        self._hdr.product_type = 'CPF_L1VFRA'

    def get_params(self) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        gen, hdr, acq = super().get_params()
        return gen + self._GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def generate_output(self) -> None:
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
            self._generate_frame_products()

    def _generate_frame_products(self):
        '''
        Generate a set of virtual frame products.
        '''
        # Input is a slice. A frame overlap is added at the end of each frame.
        acq_start, acq_end = self._hdr.begin_position, self._hdr.end_position
        slice_start, slice_end = self._hdr.validity_start, self._hdr.validity_stop
        slice_nr = self._hdr.acquisitions[0].slice_frame_nr
        first_frame_nr = (slice_nr - 1) * NUM_FRAMES_PER_SLICE + 1 if slice_nr else None

        # Sanity checks
        if slice_start is None or slice_end is None or acq_start is None or acq_end is None:
            raise ScenarioError('Start/stop times must be known here!')
        if slice_nr is None or first_frame_nr is None:
            raise ScenarioError('Cannot perform framing, slice nr. is not known')

        # Align slice start and end with grid.
        slice_start += self._slice_overlap_start
        slice_end -= self._slice_overlap_end

        # Check whether slice is incomplete. If so, the slice number/range is unreliable, so try to get them from ANX info.
        delta = (slice_end - slice_start) - self._frame_grid_spacing * NUM_FRAMES_PER_SLICE
        if delta < -datetime.timedelta(0, 0.01) or delta > datetime.timedelta(0, 0.01):
            first_frame_nr = self._get_slice_frame_nr(acq_start, self._frame_grid_spacing)
            slice_bounds = self._get_slice_frame_interval(acq_start, SLICE_GRID_SPACING)
            if first_frame_nr is None or slice_bounds is None:
                raise GeneratorError(dedent(f'\
                    Cannot perform framing, slice length (without overlaps) != {NUM_FRAMES_PER_SLICE}x frame length \
                    ({slice_end - slice_start} != {NUM_FRAMES_PER_SLICE}x{self._frame_grid_spacing}). \
                    Additionally, the slice frame number could not be determined from the ANX information.'))
            slice_start, slice_end = slice_bounds

        frames = self._generate_frames(slice_start, acq_start, acq_end, first_frame_nr)

        # Generate the virtual frame products.
        for frame in frames:
            # These are the only relevant fields for the virtual frame file.
            self._hdr.acquisitions[0].slice_frame_nr = frame.id
            self._hdr.set_phenomenon_times(frame.sensing_start, frame.sensing_stop)
            self._hdr.set_validity_times(frame.validity_start, frame.validity_stop)
            self._frame_status = frame.status

            self._generate_product()

    def _generate_frames(self, slice_start: datetime.datetime,
                         acq_start: datetime.datetime, acq_end: datetime.datetime,
                         first_frame_nr: int) -> List[Frame]:
        '''
        Generate a list of Frame objects between start and end times.
        '''
        # Get frame boundaries between the slice validity start and end.
        frame_bounds = [slice_start + d * self._frame_grid_spacing for d in range(NUM_FRAMES_PER_SLICE + 1)]

        # Map to frame instances.
        frames = []
        for fi in range(len(frame_bounds) - 1):
            # Continue if the acquisition start occurs after the frame bounds, or the acquisition end before.
            if acq_start > frame_bounds[fi + 1] or acq_end < frame_bounds[fi]:
                continue
            frames.append(Frame(
                id=fi + first_frame_nr,
                validity_start=frame_bounds[fi],
                validity_stop=frame_bounds[fi + 1] + self._frame_overlap,
                sensing_start=max(frame_bounds[fi], acq_start),
                sensing_stop=min(frame_bounds[fi + 1] + self._frame_overlap, acq_end),
                status=FrameStatus.NOMINAL
            ))

        # If the first or last frame are too short, merge them with their neghbours.
        if len(frames) > 1:
            if frames[0].sensing_stop - frames[0].sensing_start < self._frame_lower_bound:
                frames[1].sensing_start = frames[0].sensing_start
                frames.pop(0)
            if frames[-1].sensing_stop - frames[-1].sensing_start < self._frame_lower_bound:
                frames[-2].sensing_stop = frames[-1].sensing_stop
                frames.pop()

        # If any frames are partial or merged, mark them as such.
        for frame in frames:
            if frame.sensing_stop - frame.sensing_start < frame.validity_stop - frame.validity_start:
                frame.status = FrameStatus.PARTIAL
            elif frame.sensing_stop - frame.sensing_start > frame.validity_stop - frame.validity_start:
                frame.status = FrameStatus.MERGED

        return frames

    def _generate_product(self) -> None:
        '''
        Construct and write an output file given the variables set in this class.
        '''
        # Create a name generator, give it the right values and generate the product name.
        name_gen = self._create_name_generator(self._hdr)
        if self._creation_date is None:
            self._creation_date = datetime.datetime.now(tz=datetime.timezone.utc)
        name_gen.set_creation_date(self._creation_date)
        name_gen._file_class = self._file_class
        file_name = name_gen.generate_path_name()
        os.makedirs(self._output_path, exist_ok=True)
        full_file_name = os.path.join(self._output_path, file_name)

        # Ensure the presence of vital variables.
        if self._hdr.validity_start is None or self._hdr.validity_stop is None:
            raise GeneratorError('Validity start/stop times must be known here.')
        if self._hdr.acquisitions[0].slice_frame_nr is None:
            raise GeneratorError('Frame number must be known here.')

        # Construct the contents of the XML file.
        root = et.Element('Earth_Explorer_File')
        earth_explorer_header_node = et.SubElement(root, 'Earth_Explorer_Header')
        fixed_header_node = et.SubElement(earth_explorer_header_node, 'Fixed_Header')
        et.SubElement(fixed_header_node, 'File_Name').text = file_name[:-5]
        et.SubElement(fixed_header_node, 'File_Description').text = 'L1 Virtual Frame'
        et.SubElement(fixed_header_node, 'Notes').text = ''
        et.SubElement(fixed_header_node, 'Mission').text = 'BIOMASS'
        et.SubElement(fixed_header_node, 'File_Class').text = 'OPER'
        et.SubElement(fixed_header_node, 'File_Type').text = 'CPF_L1VFRA'
        validity_period_node = et.SubElement(fixed_header_node, 'Validity_Period')
        et.SubElement(fixed_header_node, 'File_Version').text = '01'
        source_node = et.SubElement(fixed_header_node, 'Source')

        et.SubElement(validity_period_node, 'Validity_Start').text = self._hdr.validity_start.strftime(FIELD_DATETIME_FORMAT)
        et.SubElement(validity_period_node, 'Validity_Stop').text = self._hdr.validity_stop.strftime(FIELD_DATETIME_FORMAT)

        et.SubElement(source_node, 'System').text = 'PDGS'
        et.SubElement(source_node, 'Creator').text = 'L1_F'
        et.SubElement(source_node, 'Creator_Version').text = '1'
        et.SubElement(source_node, 'Creation_Date').text = self._creation_date.strftime(FIELD_DATETIME_FORMAT) if self._creation_date else ''

        et.SubElement(earth_explorer_header_node, 'Variable_Header')

        data_block_node = et.SubElement(root, 'Data_Block')
        et.SubElement(data_block_node, 'source_L0S').text = ''
        et.SubElement(data_block_node, 'source_L0M').text = ''
        et.SubElement(data_block_node, 'source_AUX_ORB').text = ''
        et.SubElement(data_block_node, 'frame_id').text = str(self._hdr.acquisitions[0].slice_frame_nr)
        et.SubElement(data_block_node, 'frame_start_time').text = self._hdr.validity_start.strftime(FIELD_DATETIME_FORMAT_MICROSECONDS)
        et.SubElement(data_block_node, 'frame_stop_time').text = self._hdr.validity_stop.strftime(FIELD_DATETIME_FORMAT_MICROSECONDS)
        et.SubElement(data_block_node, 'frame_status').text = self._frame_status
        et.SubElement(data_block_node, 'ops_angle_start').text = str(self._ops_angle_from_frame_nr(self._hdr.acquisitions[0].slice_frame_nr))
        et.SubElement(data_block_node, 'ops_angle_stop').text = str(self._ops_angle_from_frame_nr(self._hdr.acquisitions[0].slice_frame_nr + 1))

        # Insert some indentation.
        dom = md.parseString(et.tostring(root, encoding='unicode'))
        xml_string = dom.toprettyxml(indent='    ')

        # Write to file.
        print()
        print(f'Filename: {full_file_name}')
        self._logger.info(f'Create {file_name}')
        with open(full_file_name, 'w') as file:
            file.write(xml_string)
            print(xml_string)

    def _ops_angle_from_frame_nr(self, frame_nr: int) -> float:
        '''
        Determine the ops_angle for a given frame number. This is the angle that
        describes the progress of the satellite along its orbit, measured from
        the last ANX.
        '''
        num_frames_per_orbit = round(ORBITAL_PERIOD / self._frame_grid_spacing)
        return ((frame_nr - 1) % num_frames_per_orbit) / num_frames_per_orbit * 360.0


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

    def get_params(self) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        gen, hdr, acq = super().get_params()
        return gen, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def _generate_product(self):
        name_gen = self._create_name_generator(self._hdr)
        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)
        self._logger.info('Create {}'.format(dir_name))

        annot_schema = GeneratedFile(['schema'], 'Annotation', 'xsd')
        orb_schema = GeneratedFile(['schema'], 'Orbit', 'xsd')
        att_schema = GeneratedFile(['schema'], 'Attitude', 'xsd')

        files = [
            GeneratedFile(['annotation'], 'annot', 'xml', annot_schema),
            GeneratedFile(['annotation', 'calibration'], 'cal', 'xml', annot_schema),
            GeneratedFile(['annotation', 'navigation'], 'orb', 'xml', orb_schema),
            GeneratedFile(['annotation', 'navigation'], 'att', 'xml', att_schema),

            GeneratedFile(['annotation', 'calibration'], 'ant', 'dat'),
            GeneratedFile(['annotation', 'calibration'], 'noise', 'dat'),
            GeneratedFile(['annotation', 'geometry'], 'geoloc', 'tiff'),

            GeneratedFile(['preview'], 'map', 'kml'),
            GeneratedFile(['preview'], 'ql', 'png'),

            GeneratedFile(['measurement', 'rfi'], 'rfi', 'tbd'),
            GeneratedFile(['measurement', 'ionosphere'], 'iono', 'tiff')
        ]
        if self._hdr.product_type in product_types.L1S_PRODUCTS:
            files += [
                GeneratedFile(['measurement'], 'i_hh', 'tiff'),
                GeneratedFile(['measurement'], 'i_hv', 'tiff'),
                GeneratedFile(['measurement'], 'i_vh', 'tiff'),
                GeneratedFile(['measurement'], 'i_vv', 'tiff')
            ]

        base_path = os.path.join(self._output_path, dir_name)
        os.makedirs(base_path, exist_ok=True)

        # Create product files
        nr_binfiles = sum(1 for file in files if file.extension != 'xml')
        for file in files:
            self._add_file_to_product(
                file_path=file.get_full_path(name_gen, base_path),
                size_mb=0 if file.extension == 'xml' else self._size_mb // nr_binfiles,
                representation_path=file.representation.get_full_path(name_gen, base_path) if file.representation else None
            )

        # Create MPH
        file_name = os.path.join(base_path, name_gen.generate_mph_file_name())
        self._hdr.write(file_name)

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
                # Skip non-directory products. These have already been parsed in the superclass.
                if not os.path.isdir(file):
                    continue
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

        # TODO: Make Product class to hold header and file list to uncouple hard link between generator and MPH.
        for hdr in self._hdrs:
            # Sanity check
            if hdr.begin_position is None or hdr.end_position is None:
                raise ScenarioError('Begin/end position must be set')
            self._hdr = hdr
            self._generate_level1_stacked_product()

    def _generate_level1_stacked_product(self):

        # If not read from an input product, use begin/end position as starting point
        if self._hdr.validity_start is None:
            self._hdr.validity_start = self._hdr.begin_position
        if self._hdr.validity_stop is None:
            self._hdr.validity_stop = self._hdr.end_position

        self._hdr.product_type = self._resolve_wildcard_product_type()
        self._hdr.processing_date = self._creation_date

        # Setup MPH
        name_gen = self._create_name_generator(self._hdr)
        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)
        self._logger.info('Create {}'.format(dir_name))

        annot_schema = GeneratedFile(['schema'], 'Annotation', 'xsd')
        orb_schema = GeneratedFile(['schema'], 'Orbit', 'xsd')
        att_schema = GeneratedFile(['schema'], 'Attitude', 'xsd')

        files = [
            GeneratedFile(['master_annotation'], 'annot', 'xml', annot_schema),
            GeneratedFile(['master_annotation', 'navigation'], 'orb', 'xml', orb_schema),
            GeneratedFile(['master_annotation', 'navigation'], 'att', 'xml', att_schema),
            GeneratedFile(['master_annotation', 'geometry'], 'geoloc', 'tiff'),

            GeneratedFile(['annotation'], 'annot', 'xml', annot_schema),
            GeneratedFile(['annotation', 'calibration'], 'cal', 'xml', annot_schema),
            GeneratedFile(['annotation', 'calibration'], 'noise', 'dat'),
            GeneratedFile(['annotation', 'navigation'], 'orb', 'xml', orb_schema),
            GeneratedFile(['annotation', 'navigation'], 'att', 'xml', att_schema),

            GeneratedFile(['coregistration'], 'shift', 'tiff'),

            GeneratedFile(['InSAR'], 'delta_iono', 'tiff'),
            GeneratedFile(['InSAR'], 'rfi_impact', 'tiff'),
            GeneratedFile(['InSAR'], 'ground_cal', 'tiff'),

            GeneratedFile(['preview'], 'map', 'kml'),
            GeneratedFile(['preview'], 'ql', 'png'),
        ]
        if self._hdr.product_type in product_types.L1S_PRODUCTS:
            files += [
                GeneratedFile(['measurement'], 'i_hh', 'tiff'),
                GeneratedFile(['measurement'], 'i_hv', 'tiff'),
                GeneratedFile(['measurement'], 'i_vh', 'tiff'),
                GeneratedFile(['measurement'], 'i_vv', 'tiff')
            ]

        base_path = os.path.join(self._output_path, dir_name)
        os.makedirs(base_path, exist_ok=True)

        # Create product files
        nr_binfiles = sum(1 for file in files if file.extension != 'xml')
        for file in files:
            self._add_file_to_product(
                file_path=file.get_full_path(name_gen, base_path),
                size_mb=0 if file.extension == 'xml' else self._size_mb // nr_binfiles,
                representation_path=file.representation.get_full_path(name_gen, base_path) if file.representation else None
            )

        # Create MPH
        file_name = os.path.join(base_path, name_gen.generate_mph_file_name())
        self._hdr.write(file_name)

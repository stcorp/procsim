'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 1 product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0044
'''
import datetime
import os
import xml.dom.minidom as md
from enum import Enum
from typing import Iterable, List, Optional, Tuple
from xml.etree import ElementTree as et

import re
from procsim.core.exceptions import ScenarioError
from procsim.core.job_order import JobOrderInput

from . import constants, main_product_header, product_generator, product_name, product_types
from .product_generator import GeneratedFile

_L1_SCS_PRODUCTS = ['S1_SCS__1S', 'S2_SCS__1S', 'S3_SCS__1S']


FILENAME_DATETIME_FORMAT = '%Y%m%dT%H%M%S'
FIELD_DATETIME_FORMAT = 'UTC=%Y-%m-%dT%H:%M:%S'
FIELD_DATETIME_FORMAT_MICROSECONDS = 'UTC=%Y-%m-%dT%H:%M:%S.%f'


L0S_PATTERN = re.compile(r'^S[0-9]_RAW__0S$')
L0M_PATTERN = re.compile(r'^S[0-9]_RAW__0M$')
AUX_ORB_TYPE = 'AUX_ORB___'


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
    '''This class is responsible for storing basic information about a frame's range and status.'''
    def __init__(self, id: int,
                 sensing_start: datetime.datetime, sensing_stop: datetime.datetime,
                 status: str = ''):
        self.id = id
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

    The acquisition period (phenomenon begin/end times) of the metadata_source
    (i.e. a L0 product) is framed. The frame grid is aligned to ANX.
    An array "anx" with one or more ANX times can be specified in the scenario,
    or a slice number can be supplied in the slice_frame_nr parameter.
    For example:

      "anx": [
        "2021-02-01T00:25:33.745Z",
        "2021-02-01T02:03:43.725Z"
      ],
    '''
    PRODUCTS = ['CPF_L1VFRA']

    _GENERATOR_PARAMS: List[tuple] = [
        ('file_class', '_file_class', 'str'),
        ('enable_framing', '_enable_framing', 'bool'),
        ('source_L0S', '_source_L0S', 'str'),
        ('source_L0M', '_source_L0M', 'str'),
        ('source_AUX_ORB', '_source_AUX_ORB', 'str'),
        ('frame_grid_spacing', '_frame_grid_spacing', 'float'),
        ('frame_overlap', '_frame_overlap', 'float'),
        ('frame_lower_bound', '_frame_lower_bound', 'float'),
        ('slice_overlap_start', '_slice_overlap_start', 'float'),
        ('slice_overlap_end', '_slice_overlap_end', 'float'),
    ]

    _ACQ_PARAMS = [
        ('slice_frame_nr', 'slice_frame_nr', 'int')
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

        self._source_L0S = None
        self._source_L0M = None
        self._source_AUX_ORB = None

    def get_params(self) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        gen, hdr, acq = super().get_params()
        return gen + self._GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:
        if not super().parse_inputs(input_products):
            return False

        prod_name = product_name.ProductName(self._compact_creation_date_epoch)

        # Find the L0S, L0M and AUX_ORB products in the input list.
        for input in input_products:
            for file in input.file_names:
                # Get and check the file type.
                prod_name.parse_path(file)
                if prod_name.file_type is None:
                    continue

                # Strip any path and extension off the filename.
                file_base = os.path.splitext(os.path.basename(file))[0]

                if L0S_PATTERN.match(prod_name.file_type) and self._source_L0S is None:
                    self._source_L0S = file_base
                elif L0M_PATTERN.match(prod_name.file_type) and self._source_L0M is None:
                    self._source_L0M = file_base
                elif prod_name.file_type == AUX_ORB_TYPE and self._source_AUX_ORB is None:
                    self._source_AUX_ORB = file_base

        return True

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
            self._hdr.is_partial = False
            self._hdr.is_merged = False
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

        # Sanity checks
        if slice_start is None or slice_end is None or acq_start is None or acq_end is None:
            raise ScenarioError('Start/stop times must be known here.')

        slice_start, slice_end = self._align_slice_times(slice_start, slice_end)
        first_frame_nr = self._get_first_frame_nr(slice_nr, slice_start)

        frames = self._generate_frames(slice_start, acq_start, acq_end, first_frame_nr)

        # Generate the virtual frame products.
        for frame in frames:
            # These are the only relevant fields for the virtual frame file.
            self._hdr.acquisitions[0].slice_frame_nr = frame.id
            self._hdr.set_phenomenon_times(frame.sensing_start, frame.sensing_stop)
            self._hdr.set_validity_times(frame.sensing_start, frame.sensing_stop)  # Virtual frames only contain sensing time.
            self._frame_status = frame.status

            self._generate_product()

    def _align_slice_times(self, start: datetime.datetime, stop: datetime.datetime) -> Tuple[datetime.datetime, datetime.datetime]:
        '''
        Given an alleged start and stop time of a slice, check whether they're
        aligned. If not, attempt to align or recalculate them.
        This method returns the start and stop times of the slice, not including
        begin/end overlaps.
        '''
        sigma = datetime.timedelta(seconds=0.001)  # Be a little lenient in checking slice bounds.
        # Check if already aligned.
        delta = (stop - start) - constants.SLICE_GRID_SPACING
        if delta > -sigma and delta < sigma:
            return (start, stop)

        # Check if aligned when overlaps subtracted.
        delta = ((stop - self._slice_overlap_end) - (start + self._slice_overlap_start)) - constants.SLICE_GRID_SPACING
        if delta > -sigma and delta < sigma:
            return (start + self._slice_overlap_start, stop - self._slice_overlap_end)

        # Could not align based on overlaps. Try to align based on ANX times.
        slice_bounds = self._get_slice_frame_interval(start + (stop - start) / 2, constants.SLICE_GRID_SPACING)
        if slice_bounds is None:
            raise ScenarioError(f'Could not determine exact slice bounds from start {start} and stop {stop}.')
        return slice_bounds

    def _get_first_frame_nr(self, slice_nr: Optional[int], start_time: datetime.datetime) -> int:
        '''
        If a slice number is provided, use that to determine the first frame
        number in the slice. Else determine frame number from ANX times.
        '''
        if slice_nr is not None:
            first_frame_nr = (slice_nr - 1) * constants.NUM_FRAMES_PER_SLICE + 1
        else:
            slice_bounds = self._get_slice_frame_interval(start_time, constants.SLICE_GRID_SPACING)
            first_frame_nr = self._get_slice_frame_nr(slice_bounds[0], self._frame_grid_spacing) if slice_bounds is not None else None
            if first_frame_nr is None:
                raise ScenarioError(f'Cannot determine frame number from slice number {slice_nr} or start time {start_time} '
                                    + f'given ANX list {self._anx_list}.')

        return first_frame_nr

    def _generate_frames(self, slice_start: datetime.datetime,
                         acq_start: datetime.datetime, acq_end: datetime.datetime,
                         first_frame_nr: int) -> List[Frame]:
        '''
        Generate a list of Frame objects between start and end times. The first
        frame number is expected to be relative to the slice start.
        '''
        # If the acquisition start matches the slice start - overlap, or the acquisition end matches the slice end + overlap, don't generate frames
        # into the slice overlap beyond the regular frame overlap.
        if self._datetimes_match(acq_start, slice_start - constants.SLICE_OVERLAP_START, upto_n_decimals=3):
            frame_range_start = slice_start
        else:
            frame_range_start = acq_start
        if self._datetimes_match(acq_end, slice_start + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, upto_n_decimals=3):
            frame_range_end = slice_start + constants.SLICE_GRID_SPACING + constants.FRAME_OVERLAP
        else:
            frame_range_end = acq_end

        # Create list of frames that covers the entire acquisition range.
        frames: List[Frame] = []
        frame_start = slice_start + (frame_range_start - slice_start) // self._frame_grid_spacing * self._frame_grid_spacing
        while frame_start < frame_range_end:
            id = first_frame_nr + (frame_start - slice_start) // self._frame_grid_spacing
            frames.append(Frame(id=id,
                                sensing_start=frame_start,
                                sensing_stop=frame_start + self._frame_grid_spacing + constants.FRAME_OVERLAP,
                                status=FrameStatus.NOMINAL))
            frame_start += self._frame_grid_spacing

        # Check first and last frames for partiality.
        if frames and frames[0].sensing_start < frame_range_start:
            frames[0].status = FrameStatus.PARTIAL
            frames[0].sensing_start = frame_range_start
        if frames and frames[-1].sensing_stop > frame_range_end:
            frames[-1].status = FrameStatus.PARTIAL
            frames[-1].sensing_stop = frame_range_end

        # Remove edge frames that are completely covered by their neighbours.
        while len(frames) > 1 and frames[0].sensing_start >= frames[1].sensing_start:
            frames.pop(0)
        while len(frames) > 1 and frames[-1].sensing_stop <= frames[-2].sensing_stop:
            frames.pop()

        # If the first or last frame are too short, merge them with their neighbours.
        if len(frames) > 1 and frames[0].sensing_stop - frames[0].sensing_start < self._frame_lower_bound:
            if frames[1].sensing_start > frames[0].sensing_start:
                frames[1].status = FrameStatus.MERGED
                frames[1].sensing_start = frames[0].sensing_start
            frames.pop(0)
        if len(frames) > 1 and frames[-1].sensing_stop - frames[-1].sensing_start < self._frame_lower_bound:
            if frames[-2].sensing_stop < frames[-1].sensing_stop:
                frames[-2].status = FrameStatus.MERGED
                frames[-2].sensing_stop = frames[-1].sensing_stop
            frames.pop()

        return frames

    def _datetimes_match(self, a: datetime.datetime, b: datetime.datetime, upto_n_decimals: int = 6) -> bool:
        '''
        Check whether datetimes match to a given number of decimals.
        '''
        return int((a - b).total_seconds() * 10**upto_n_decimals) == 0

    def _generate_product(self) -> None:
        '''
        Construct and write an output file given the variables set in this class.
        '''
        # Create a name generator, give it the right values and generate the product name.
        name_gen = self._create_name_generator(self._hdr)
        if self._creation_date is None:
            self._creation_date = datetime.datetime.now(tz=datetime.timezone.utc)
        name_gen.set_creation_date(self._creation_date)
        name_gen.file_class = self._file_class
        name_gen.baseline_identifier = self._hdr.product_baseline
        file_name = name_gen.generate_path_name()
        os.makedirs(self._output_path, exist_ok=True)
        full_file_name = os.path.join(self._output_path, file_name)

        # Construct the contents of the XML file.
        xml_string = self._generate_xml(file_name)

        # Write to file.
        self._logger.info(f'Create {file_name}')
        with open(full_file_name, 'w') as file:
            file.write(xml_string)

    def _generate_xml(self, file_name: str) -> str:
        # Ensure the presence of vital variables.
        if self._hdr.validity_start is None or self._hdr.validity_stop is None:
            raise ScenarioError('Validity start/stop times must be known here.')
        if self._hdr.acquisitions[0].slice_frame_nr is None:
            raise ScenarioError('Frame number must be known here.')
        if self._source_L0S is None or self._source_L0M is None or self._source_AUX_ORB is None:
            raise ScenarioError('Input products must be known here.')

        root = et.Element('Earth_Explorer_File')
        earth_explorer_header_node = et.SubElement(root, 'Earth_Explorer_Header')
        fixed_header_node = et.SubElement(earth_explorer_header_node, 'Fixed_Header')
        et.SubElement(fixed_header_node, 'File_Name').text = file_name[:-4]
        et.SubElement(fixed_header_node, 'File_Description').text = 'L1 Virtual Frame'
        et.SubElement(fixed_header_node, 'Notes').text = ''
        et.SubElement(fixed_header_node, 'Mission').text = 'BIOMASS'
        et.SubElement(fixed_header_node, 'File_Class').text = self._file_class
        et.SubElement(fixed_header_node, 'File_Type').text = self._output_type
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

        data_block_node = et.SubElement(root, 'Data_Block', {'type': 'xml'})
        et.SubElement(data_block_node, 'source_L0S').text = self._source_L0S
        et.SubElement(data_block_node, 'source_L0M').text = self._source_L0M
        et.SubElement(data_block_node, 'source_AUX_ORB').text = self._source_AUX_ORB
        et.SubElement(data_block_node, 'frame_id').text = str(self._hdr.acquisitions[0].slice_frame_nr)
        et.SubElement(data_block_node, 'frame_start_time').text = self._hdr.validity_start.strftime(FIELD_DATETIME_FORMAT_MICROSECONDS)
        et.SubElement(data_block_node, 'frame_stop_time').text = self._hdr.validity_stop.strftime(FIELD_DATETIME_FORMAT_MICROSECONDS)
        et.SubElement(data_block_node, 'frame_status').text = self._frame_status
        et.SubElement(data_block_node, 'ops_angle_start', {'unit': 'deg'}).text =\
            str(self._ops_angle_from_frame_nr(self._hdr.acquisitions[0].slice_frame_nr))
        et.SubElement(data_block_node, 'ops_angle_stop', {'unit': 'deg'}).text =\
            str(self._ops_angle_from_frame_nr(self._hdr.acquisitions[0].slice_frame_nr + 1))

        # Insert some indentation.
        dom = md.parseString(et.tostring(root, encoding='unicode'))
        xml_string = dom.toprettyxml(indent='    ')
        return xml_string

    def _ops_angle_from_frame_nr(self, frame_nr: int) -> float:
        '''
        Determine the ops_angle for a given frame number. This is the angle that
        describes the progress of the satellite along its orbit, measured from
        the last ANX.
        '''
        num_frames_per_orbit = round(constants.ORBITAL_PERIOD / self._frame_grid_spacing)
        return ((frame_nr - 1) % num_frames_per_orbit) / num_frames_per_orbit * 360.0


class Level1Stripmap(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating dummy Biomass Level-1a Single-look Complex Slant (SCS) and
    the Level-1b Detected Ground Multi-look (DGM) products.

    Input are a single CPF_L1VFRA, Sx_RAW__0S, Sx_RAW__0M, AUX_ORB___,
    AUX_ATT___, ... product. Output is a single frame, the length of which is
    dictated by the CPF_L1VFRA input.

    The generator adjusts the following metadata:
    - phenomenonTime, acquisition begin/end times.
    - validTime, theoretical frame begin/end times (including overlap).
    - wrsLatitudeGrid, aka the slice_frame_nr.
    '''
    PRODUCTS = ['S1_SCS__1S', 'S2_SCS__1S', 'S3_SCS__1S', 'Sx_SCS__1S',
                'S1_SCS__1M', 'S2_SCS__1M', 'S3_SCS__1M', 'Sx_SCS__1M',
                'S1_DGM__1S', 'S2_DGM__1S', 'S3_DGM__1S', 'Sx_DGM__1S',
                'RO_SCS__1S']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._frame_status = None

    def get_params(self) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        gen, hdr, acq = super().get_params()
        return gen, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:
        if not super().parse_inputs(input_products):
            return False

        for input in input_products:
            for file in input.file_names:
                if input.file_type in product_types.VFRA_PRODUCT_TYPES:
                    self._parse_virtual_frame_file(file)

        return True

    def _parse_virtual_frame_file(self, file_name: str) -> None:
        '''Get frame information from virtual frame file.'''
        root = et.parse(file_name).getroot()

        # Find all OSV elements containing frame ID, start/stop time and status. No XML namespaces are expected.
        frame_id_node = root.find('Data_Block/frame_id')
        if frame_id_node is not None and frame_id_node.text is not None:
            self._hdr.acquisitions[0].slice_frame_nr = int(frame_id_node.text)

        frame_start_time_node = root.find('Data_Block/frame_start_time')
        if frame_start_time_node is not None and frame_start_time_node.text is not None:
            # Trim 'UTC=' off the start of the timestamp and convert to datetime.
            self._hdr.begin_position = self._time_from_iso(frame_start_time_node.text[4:])

        frame_stop_time_node = root.find('Data_Block/frame_stop_time')
        if frame_stop_time_node is not None and frame_stop_time_node.text is not None:
            # Trim 'UTC=' off the start of the timestamp and convert to datetime.
            self._hdr.end_position = self._time_from_iso(frame_stop_time_node.text[4:])

        frame_status_node = root.find('Data_Block/frame_status')
        if frame_status_node is not None and frame_status_node.text is not None:
            self._frame_status = frame_status_node.text

        if not self._hdr.acquisitions[0].slice_frame_nr or not self._hdr.begin_position or not self._hdr.end_position or not self._frame_status:
            self._logger.warning(f'Could not parse frame information from {file_name}. Read the following values:\n'
                                 + f'  frame number: {self._hdr.acquisitions[0].slice_frame_nr},\n'
                                 + f'  begin position: {self._hdr.begin_position},\n'
                                 + f'  end position: {self._hdr.end_position},\n'
                                 + f'  frame status: {self._frame_status}')

        # Set header variables based on the frame status.
        self._hdr.is_partial = self._frame_status == FrameStatus.PARTIAL
        self._hdr.is_merged = self._frame_status == FrameStatus.MERGED
        # Setting the frame status to incomplete (based on contingency) is currently not supported.
        self._hdr.is_incomplete = False

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

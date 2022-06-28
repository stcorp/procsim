'''
Copyright (C) 2022 S[&]T, The Netherlands.
'''
import datetime
import itertools
import os
import shutil
import tempfile
import unittest
from xml.etree import ElementTree as et

from procsim.biomass import constants
from procsim.biomass.level1_product_generator import Level1PreProcessor, Level1Stripmap
from procsim.biomass.product_name import _REGEX_VFRA_FILE_NAME, ProductName
from procsim.core.exceptions import ScenarioError
from procsim.core.job_order import JobOrderInput

TEST_DIR = tempfile.TemporaryDirectory()


class _Logger:
    def __init__(self):
        self.count = 0

    def debug(self, *args, **kwargs):
        # print(*args, **kwargs)
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        print(*args, **kwargs)

    def error(self, *args, **kwargs):
        print(*args, **kwargs)


DATETIME_INPUT_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


ANX1 = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
ANX2 = ANX1 + constants.ORBITAL_PERIOD


STANDARD_CONFIG = {
    'output_path': TEST_DIR.name,
    'baseline': 0,
    'class': 'TEST',
    'type': 'CPF_L1VFRA',
    'processor_name': 'unittest',
    'processor_version': '01.01',
    'zip_output': False,
    'slice_overlap_start': constants.SLICE_OVERLAP_START.total_seconds(),
    'slice_overlap_end': constants.SLICE_OVERLAP_END.total_seconds(),
    'slice_minimum_duration': constants.SLICE_MINIMUM_DURATION.total_seconds(),
    'enable_framing': True,
    'frame_grid_spacing': constants.FRAME_GRID_SPACING.total_seconds(),
    'frame_overlap': constants.FRAME_OVERLAP.total_seconds(),
    'frame_lower_bound': constants.FRAME_MINIMUM_DURATION.total_seconds(),
    'begin_position': (ANX1 - constants.SLICE_OVERLAP_START).strftime(DATETIME_INPUT_FORMAT),
    'end_position': (ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END).strftime(DATETIME_INPUT_FORMAT),
    'slice_frame_nr': 1,
    'data_take_id': 1,
}

# From the GitHub repo, issue 35.
ANX_CONFIG = {
    'output_path': TEST_DIR.name,
    'baseline': 0,
    'name': 'Framer',
    'type': 'CPF_L1VFRA',
    'file_name': 'framer',
    'processor_name': 'Framer',
    'processor_version': '01.00',
    'task_name': 'Framer',
    'task_version': '01.00',
    'log_level': 'debug',
    'begin_position': (ANX1 - constants.SLICE_OVERLAP_START).strftime(DATETIME_INPUT_FORMAT),
    'end_position': (ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END).strftime(DATETIME_INPUT_FORMAT),
    'anx': [
        '2017-02-25T05:00:18.883013Z',
        '2017-02-25T06:38:29.864514Z',
        '2017-02-25T08:16:40.846015Z',
        '2017-02-25T09:54:51.827516Z',
        '2017-02-25T11:33:02.809016Z',
        '2017-02-25T13:11:13.790517Z'
    ],
    'data_take_id': 1,
}


VFRA_DATA = '''<?xml version="1.0" ?>
<Earth_Explorer_File>
    <Earth_Explorer_Header>
        <Fixed_Header>
            <File_Name>BIO_TEST_CPF_L1VFRA_20220421T143831_20220421T143852_01_BN3ZGI</File_Name>
            <File_Description>L1 Virtual Frame</File_Description>
            <Notes/>
            <Mission>BIOMASS</Mission>
            <File_Class>OPER</File_Class>
            <File_Type>CPF_L1VFRA</File_Type>
            <Validity_Period>
                <Validity_Start>UTC=2022-04-21T14:38:31</Validity_Start>
                <Validity_Stop>UTC=2022-04-21T14:38:52</Validity_Stop>
            </Validity_Period>
            <File_Version>01</File_Version>
            <Source>
                <System>PDGS</System>
                <Creator>L1_F</Creator>
                <Creator_Version>1.0</Creator_Version>
                <Creation_Date>UTC=2022-04-22T12:17:06</Creation_Date>
            </Source>
        </Fixed_Header>
        <Variable_Header/>
    </Earth_Explorer_Header>
    <Data_Block type="xml">
        <source_L0S>L0S_Product_Name</source_L0S>
        <source_L0M>L0M_Product_Name</source_L0M>
        <source_AUX_ORB>AUX_ORB_Product_Name</source_AUX_ORB>
        <frame_id>155</frame_id>
        <frame_start_time>UTC=2022-04-21T14:38:31.123456</frame_start_time>
        <frame_stop_time>UTC=2022-04-21T14:38:52.654321</frame_stop_time>
        <frame_status>NOMINAL</frame_status>
        <ops_angle_start unit="deg">178.838710</ops_angle_start>
        <ops_angle_stop unit="deg">180</ops_angle_stop>
    </Data_Block>
</Earth_Explorer_File>'''


class FrameGeneratorTest(unittest.TestCase):
    gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)
    gen.read_scenario_parameters()

    def test_frame_id(self) -> None:
        '''Check whether frame IDs are set correctly.'''
        # Entire slice that should create only nominal frames.
        frames = self.gen._generate_frames(ANX1, ANX1, ANX1 + constants.SLICE_GRID_SPACING + constants.FRAME_OVERLAP, 1)
        for fi, frame in enumerate(frames):
            self.assertEqual(frame.id, fi + 1)

        # Partial frames at start and end.
        frames = self.gen._generate_frames(ANX1, ANX1 + datetime.timedelta(seconds=1),
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.FRAME_OVERLAP - datetime.timedelta(seconds=1), 1)
        for fi, frame in enumerate(frames):
            self.assertEqual(frame.id, fi + 1)

        # Merged frames at start and end.
        frames = self.gen._generate_frames(ANX1, ANX1 - datetime.timedelta(seconds=1),
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.FRAME_OVERLAP + datetime.timedelta(seconds=1), 1)
        for fi, frame in enumerate(frames):
            self.assertEqual(frame.id, fi + 1)

        # Missing frames at start and end.
        frames = self.gen._generate_frames(ANX1, ANX1 + constants.FRAME_GRID_SPACING,
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.FRAME_OVERLAP - constants.FRAME_GRID_SPACING, 1)
        for fi, frame in enumerate(frames, start=1):  # First frame skipped, so start count at 1.
            self.assertEqual(frame.id, fi + 1)

    def test_first_frame_generation(self) -> None:
        '''Test the first frame number getter and frame generation together.'''
        # Acquisition and slice start do not match, first frame number not 1.
        acq_start = ANX1 + constants.SLICE_GRID_SPACING
        acq_end = acq_start + 3 * constants.FRAME_GRID_SPACING
        self.gen._anx_list = [ANX1]
        first_frame_nr = self.gen._get_first_frame_nr(None, acq_start)
        frames = self.gen._generate_frames(ANX1 + constants.SLICE_GRID_SPACING, acq_start, acq_end, first_frame_nr)
        for fi, frame in enumerate(frames):
            self.assertEqual(frame.id, fi + constants.NUM_FRAMES_PER_SLICE + 1)

    def test_entire_slice(self) -> None:
        '''Try to create frames from an entire slice including overlaps on either side.'''
        frames = self.gen._generate_frames(ANX1, ANX1 - constants.SLICE_OVERLAP_START,
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        # The slice start/end overlap is disregarded since the slice is nominal and not expected to be at the start/end of a data take.
        for fi, frame in enumerate(frames):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')

    def test_slice_no_overlap(self) -> None:
        '''Try to create frames from a slice that does not include overlaps on either side.'''
        frames = self.gen._generate_frames(ANX1, ANX1, ANX1 + constants.SLICE_GRID_SPACING, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        for fi, frame in enumerate(frames[:-1]):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')

        # The last frame should have a shorter sensing time since the overlap can't be applied.
        self.assertEqual(frames[-1].id, len(frames))
        self.assertEqual(frames[-1].sensing_start, ANX1 + constants.FRAME_GRID_SPACING * (len(frames) - 1))
        self.assertEqual(frames[-1].sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * len(frames))
        self.assertEqual(frames[-1].status, 'PARTIAL')

    def test_partial_slice(self) -> None:
        '''Create frames from a slice that is missing data in its first frame range.'''
        # Choose offset just on the edge of the frame getting merged.
        test_offset = constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP - constants.FRAME_MINIMUM_DURATION
        frames = self.gen._generate_frames(ANX1, ANX1 + test_offset, ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        # Test all but the first frame.
        for fi, frame in enumerate(frames[1:], start=1):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')
        # The first frame should have a shorter sensing time since the overlap can't be applied.
        first_frame = frames[0]
        self.assertEqual(first_frame.id, 1)
        self.assertEqual(first_frame.sensing_start, ANX1 + test_offset)
        self.assertEqual(first_frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP)
        self.assertEqual(first_frame.status, 'PARTIAL')

    def test_slightly_partial_slice_at_start(self) -> None:
        '''Create frames from a slice that is missing data in its starting overlap.'''
        test_offset = datetime.timedelta(milliseconds=1)
        frames = self.gen._generate_frames(ANX1, ANX1 - constants.SLICE_OVERLAP_START + test_offset,
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        # Test all but the first frame.
        for fi, frame in enumerate(frames[1:], start=1):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')
        # The first frame should have a longer sensing time since it absorbed all of the slice start overlap minus the test offset.
        first_frame = frames[0]
        self.assertEqual(first_frame.id, 1)
        self.assertEqual(first_frame.sensing_start, ANX1 - constants.SLICE_OVERLAP_START + test_offset)
        self.assertEqual(first_frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP)
        self.assertEqual(first_frame.status, 'MERGED')

    def test_slightly_partial_slice_at_end(self) -> None:
        '''Create frames from a slice that is missing data in its end overlap.'''
        test_offset = datetime.timedelta(milliseconds=1)
        frames = self.gen._generate_frames(ANX1, ANX1 - constants.SLICE_OVERLAP_START,
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END - test_offset, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        # Test all but the last frame.
        for fi, frame in enumerate(frames[:-1]):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')
        # The last frame should have a longer sensing time since it absorbed all of the slice end overlap minus the test offset.
        first_frame = frames[-1]
        self.assertEqual(first_frame.id, len(frames))
        self.assertEqual(first_frame.sensing_start, ANX1 + constants.SLICE_GRID_SPACING - constants.FRAME_GRID_SPACING)
        self.assertEqual(first_frame.sensing_stop, ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END - test_offset)
        self.assertEqual(first_frame.status, 'MERGED')

    def test_slightly_merged_slice_at_start(self) -> None:
        '''Create frames from a slice that has additional data at its start.'''
        test_offset = datetime.timedelta(milliseconds=1)
        frames = self.gen._generate_frames(ANX1, ANX1 - constants.SLICE_OVERLAP_START - test_offset,
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        # Test all but the first frame.
        for fi, frame in enumerate(frames[1:], start=1):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')
        # The first frame should have a longer sensing time since it absorbed all of the slice start overlap plus the test offset.
        first_frame = frames[0]
        self.assertEqual(first_frame.id, 1)
        self.assertEqual(first_frame.sensing_start, ANX1 - constants.SLICE_OVERLAP_START - test_offset)
        self.assertEqual(first_frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP)
        self.assertEqual(first_frame.status, 'MERGED')

    def test_slightly_merged_slice_at_end(self) -> None:
        '''Create frames from a slice that has additional data at its end overlap.'''
        test_offset = datetime.timedelta(milliseconds=1)
        frames = self.gen._generate_frames(ANX1, ANX1 - constants.SLICE_OVERLAP_START,
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END + test_offset, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        # Test all but the last frame.
        for fi, frame in enumerate(frames[:-1]):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')
        # The last frame should have a longer sensing time since it absorbed all of the slice end overlap plus the test offset.
        first_frame = frames[-1]
        self.assertEqual(first_frame.id, len(frames))
        self.assertEqual(first_frame.sensing_start, ANX1 + constants.SLICE_GRID_SPACING - constants.FRAME_GRID_SPACING)
        self.assertEqual(first_frame.sensing_stop, ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END + test_offset)
        self.assertEqual(first_frame.status, 'MERGED')

    def test_frame_merge(self) -> None:
        '''Make the first frame so short that it's merged into its neighbour.'''
        # Choose offset just over the edge of the frame getting merged.
        test_offset = constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP - constants.FRAME_MINIMUM_DURATION + datetime.timedelta(microseconds=1)
        frames = self.gen._generate_frames(ANX1, ANX1 + test_offset, ANX1 + constants.SLICE_GRID_SPACING + constants.FRAME_OVERLAP, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE - 1)
        # The first frame should have a longer sensing time since it resulted from a merge.
        self.assertEqual(frames[0].id, 2)
        self.assertEqual(frames[0].sensing_start, ANX1 + test_offset)
        self.assertEqual(frames[0].sensing_stop, ANX1 + 2 * constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP)
        self.assertEqual(frames[0].status, 'MERGED')
        for fi, frame in enumerate(frames):
            if fi == 0:
                continue
            self.assertEqual(frame.id, fi + 2)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1))
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 2) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')

    def test_missing_frame(self) -> None:
        '''Shorten the slice so that the first or last frame goes missing entirely.'''
        # Remove first frame.
        frames = self.gen._generate_frames(ANX1, ANX1 + constants.FRAME_GRID_SPACING,
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.FRAME_OVERLAP, 1)
        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE - 1)
        for fi, frame in enumerate(frames):
            self.assertEqual(frame.id, fi + 2)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1))
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 2) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')

        # Remove last frame. All other frames should be nominal.
        frames = self.gen._generate_frames(ANX1, ANX1,
                                           ANX1 + constants.SLICE_GRID_SPACING - constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP, 1)
        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE - 1)
        for fi, frame in enumerate(frames):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')

    def test_timerange_exceeds_slice_bounds(self) -> None:
        '''
        When the requested time range exceeds a slice boundary, frames should be
        generated within either slice.
        '''
        sensing_start = ANX1
        sensing_stop = ANX1 + constants.SLICE_GRID_SPACING + constants.FRAME_MINIMUM_DURATION + datetime.timedelta(seconds=1)
        frames = self.gen._generate_frames(sensing_start, sensing_start, sensing_stop, 1)
        self.assertEqual(frames[0].sensing_start, ANX1)
        self.assertEqual(frames[-1].sensing_start, ANX1 + constants.SLICE_GRID_SPACING)
        self.assertEqual(frames[-1].sensing_stop, sensing_stop)

    def test_no_frame_minimum(self) -> None:
        '''
        A nominal slice framed with no frame minimum duration should produce the
        same number of frames.
        '''
        old_frame_minimum = self.gen._frame_lower_bound
        self.gen._frame_lower_bound = datetime.timedelta(seconds=0)
        frames = self.gen._generate_frames(ANX1, ANX1 - constants.SLICE_OVERLAP_START,
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)
        self.gen._frame_lower_bound = old_frame_minimum

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        # The slice start/end overlap is disregarded since the slice is nominal and not expected to be at the start/end of a data take.
        for fi, frame in enumerate(frames):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')


class VirtualFrameProductTest(unittest.TestCase):
    '''Test virtual frame production.'''
    def tearDown(self) -> None:
        # Remove all files from the test directory between tests.
        for filename in os.listdir(TEST_DIR.name):
            full_path = os.path.join(TEST_DIR.name, filename)
            if os.path.isfile(full_path):
                os.remove(full_path)
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path)
        return super().tearDown()

    def test_product_name(self) -> None:
        gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)
        gen.read_scenario_parameters()

        start = ANX1
        end = ANX1 + constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP

        # Set frame information manually.
        gen._hdr.acquisitions[0].slice_frame_nr = 1
        gen._hdr.set_phenomenon_times(start, end)
        gen._hdr.set_validity_times(start, end)
        gen._frame_status = 'NOMINAL'
        gen._creation_date = end
        gen._source_L0S = ''
        gen._source_L0M = ''
        gen._source_AUX_ORB = ''
        gen._generate_product()

        # Get the compact create date via a ProductName object.
        name_gen = ProductName()
        name_gen.set_creation_date(gen._creation_date)
        compact_create_date = name_gen._compact_create_date

        expected_filename = f'BIO_TEST_CPF_L1VFRA_{start.strftime("%Y%m%dT%H%M%S")}_{end.strftime("%Y%m%dT%H%M%S")}_00_{compact_create_date}.EOF'
        self.assertEqual(os.listdir(TEST_DIR.name)[0], expected_filename)

    def test_product_contents(self) -> None:
        gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)
        gen.read_scenario_parameters()

        start = ANX1
        end = ANX1 + constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP

        # Set frame information manually.
        gen._hdr.acquisitions[0].slice_frame_nr = 1
        gen._hdr.set_phenomenon_times(start, end)
        gen._hdr.set_validity_times(start, end)
        gen._frame_status = 'NOMINAL'
        gen._creation_date = end
        gen._source_L0S = 'L0S input file'
        gen._source_L0M = 'L0M input file'
        gen._source_AUX_ORB = 'AUX_ORB input file'
        gen._generate_product()

        # Get the compact create date via a ProductName object.
        name_gen = ProductName()
        name_gen.set_creation_date(gen._creation_date)
        compact_create_date = name_gen._compact_create_date
        expected_filename = f'BIO_TEST_CPF_L1VFRA_{start.strftime("%Y%m%dT%H%M%S")}_{end.strftime("%Y%m%dT%H%M%S")}_00_{compact_create_date}'

        with open(os.path.join(TEST_DIR.name, os.listdir(TEST_DIR.name)[0]), 'rb') as f:
            contents = f.read()
        root = et.fromstring(contents)

        checks = [
            ('Earth_Explorer_Header/Fixed_Header/File_Name', expected_filename),
            ('Earth_Explorer_Header/Fixed_Header/File_Description', 'L1 Virtual Frame'),
            ('Earth_Explorer_Header/Fixed_Header/Mission', 'BIOMASS'),
            ('Earth_Explorer_Header/Fixed_Header/File_Class', 'TEST'),
            ('Earth_Explorer_Header/Fixed_Header/File_Type', 'CPF_L1VFRA'),
            ('Earth_Explorer_Header/Fixed_Header/Validity_Period/Validity_Start', start.strftime('UTC=%Y-%m-%dT%H:%M:%S')),
            ('Earth_Explorer_Header/Fixed_Header/Validity_Period/Validity_Stop', end.strftime('UTC=%Y-%m-%dT%H:%M:%S')),
            ('Earth_Explorer_Header/Fixed_Header/File_Version', '01'),
            ('Earth_Explorer_Header/Fixed_Header/Source/System', 'PDGS'),
            ('Earth_Explorer_Header/Fixed_Header/Source/Creator', 'L1_F'),
            ('Earth_Explorer_Header/Fixed_Header/Source/Creator_Version', '1'),
            ('Earth_Explorer_Header/Fixed_Header/Source/Creation_Date', gen._creation_date.strftime('UTC=%Y-%m-%dT%H:%M:%S')),
            ('Data_Block/source_L0S', gen._source_L0S),
            ('Data_Block/source_L0M', gen._source_L0M),
            ('Data_Block/source_AUX_ORB', gen._source_AUX_ORB),
            ('Data_Block/frame_id', 1),
            ('Data_Block/frame_start_time', start.strftime('UTC=%Y-%m-%dT%H:%M:%S.%f')),
            ('Data_Block/frame_stop_time', end.strftime('UTC=%Y-%m-%dT%H:%M:%S.%f')),
            ('Data_Block/frame_status', 'NOMINAL'),
            ('Data_Block/ops_angle_start', 0.0),
            ('Data_Block/ops_angle_stop', 1.1612903225806452),
        ]

        for element, expected_value in checks:
            node = root.find(element)
            self.assertIsNotNone(node)
            self.assertEqual(node.text if node is not None else None, str(expected_value))

    def test_parse_inputs(self) -> None:
        L0S_input = JobOrderInput()
        L0S_input.id = '1'
        L0S_input.alternative_input_id = ''
        L0S_input.file_type = 'S1_RAW__0S'
        L0S_input.file_names = ['$PATH/BIO_S1_RAW__0S_20210201T002432_20210201T002539_T_G___M01_C___T000_F062_00_BJNPAC.zip']  # zip just for testing

        L0M_input = JobOrderInput()
        L0M_input.id = '2'
        L0M_input.alternative_input_id = ''
        L0M_input.file_type = 'S1_RAW__0M'
        L0M_input.file_names = ['$PATH/BIO_S1_RAW__0M_20210201T002432_20210201T002539_T_G___M01_C___T000_F____00_BJNPAD']

        AUX_ORB_input = JobOrderInput()
        AUX_ORB_input.id = '3'
        AUX_ORB_input.alternative_input_id = ''
        AUX_ORB_input.file_type = 'AUX_ORB___'
        AUX_ORB_input.file_names = ['$PATH/BIO_AUX_ORB____20210201T002512_20210201T002715_00_BJNPAC']

        # Any combination of 0, 1, 2, 4 or more inputs should raise an exception.
        for num_inputs in [0, 1, 2, 4, 5]:
            for combination in itertools.combinations([L0S_input, L0M_input, AUX_ORB_input], num_inputs):
                with self.assertRaises(ScenarioError, msg=f'Failed to raise ScenarioError for combination {combination}'):
                    gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)
                    gen.parse_inputs(combination)
                    gen.read_scenario_parameters()
                    gen.generate_output()

        # Should not raise an exception.
        gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)
        gen.parse_inputs([L0S_input, L0M_input, AUX_ORB_input])
        gen.read_scenario_parameters()
        gen.generate_output()

        self.assertEqual(gen._source_L0S, 'BIO_S1_RAW__0S_20210201T002432_20210201T002539_T_G___M01_C___T000_F062_00_BJNPAC')
        self.assertEqual(gen._source_L0M, 'BIO_S1_RAW__0M_20210201T002432_20210201T002539_T_G___M01_C___T000_F____00_BJNPAD')
        self.assertEqual(gen._source_AUX_ORB, 'BIO_AUX_ORB____20210201T002512_20210201T002715_00_BJNPAC')

    def test_generate_from_scenario(self) -> None:
        '''
        Make sure virtual frames can be generated without input files as long as
        the right scenario parameters are set.
        '''
        gen_config = STANDARD_CONFIG.copy()
        gen_config['source_L0S'] = 'Scenario L0S filename'
        gen_config['source_L0M'] = 'Scenario L0M filename'
        gen_config['source_AUX_ORB'] = 'Scenario AUX_ORB filename'
        gen = Level1PreProcessor(_Logger(), None, gen_config, gen_config)

        # Should not throw an exception since input filenames were set in scenario.
        gen.parse_inputs([])
        gen.read_scenario_parameters()
        gen.generate_output()

        # Check whether the output directory contains files.
        self.assertTrue(os.listdir(TEST_DIR.name))

        # Open the first file and check its source file contents.
        checks = [
            ('Data_Block/source_L0S', 'Scenario L0S filename'),
            ('Data_Block/source_L0M', 'Scenario L0M filename'),
            ('Data_Block/source_AUX_ORB', 'Scenario AUX_ORB filename'),
        ]

        root = et.parse(os.path.join(TEST_DIR.name, os.listdir(TEST_DIR.name)[0]))
        for element, expected_value in checks:
            node = root.find(element)
            self.assertIsNotNone(node)
            self.assertEqual(node.text if node is not None else None, str(expected_value))

    def test_generate_from_anx_scenario(self) -> None:
        '''
        Ensure that virtual frames can be generated without a frame number, just
        from ANX information provided in the scenario.
        '''
        gen_config = ANX_CONFIG.copy()
        gen_config['source_L0S'] = 'Scenario L0S filename'
        gen_config['source_L0M'] = 'Scenario L0M filename'
        gen_config['source_AUX_ORB'] = 'Scenario AUX_ORB filename'
        gen = Level1PreProcessor(_Logger(), None, gen_config, gen_config)

        # Should not throw an exception since input filenames were set in scenario.
        gen.parse_inputs([])
        gen.read_scenario_parameters()
        gen.generate_output()

        # Check whether the output directory contains files.
        self.assertTrue(os.listdir(TEST_DIR.name))

        # Open the first file and check its source file contents.
        checks = [
            ('Data_Block/source_L0S', 'Scenario L0S filename'),
            ('Data_Block/source_L0M', 'Scenario L0M filename'),
            ('Data_Block/source_AUX_ORB', 'Scenario AUX_ORB filename'),
        ]

        root = et.parse(os.path.join(TEST_DIR.name, os.listdir(TEST_DIR.name)[0]))
        for element, expected_value in checks:
            node = root.find(element)
            self.assertIsNotNone(node)
            self.assertEqual(node.text if node is not None else None, str(expected_value))

    def test_sensing_times_in_product(self) -> None:
        '''
        Virtual frames only ever make use of the sensing/phenomenon time, and
        never the validity time (via correspondence with Luca). Make sure that
        the correct times appear in the product.
        '''
        gen_config = STANDARD_CONFIG.copy()
        gen_config['source_L0S'] = 'Scenario L0S filename'
        gen_config['source_L0M'] = 'Scenario L0M filename'
        gen_config['source_AUX_ORB'] = 'Scenario AUX_ORB filename'
        gen = Level1PreProcessor(_Logger(), None, gen_config, gen_config)
        gen.parse_inputs([])
        gen.read_scenario_parameters()

        # Manually set sensing time to different times.
        start_sensing_time = ANX1
        end_sensing_time = ANX1 + constants.SLICE_GRID_SPACING
        gen._hdr.validity_start = ANX1 - constants.SLICE_OVERLAP_START
        gen._hdr.validity_stop = ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END
        gen._hdr.begin_position = start_sensing_time
        gen._hdr.end_position = end_sensing_time
        self.assertNotEqual(gen._hdr.validity_start, gen._hdr.begin_position)
        self.assertNotEqual(gen._hdr.validity_stop, gen._hdr.end_position)
        gen.generate_output()

        # The first and last virtual frame products should contain the sensing
        # times in their name, validity time fields and frame time fields.
        num_files = len(os.listdir(TEST_DIR.name))
        self.assertNotEqual(num_files, 0)

        sorted_filenames = sorted(os.listdir(TEST_DIR.name))  # String sorting works well to sort by date in this case.
        first_filename = sorted_filenames[0]
        last_filename = sorted_filenames[-1]

        # Verify times in filenames.
        first_match = _REGEX_VFRA_FILE_NAME.match(first_filename)
        last_match = _REGEX_VFRA_FILE_NAME.match(last_filename)
        first_match_dict = first_match.groupdict() if first_match else {}
        last_match_dict = last_match.groupdict() if last_match else {}
        self.assertEqual(first_match_dict.get('vstart'), start_sensing_time.strftime('%Y%m%dT%H%M%S'))
        self.assertEqual(last_match_dict.get('vstop'), end_sensing_time.strftime('%Y%m%dT%H%M%S'))

        # Verify times in validity time fields.
        first_root = et.parse(os.path.join(TEST_DIR.name, first_filename))
        first_vstart_node = first_root.find('Earth_Explorer_Header/Fixed_Header/Validity_Period/Validity_Start')
        self.assertEqual(first_vstart_node.text if first_vstart_node is not None else None, start_sensing_time.strftime('UTC=%Y-%m-%dT%H:%M:%S'))
        last_root = et.parse(os.path.join(TEST_DIR.name, last_filename))
        last_vstop_node = last_root.find('Earth_Explorer_Header/Fixed_Header/Validity_Period/Validity_Stop')
        self.assertEqual(last_vstop_node.text if last_vstop_node is not None else None, end_sensing_time.strftime('UTC=%Y-%m-%dT%H:%M:%S'))

        # Verify times in frame time fields.
        first_frame_start = first_root.find('Data_Block/frame_start_time')
        self.assertEqual(first_frame_start.text if first_frame_start is not None else None, start_sensing_time.strftime('UTC=%Y-%m-%dT%H:%M:%S.%f'))
        last_frame_stop = last_root.find('Data_Block/frame_stop_time')
        self.assertEqual(last_frame_stop.text if last_frame_stop is not None else None, end_sensing_time.strftime('UTC=%Y-%m-%dT%H:%M:%S.%f'))

    def test_align_slice_times(self) -> None:
        '''
        Virtual frames only contain data concerning sensing time, but the frame
        boundaries follow the theoretical slice/frame grid. The theoretical
        bounds of the slice need to be accurate for this reason.
        '''
        gen_config = ANX_CONFIG.copy()
        gen_config['source_L0S'] = 'Scenario L0S filename'
        gen_config['source_L0M'] = 'Scenario L0M filename'
        gen_config['source_AUX_ORB'] = 'Scenario AUX_ORB filename'
        gen = Level1PreProcessor(_Logger(), None, gen_config, gen_config)

        # Pick one ANX time from the used scenario.
        anx = datetime.datetime(2017, 2, 25, 8, 16, 40, 846015, tzinfo=datetime.timezone.utc)

        slice_sensing_start = anx
        slice_sensing_stop = anx + constants.SLICE_GRID_SPACING

        # Slice times that are consistent with the slice grid.
        aligned_bounds = gen._align_slice_times(slice_sensing_start, slice_sensing_stop)
        self.assertEqual(aligned_bounds, (slice_sensing_start, slice_sensing_stop))

        # Slice times consistent with the slice grid including overlap.
        slice_sensing_start_overlap = anx - constants.SLICE_OVERLAP_START
        slice_sensing_stop_overlap = anx + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END
        overlap_bounds = gen._align_slice_times(slice_sensing_start_overlap, slice_sensing_stop_overlap)
        self.assertEqual(overlap_bounds, (slice_sensing_start, slice_sensing_stop))

        # Slice times within a single slice's bounds.
        slice_sensing_start_internal = anx + datetime.timedelta(seconds=1)
        slice_sensing_stop_internal = anx + constants.SLICE_GRID_SPACING - datetime.timedelta(seconds=1)
        internal_bounds = gen._align_slice_times(slice_sensing_start_internal, slice_sensing_stop_internal)
        self.assertEqual(internal_bounds, (slice_sensing_start, slice_sensing_stop))

        # One of sensing times slightly exceeds the slice bounds.
        slice_sensing_start_exceed = anx
        slice_sensing_stop_exceed = anx + constants.SLICE_GRID_SPACING + datetime.timedelta(seconds=1)
        exceed_bounds = gen._align_slice_times(slice_sensing_start_exceed, slice_sensing_stop_exceed)
        self.assertEqual(exceed_bounds, (slice_sensing_start, slice_sensing_stop))


class VirtualFrameParsingTest(unittest.TestCase):
    '''Test parsing of virtual frames.'''
    def test_settings_from_file(self) -> None:
        '''Check whether settings are properly read from the test data.'''
        config = {'type': 'test'}
        gen = Level1Stripmap(logger=_Logger(), job_config=None, scenario_config=config, output_config=config)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(VFRA_DATA.encode('utf-8'))
            virtual_frame_path = f.name

        gen._parse_virtual_frame_file(virtual_frame_path)

        self.assertEqual(gen._hdr.acquisitions[0].slice_frame_nr, 155)
        self.assertEqual(gen._hdr.begin_position, datetime.datetime(2022, 4, 21, 14, 38, 31, 123456, tzinfo=datetime.timezone.utc))
        self.assertEqual(gen._hdr.end_position, datetime.datetime(2022, 4, 21, 14, 38, 52, 654321, tzinfo=datetime.timezone.utc))
        self.assertEqual(gen._frame_status, 'NOMINAL')

    def test_no_frame_info(self) -> None:
        '''Verify that an exception is thrown if framing is attempted without frame info.'''
        config = {
            'output_path': TEST_DIR,
            'type': 'RAWS025_10',
            'processor_name': 'unittest',
            'processor_version': '01.01',
            'baseline': 10,
            'acquisition_date': '2021-01-01T00:00:00.000Z',
            'acquisition_station': 'unittest',
            'num_isp': 387200,
            'num_isp_erroneous': 0,
            'num_isp_corrupt': 0,
            'num_tf': 387200,
            'num_tf_erroneous': 0,
            'num_tf_corrupt': 0,
            'zip_output': False,
            'slice_overlap_start': 5.0,
            'slice_overlap_end': 7.0,
            'slice_minimum_duration': 15.0
        }
        gen = Level1PreProcessor(logger=_Logger(), job_config=None, scenario_config=config, output_config=config)
        gen._enable_framing = True
        with self.assertRaises(ScenarioError):
            gen.generate_output()


if __name__ == '__main__':
    unittest.main()

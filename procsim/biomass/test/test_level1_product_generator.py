'''
Copyright (C) 2022 S[&]T, The Netherlands.
'''
import datetime
import itertools
import os
import tempfile
import unittest
from xml.etree import ElementTree as et

from procsim.biomass import constants
from procsim.biomass.level1_product_generator import Level1PreProcessor
from procsim.biomass.product_name import ProductName
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

    def error(self, *args, **kwargs):
        print(*args, **kwargs)


ANX1 = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
ANX2 = ANX1 + constants.ORBITAL_PERIOD


STANDARD_CONFIG = {
    'output_path': TEST_DIR,
    'class': 'TEST',
    'type': 'CPF_L1VFRA',
    'processor_name': 'unittest',
    'processor_version': '01.01',
    'zip_output': False,
    'slice_overlap_start': constants.SLICE_OVERLAP_START,
    'slice_overlap_end': constants.SLICE_OVERLAP_END,
    'slice_minimum_duration': constants.SLICE_MINIMUM_DURATION,
    'enable_framing': True,
    'frame_grid_spacing': constants.FRAME_GRID_SPACING,
    'frame_overlap': constants.FRAME_OVERLAP,
    'frame_lower_bound': constants.FRAME_MINIMUM_DURATION,
}


class FrameGeneratorTest(unittest.TestCase):
    gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)

    '''Try to create frames from an entire slice including overlaps on either side.'''
    def test_entire_slice(self) -> None:
        frames = self.gen._generate_frames(ANX1, ANX1 - constants.SLICE_OVERLAP_START,
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        for fi, frame in enumerate(frames[:-1]):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.validity_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.validity_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')

    def test_slice_no_overlap(self) -> None:
        '''Try to create frames from a slice that does not include overlaps on either side.'''
        frames = self.gen._generate_frames(ANX1, ANX1, ANX1 + constants.SLICE_GRID_SPACING, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        for fi, frame in enumerate(frames[:-1]):
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.validity_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.validity_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')

        # The last frame should have a shorter sensing time since the overlap can't be applied.
        self.assertEqual(frames[-1].id, len(frames))
        self.assertEqual(frames[-1].validity_start, ANX1 + constants.FRAME_GRID_SPACING * (len(frames) - 1))
        self.assertEqual(frames[-1].validity_stop, ANX1 + constants.FRAME_GRID_SPACING * len(frames) + constants.FRAME_OVERLAP)
        self.assertEqual(frames[-1].sensing_start, ANX1 + constants.FRAME_GRID_SPACING * (len(frames) - 1))
        self.assertEqual(frames[-1].sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * len(frames))
        self.assertEqual(frames[-1].status, 'PARTIAL')

    def test_partial_slice(self) -> None:
        '''Create frames from a slice that is missing data in its first frame range.'''
        # Choose offset just on the edge of the frame getting merged.
        test_offset = constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP - constants.FRAME_MINIMUM_DURATION
        frames = self.gen._generate_frames(ANX1, ANX1 + test_offset, ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE)
        # The first frame should have a shorter sensing time since the overlap can't be applied.
        self.assertEqual(frames[0].id, 1)
        self.assertEqual(frames[0].validity_start, ANX1)
        self.assertEqual(frames[0].validity_stop, ANX1 + constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP)
        self.assertEqual(frames[0].sensing_start, ANX1 + test_offset)
        self.assertEqual(frames[0].sensing_stop, ANX1 + constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP)
        self.assertEqual(frames[0].status, 'PARTIAL')
        for fi, frame in enumerate(frames):
            if fi == 0:
                continue
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.validity_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.validity_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')

    def test_frame_merge(self) -> None:
        '''Make the first frame so short that it's merged into its neighbour.'''
        # Choose offset just over the edge of the frame getting merged.
        test_offset = constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP - constants.FRAME_MINIMUM_DURATION + datetime.timedelta(microseconds=1)
        frames = self.gen._generate_frames(ANX1, ANX1 + test_offset, ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)

        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE - 1)
        # The first frame should have a longer sensing time since it resulted from a merge.
        self.assertEqual(frames[0].id, 2)
        self.assertEqual(frames[0].validity_start, ANX1 + constants.FRAME_GRID_SPACING)
        self.assertEqual(frames[0].validity_stop, ANX1 + 2 * constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP)
        self.assertEqual(frames[0].sensing_start, ANX1 + test_offset)
        self.assertEqual(frames[0].sensing_stop, ANX1 + 2 * constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP)
        self.assertEqual(frames[0].status, 'MERGED')
        for fi, frame in enumerate(frames):
            if fi == 0:
                continue
            self.assertEqual(frame.id, fi + 2)
            self.assertEqual(frame.validity_start, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1))
            self.assertEqual(frame.validity_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 2) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1))
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 2) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')

    def test_missing_frame(self) -> None:
        '''Shorten the slice so that the first or last frame goes missing entirely.'''
        # Remove first frame.
        frames = self.gen._generate_frames(ANX1, ANX1 + constants.FRAME_GRID_SPACING,
                                           ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)
        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE - 1)
        for fi, frame in enumerate(frames):
            if fi == 0:
                continue
            self.assertEqual(frame.id, fi + 2)
            self.assertEqual(frame.validity_start, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1))
            self.assertEqual(frame.validity_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 2) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1))
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 2) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')

        # Remove last frame. All other frames should be nominal.
        frames = self.gen._generate_frames(ANX1, ANX1,
                                           ANX1 + constants.SLICE_GRID_SPACING - constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP, 1)
        for frame in frames:
            print(frame.sensing_stop - frame.sensing_start)
        self.assertEqual(len(frames), constants.NUM_FRAMES_PER_SLICE - 1)
        for fi, frame in enumerate(frames):
            print(fi, frame.status)
            self.assertEqual(frame.id, fi + 1)
            self.assertEqual(frame.validity_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.validity_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.sensing_start, ANX1 + constants.FRAME_GRID_SPACING * fi)
            self.assertEqual(frame.sensing_stop, ANX1 + constants.FRAME_GRID_SPACING * (fi + 1) + constants.FRAME_OVERLAP)
            self.assertEqual(frame.status, 'NOMINAL')


class VirtualFrameProductTest(unittest.TestCase):
    '''Test virtual frame production.'''
    def test_product_name(self) -> None:
        gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)
        gen._output_path = str(TEST_DIR)

        start = ANX1
        end = ANX1 + constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP

        # Set frame information manually.
        gen._hdr.acquisitions[0].slice_frame_nr = 1
        gen._hdr.set_phenomenon_times(start, end)
        gen._hdr.set_validity_times(start, end)
        gen._frame_status = 'NOMINAL'
        gen._creation_date = end
        gen._generate_product()

        # Get the compact create date via a ProductName object.
        name_gen = ProductName()
        name_gen.set_creation_date(gen._creation_date)
        compact_create_date = name_gen._compact_create_date

        expected_filename = f'BIO_TEST_CPF_L1VFRA_{start.strftime("%Y%m%dT%H%M%S")}_{end.strftime("%Y%m%dT%H%M%S")}_00_{compact_create_date}.EOF'
        self.assertEqual(os.listdir(str(TEST_DIR))[0], expected_filename)

    def test_parse_inputs(self) -> None:
        gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)
        gen._output_path = str(TEST_DIR)

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
                with self.assertRaises(ScenarioError):
                    gen.parse_inputs(combination)

        # Should not raise an exception.
        gen.parse_inputs([L0S_input, L0M_input, AUX_ORB_input])

        self.assertEqual(gen._source_L0S, 'BIO_S1_RAW__0S_20210201T002432_20210201T002539_T_G___M01_C___T000_F062_00_BJNPAC')
        self.assertEqual(gen._source_L0M, 'BIO_S1_RAW__0M_20210201T002432_20210201T002539_T_G___M01_C___T000_F____00_BJNPAD')
        self.assertEqual(gen._source_AUX_ORB, 'BIO_AUX_ORB____20210201T002512_20210201T002715_00_BJNPAC')


if __name__ == '__main__':
    unittest.main()

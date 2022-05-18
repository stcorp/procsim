'''
Copyright (C) 2022 S[&]T, The Netherlands.
'''
import datetime
import glob
import os
import shutil
import unittest
from xml.etree import ElementTree as et

from procsim.biomass import main_product_header
from procsim.biomass import constants
from procsim.biomass.level1_product_generator import Level1PreProcessor

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')


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


ANX1 = datetime.datetime(2020, 1, 1, 0, 0, 0)
ANX2 = ANX1 + constants.ORBITAL_PERIOD


STANDARD_CONFIG = {
    'output_path': TEST_DIR,
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


class VirtualFrameGeneratorTest(unittest.TestCase):
    '''Try to create frames from an entire slice including overlaps on either side.'''
    def test_entire_slice(self) -> None:
        gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)
        frames = gen._generate_frames(ANX1,
                                      ANX1 - constants.SLICE_OVERLAP_START, ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END,
                                      1)

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
        gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)

        frames = gen._generate_frames(ANX1, ANX1, ANX1 + constants.SLICE_GRID_SPACING, 1)

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
        gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)

        # Choose offset just on the edge of the frame getting merged.
        test_offset = constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP - constants.FRAME_MINIMUM_DURATION
        frames = gen._generate_frames(ANX1, ANX1 + test_offset, ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)

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
        gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)

        # Choose offset just over the edge of the frame getting merged.
        test_offset = constants.FRAME_GRID_SPACING + constants.FRAME_OVERLAP - constants.FRAME_MINIMUM_DURATION + datetime.timedelta(microseconds=1)
        frames = gen._generate_frames(ANX1, ANX1 + test_offset, ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)

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
        gen = Level1PreProcessor(_Logger(), None, STANDARD_CONFIG, STANDARD_CONFIG)

        # Remove first frame.
        frames = gen._generate_frames(ANX1, ANX1 + constants.FRAME_GRID_SPACING, ANX1 + constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END, 1)
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
        frames = gen._generate_frames(ANX1, ANX1,
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


if __name__ == '__main__':
    unittest.main()

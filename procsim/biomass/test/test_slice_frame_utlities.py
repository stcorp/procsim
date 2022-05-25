'''
Copyright (C) 2022 S[&]T, The Netherlands.
'''
import datetime
import unittest

from procsim.biomass.product_generator import ProductGeneratorBase


class _Logger:
    def __init__(self):
        self.count = 0

    def debug(self, *args, **kwargs):
        # print(*args, **kwargs)
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        print(*args, **kwargs)


class SliceFrameUtilitiesTest(unittest.TestCase):
    gen = ProductGeneratorBase(_Logger(), None, {'type': 'test'}, {'type': 'test'})

    anx1 = datetime.datetime(2020, 1, 1, 0, 0, 0)
    anx_diff = datetime.timedelta(hours=1.5)
    anx2 = anx1 + anx_diff
    gen._anx_list = [anx1, anx2]
    spacing = datetime.timedelta(minutes=5)

    def test_get_anx(self) -> None:
        # Attempt to get an ANX before any known ANX.
        self.assertIsNone(self.gen._get_anx(self.anx1 - datetime.timedelta(seconds=1)))
        self.assertIsNone(self.gen._get_anx(self.anx1 - datetime.timedelta(days=1)))
        self.assertIsNone(self.gen._get_anx(self.anx1 - datetime.timedelta(days=1000)))

        # Get the first ANX across the entire first orbit.
        self.assertEqual(self.gen._get_anx(self.anx1), self.anx1)
        self.assertEqual(self.gen._get_anx(self.anx1 + datetime.timedelta(seconds=1)), self.anx1)
        self.assertEqual(self.gen._get_anx(self.anx1 + datetime.timedelta(hours=1)), self.anx1)
        self.assertEqual(self.gen._get_anx(self.anx1 + self.anx_diff - datetime.timedelta(seconds=1)), self.anx1)

        # Get the second ANX.
        self.assertEqual(self.gen._get_anx(self.anx2), self.anx2)
        self.assertEqual(self.gen._get_anx(self.anx2 + datetime.timedelta(days=1)), self.anx2)
        self.assertEqual(self.gen._get_anx(self.anx2 + datetime.timedelta(days=10000)), self.anx2)

    def test_get_slice_frame_nr(self) -> None:
        # Get a slice/frame number before the first ANX.
        self.assertIsNone(self.gen._get_slice_frame_nr(self.anx1 - datetime.timedelta(seconds=1), self.spacing))

        # Get slices/frame numbers within the first orbit.
        self.assertEqual(self.gen._get_slice_frame_nr(self.anx1, self.spacing), 1)
        self.assertEqual(self.gen._get_slice_frame_nr(self.anx1 + self.spacing - datetime.timedelta(seconds=1), self.spacing), 1)
        self.assertEqual(self.gen._get_slice_frame_nr(self.anx1 + self.spacing, self.spacing), 2)
        self.assertEqual(self.gen._get_slice_frame_nr(self.anx1 + self.anx_diff - datetime.timedelta(seconds=1), self.spacing),
                         self.anx_diff // self.spacing)

        # Get slices/frame numbers within and after the second orbit.
        self.assertEqual(self.gen._get_slice_frame_nr(self.anx2, self.spacing), 1)
        self.assertEqual(self.gen._get_slice_frame_nr(self.anx2 + self.spacing * 1000, self.spacing), 1)

    def test_get_slice_frame_interval(self) -> None:
        # Get an interval before the first ANX.
        self.assertIsNone(self.gen._get_slice_frame_interval(self.anx1 - datetime.timedelta(seconds=1), self.spacing))

        # Get intervals within the first orbit.
        self.assertEqual(self.gen._get_slice_frame_interval(self.anx1, self.spacing), (self.anx1, self.anx1 + self.spacing))
        self.assertEqual(self.gen._get_slice_frame_interval(self.anx1 + self.spacing, self.spacing),
                         (self.anx1 + self.spacing, self.anx1 + 2 * self.spacing))
        self.assertEqual(self.gen._get_slice_frame_interval(self.anx1 + self.spacing + datetime.timedelta(seconds=1), self.spacing),
                         (self.anx1 + self.spacing, self.anx1 + 2 * self.spacing))
        self.assertEqual(self.gen._get_slice_frame_interval(self.anx1 + 1.5 * self.spacing, self.spacing),
                         (self.anx1 + self.spacing, self.anx1 + 2 * self.spacing))
        self.assertEqual(self.gen._get_slice_frame_interval(self.anx1 + 2 * self.spacing - datetime.timedelta(seconds=1), self.spacing),
                         (self.anx1 + self.spacing, self.anx1 + 2 * self.spacing))

        # Get intervals within and after the second orbit.
        self.assertEqual(self.gen._get_slice_frame_interval(self.anx2, self.spacing), (self.anx2, self.anx2 + self.spacing))
        self.assertEqual(self.gen._get_slice_frame_interval(self.anx2 + 1000.5 * self.spacing, self.spacing), (self.anx2, self.anx2 + self.spacing))


if __name__ == '__main__':
    unittest.main()

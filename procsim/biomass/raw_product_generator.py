'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw output product generators, according to BIO-ESA-EOPG-EEGS-TN-0073
'''
import bisect
import datetime
import os
import shutil
import zipfile
from typing import List

from procsim.core.exceptions import ScenarioError

from . import constants, product_generator, product_name

_GENERATOR_PARAMS = [
    ('output_path', '_output_path', 'str')
]
_HDR_PARAMS = [
    ('baseline', 'product_baseline', 'int'),
    ('acquisition_date', 'acquisition_date', 'date'),
    ('acquisition_station', 'acquisition_station', 'str'),
    ('num_isp', 'nr_instrument_source_packets', 'int'),
    ('num_isp_erroneous', 'nr_instrument_source_packets_erroneous', 'int'),
    ('num_isp_corrupt', 'nr_instrument_source_packets_corrupt', 'int')
]
_ACQ_PARAMS = []


class RawProductGeneratorBase(product_generator.ProductGeneratorBase):
    '''
    This abstract class is responsible for creating raw products and is used as
    base class for the specific raw product generators.
    '''
    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        val = output_config.get('zip_outputs') or scenario_config.get('zip_outputs')
        self._zip_outputs = True if val is None else val

    def get_params(self):
        return _GENERATOR_PARAMS, _HDR_PARAMS, _ACQ_PARAMS

    def _create_raw_product(self, dir_name, name_gen):
        self._logger.info('Create {}'.format(dir_name))
        full_dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(full_dir_name, exist_ok=True)
        mph_file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        full_mph_file_name = os.path.join(self._output_path, mph_file_name)
        self._hdr.write(full_mph_file_name)
        bin_file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
        full_bin_file_name = os.path.join(self._output_path, bin_file_name)
        self._generate_bin_file(full_bin_file_name, self._size_mb)
        if self._zip_outputs:
            self._zip_directory(full_dir_name, [full_mph_file_name, full_bin_file_name], [mph_file_name, bin_file_name])

    def _zip_directory(self, dir_name: str, filenames: List[str], arcnames: List[str]):
        # Note: Deletes input files afterwards
        self._logger.debug('Archive to .zip')
        with zipfile.ZipFile(dir_name + '.zip', 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            for filename, arcname in zip(filenames, arcnames):
                zipped.write(filename, arcname)
            zipped.close()
            shutil.rmtree(dir_name)


class RAW_xxx_10(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw products generation.
    '''
    PRODUCTS = ['RAW_022_10', 'RAW_023_10', 'RAW_024_10', 'RAW_025_10',
                'RAW_026_10', 'RAW_027_10', 'RAW_028_10', 'RAW_035_10',
                'RAW_036_10']

    HDR_PARAMS = [
        ('begin_position', 'begin_position', 'date'),
        ('end_position', 'end_position', 'date'),
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen, hdr + self.HDR_PARAMS, acq

    def generate_output(self):
        # Base class is doing part of the setup
        super(RAW_xxx_10, self).generate_output()

        create_date = datetime.datetime.utcnow()
        start = self._hdr.begin_position
        stop = self._hdr.end_position

        # Construct product name and set metadata fields
        name_gen = product_name.ProductName()
        name_gen.file_type = self._output_type
        name_gen.start_time = start
        name_gen.stop_time = stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(create_date)
        name_gen.downlink_time = self._hdr.acquisition_date

        dir_name = name_gen.generate_path_name()
        self._hdr.product_type = self._output_type
        self._hdr.set_product_filename(dir_name)
        self._hdr.set_validity_times(start, stop)

        self._create_raw_product(dir_name, name_gen)


class RAWSxxx_10(RawProductGeneratorBase):
    '''
    This class implements the RawProductGeneratorBase and is responsible for
    the raw slice-based products generation.

    The acquisition period (phenomenon begin/end times) of the metadata_source
    (i.e. a RAW_xxx_10 product) is sliced. The slice grid is aligned to ANX.
    An array "anx" with one or more ANX times must be specified in the scenario.
    For example:

      "anx": [
        "2021-02-01T00:25:33.745Z",
        "2021-02-01T02:03:43.725Z"
      ],

    Edge cases:
    - ANX falls within an acquisition. Slice 62 ends at the grid defined by
        the 'old' ANX, slice 1 starts at the 'new' ANX.
    - Acquisition starts ts=0..5 seconds before the end of slice n. Create
        slice n+1 with lead time ts.
    - Acquisition ends te=0..7 seconds after the end of slice n. Create
        slice n with trail time te.

    The generator adjusts the following metadata:
    - phenomenonTime, acquisition begin/end times.
    - validTime, theoretical slice begin/end times (including overlap).
    - wrsLatitudeGrid, aka the slice_frame_nr.
    '''

    PRODUCTS = ['RAWS022_10', 'RAWS023_10', 'RAWS024_10', 'RAWS025_10',
                'RAWS026_10', 'RAWS027_10', 'RAWS028_10', 'RAWS035_10',
                'RAWS036_10']

    GENERATOR_PARAMS: List[tuple] = [
        ('enable_slicing', '_enable_slicing', 'bool')
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        # Get anx list from config. Can be located at either scenario or product level
        anx_list = output_config.get('anx') or scenario_config.get('anx')
        if anx_list is None:
            raise ScenarioError('ANX must be configured for RAWSxxx_10 product')
        self._anx_list = [self._time_from_iso(anx) for anx in anx_list]
        self._anx_list.sort()
        self._enable_slicing = True

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + self.GENERATOR_PARAMS, hdr, acq

    def generate_output(self):
        super(RAWSxxx_10, self).generate_output()

        if self._enable_slicing:
            self._generate_sliced_output()
        else:
            self._create_product(self._hdr.begin_position, self._hdr.end_position)

    def _create_product(self, acq_start, acq_stop):
        # Construct product name and set metadata fields
        create_date = datetime.datetime.utcnow()
        name_gen = product_name.ProductName()
        name_gen.file_type = self._output_type
        name_gen.start_time = acq_start
        name_gen.stop_time = acq_stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(create_date)
        name_gen.downlink_time = self._hdr.acquisition_date

        dir_name = name_gen.generate_path_name()
        self._hdr.product_type = self._output_type
        self._hdr.set_product_filename(dir_name)
        self._hdr.set_phenomenon_times(acq_start, acq_stop)

        self._create_raw_product(dir_name, name_gen)

    def _get_anx(self, t):
        # Returns the latest ANX before the given time
        idx = bisect.bisect(self._anx_list, t) - 1  # anx_list[idx-1] <= tstart
        return self._anx_list[min(max(idx, 0), len(self._anx_list) - 1)]

    def _generate_sliced_output(self):
        segment_start = self._hdr.begin_position
        segment_end = self._hdr.end_position
        if segment_start is None or segment_end is None:
            self._logger.error('Phenomenon begin/end times must be known')
            return

        start = segment_start
        while start < segment_end:
            # Find slice
            anx = self._get_anx(start)
            n = (start - anx) // constants.SLICE_GRID_SPACING

            # Test if the first slice starts within the 'start overlap time' of
            # the next slice. In that case, use that slice instead.
            s = start + constants.SLICE_OVERLAP_START
            anx2 = self._get_anx(s)
            n2 = (s - anx) // constants.SLICE_GRID_SPACING
            if n2 != n:
                n = n2
                anx = anx2
                self._logger.debug('Slice start is within lead time of next slice, using that one.')

            # Calculate the 'theoretical' slice start/end times, i.e. the grid
            # nodes, with overlap added.
            slice_start = anx + n * constants.SLICE_GRID_SPACING - constants.SLICE_OVERLAP_START
            slice_end = anx + (n + 1) * constants.SLICE_GRID_SPACING + constants.SLICE_OVERLAP_END
            slice_nr = (n % constants.SLICES_PER_ORBIT) + 1
            self._hdr.acquisitions[0].slice_frame_nr = slice_nr

            # Calculate the 'real' start/end times
            acq_start = max(slice_start, segment_start)
            acq_end = min(slice_end, segment_end)
            self._hdr.set_validity_times(slice_start, slice_end)
            self._logger.debug('Create slice #{}, {}-{}, anx {}'.format(
                slice_nr,
                acq_start,
                acq_end,
                anx
            ))
            self._create_product(acq_start, acq_end)

            start = acq_end

'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw output product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0073

Biomass Level 0 output product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0045
'''
import datetime
import os
from typing import List

from biomass import product_name
from biomass import product_generator
from job_order import JobOrderInput, JobOrderOutput

ISO_TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'


def _time_from_iso(timestr):
    timestr = timestr[:-1]  # strip 'Z'
    return datetime.datetime.strptime(timestr, ISO_TIME_FORMAT)


def _is_intersection(t1start, t1end, t2start, t2end):
    # Returns True if time 1 is (partly) within time 2
    return (t1start <= t2start <= t1end) or (t2start <= t1start <= t2end)


class Sx_RAW__0x(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 slice based products.

    Input is a set of (partial) RAWSxxx_10 slices.
    If one or more slices are incomplete (due to dump transitions), they are
    merged. The output is a single product, or multiple if there are data take
    transitions within the slice period.
    '''

    PRODUCTS = ['S1_RAW__0S', 'S1_RAWP_0M',
                'S2_RAW__0S', 'S2_RAWP_0M',
                'S3_RAW__0S', 'S3_RAWP_0M',
                'RO_RAW__0S', 'RO_RAWP_0M',
                'EC_RAW__0S', 'EC_RAWP_0M']

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

        # Get anx list from config. Can be located at either scenario or product level
        anx_list = output_config.get('anx') or scenario_config.get('anx')
        if anx_list is None:
            raise Exception('ANX must be configured for {} product'.format(self._output_type))
        self.anx_list = [_time_from_iso(anx) for anx in anx_list]
        self.anx_list.sort()
        self._data_takes = self._read_data_takes_from_config()

    def _read_data_takes_from_config(self):
        data_takes = []
        for dt in self._scenario_config.get('data_takes'):
            id = dt['id']
            start = _time_from_iso(dt['validity_start'])
            stop = _time_from_iso(dt['validity_stop'])
            data_takes.append({'id': id, 'start': start, 'stop': stop})
        return sorted(data_takes, key=lambda k: k['start'])

    def parse_inputs(self, input_products: List[JobOrderInput]) -> bool:
        # First copy the metadata from any input product (normally H or V)
        if not super().parse_inputs(input_products):
            return False

        # 'Merge' partial H or V slices. If either H or V (or both?) consists of
        # multiple parts, then use the overall time as validity period for the
        # output.
        HV_PRODUCTS = ['RAWS025_10', 'RAWS026_10']  # TODO: extend!
        for input in input_products:
            if input.file_type in HV_PRODUCTS:
                for file in input.file_names:
                    gen = product_name.ProductName()
                    if gen.parse_path(file):
                        self._start = min(self._start, gen._start_time)
                        self._stop = max(self._stop, gen._stop_time)
        return True

    def _generate_product(self, start, stop, data_take_id):
        self._logger.debug('Create product for datatake {}, {}-{}'.format(data_take_id, start, stop))
        name_gen = product_name.ProductName()
        name_gen.setup(self._output_type, start, stop, self._baseline_id, self._create_date)
        dir_name = name_gen.generate_path_name()

        self.hdr.set_product_type(self._output_type, self._baseline_id)
        self.hdr.set_product_filename(dir_name)
        self.hdr.set_validity_times(start, stop)
        self.hdr.set_data_take_id(data_take_id)
        self.hdr.set_num_of_lines(self._num_l0_lines, self._num_l0_lines_corrupt, self._num_l0_lines_missing)

        # Create directory and files
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self.hdr.write(file_name)

        # H/V measurement data
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxh'))
        self._generate_bin_file(file_name, self._size//2)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxv'))
        self._generate_bin_file(file_name, self._size//2)

        # Ancillary products, low rate
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxh'))
        self._generate_bin_file(file_name)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxv'))
        self._generate_bin_file(file_name)

    def generate_output(self):
        super(Sx_RAW__0x, self).generate_output()
        self._create_date, _ = self.hdr.get_phenomenon_times()   # HACK: fill in current date?

        # Find data take(s) in this slice and create products for each segment.
        # TODO: partial/incomplete slice flags!
        start = self._start
        stop = self._stop
        for dt in self._data_takes:
            if dt['start'] <= start <= dt['stop']:  # Segment starts within this data take
                stop = min(stop, dt['stop'])
                self._generate_product(start, stop, dt['id'])
                if stop >= self._stop:
                    break
                start = stop


class Sx_RAW__0M(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 slice based products.

    Input is a set of (partial) RAWSxxx_10 slices.
    If one or more slices are incomplete (due to dump transitions), they are
    merged. The output is a single product, or multiple if there are data take
    transitions within the slice period.
    '''

    PRODUCTS = ['S1_RAW__0M', 'S2_RAW__0M', 'S3_RAW__0M']

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

    def _generate_product(self, start, stop):
        name_gen = product_name.ProductName()
        name_gen.setup(self._output_type, start, stop, self._baseline_id, self._create_date)
        dir_name = name_gen.generate_path_name()

        self.hdr.set_product_type(self._output_type, self._baseline_id)
        self.hdr.set_product_filename(dir_name)
        self.hdr.set_validity_times(start, stop)
        self.hdr.set_num_of_lines(self._num_l0_lines, self._num_l0_lines_corrupt, self._num_l0_lines_missing)

        # Create directory and files
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self.hdr.write(file_name)

        # H/V measurement data
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxh'))
        self._generate_bin_file(file_name, self._size//2)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxv'))
        self._generate_bin_file(file_name, self._size//2)

        # Ancillary products, low rate
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxh'))
        self._generate_bin_file(file_name)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxv'))
        self._generate_bin_file(file_name)

    def generate_output(self):
        super().generate_output()
        self._create_date, _ = self.hdr.get_phenomenon_times()   # HACK: fill in current date?
        start = self._start
        stop = self._stop
        self._generate_product(start, stop)

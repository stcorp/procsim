'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw data generator.
'''
import os
import sys
import datetime
import constants

from lxml import etree as et

import biomass_mph


def get_file_type(mode: str, polarization: str):
    if mode == 'MEASUREMENT' and polarization == 'H':
        return 'RAW_025_10'
    if mode == 'MEASUREMENT' and polarization == 'V':
        return 'RAW_026_10'
    if mode == 'RECEIVE_ONLY' and polarization == 'H':
        return 'RAW_027_10'
    if mode == 'RECEIVE_ONLY' and polarization == 'V':
        return 'RAW_028_10'


class ProductNameGenerator:
    '''
    This class is responsible for creating the correct directory/file names,
    according to BIO-ESA-EOPG-EEGS-TN-0050, BIOMASS Products Naming Convention.
    '''
    SATELLITE_ID = 'BIO'   # FIXED

    def __init__(self, file_type):
        self.file_type = file_type
        self.start_time = datetime.datetime(2021, 1, 1, 0, 0, 0)
        self.stop_time = datetime.datetime(2021, 1, 1, 1, 30, 0)
        self.downlink_time = datetime.datetime(2021, 1, 1, 2, 0, 0)
        self.baseline_identifier = 1
        self.compact_create_date = 'ACZ976'

    def _generate_prefix(self):
        name = '{}_{}_{}_{}_'\
            .format(self.SATELLITE_ID,
                    self.file_type,
                    self.start_time.strftime('%Y%m%dT%H%M%S'),
                    self.stop_time.strftime('%Y%m%dT%H%M%S'))
        return name

    # def generate_l0l1(self):
    #     return self._generate_prefix() + '<P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>_<BB>_<DDDDDD>'

    def generate_path(self):
        name = self._generate_prefix() + 'D{}_{:02}_{}'\
            .format(
                self.downlink_time.strftime('%Y%m%dT%H%M%S'),
                self.baseline_identifier,
                self.compact_create_date
            )
        return name

    def generate_mph_file_name(self):
        return self.generate_path().lower() + '.xml'

    def generate_binary_file_name(self):
        name = self._generate_prefix() + 'D{}.dat'.format(
            self.downlink_time.strftime('%Y%m%dT%H%M%S')
        )
        return name.lower()


class RawProductGenerator:
    '''This class is responsible for generating raw Biomass data.'''
    def __init__(self, output_path):
        self.output_path = output_path
        self.orbit_nr = 0
        self.mode = 'MEASUREMENT'

    def _generate_bin_file(self, file_name):
        file = open(file_name, 'w')
        file.write('test')

    def _generate_data_take(self, tstart, tend):
        '''Generate product data for this data take.'''
        print('Generate data take for orbit {}, {}'.format(self.orbit_nr, tstart))
        file_type = get_file_type(self.mode, 'H')
        name_gen = ProductNameGenerator(file_type)
        name_gen.generate_binary_file_name()
        name_gen.generate_mph_file_name()

    def generate(self, start_time: datetime.datetime, end_time: datetime.datetime):
        '''Generate raw data file(s) over the specified period'''
        self.orbit_nr = int((start_time - constants.ANX).total_seconds() / constants.ORBIT_DURATION.total_seconds())
        data_take_start = constants.ORBIT_DURATION / 4
        max_data_takes = 5
        data_take_duration = datetime.timedelta(0, 300)  # 'several minutes'

        # Simulate orbits. During every orbit, multiple data takes are produced.
        while (start_time < end_time):
            orbit_time = data_take_start
            nr_data_takes = 0
            while orbit_time + data_take_duration < constants.ORBIT_DURATION and nr_data_takes < max_data_takes:
                self._generate_data_take(start_time + orbit_time, start_time + orbit_time + data_take_duration)
                orbit_time += data_take_duration
                nr_data_takes += 1

            print('Generate data for orbit {}'.format(self.orbit_nr))
            self.orbit_nr = self.orbit_nr + 1
            start_time += constants.ORBIT_DURATION

        name_gen = ProductNameGenerator(get_file_type(self.mode, 'H'))
        self.eop_identifier = name_gen.generate_path()
        dir_name = os.path.join(self.output_path, self.eop_identifier)

        # Create directory
        print('Create {}'.format(dir_name))
        os.makedirs(dir_name, exist_ok=True)

        # Create MPH file
        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        mph = biomass_mph.MainProductHeader()
        mph.write(file_name)

        # Create binary telemetry file
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
        self._generate_bin_file(file_name)


def main():
    args = sys.argv[1:]
    output_path = 'data'
    if len(args) > 0:
        output_path = args[0]

    gen = RawProductGenerator(output_path)
    start = datetime.datetime(2021, 2, 1, 0, 0, 0)    # Just some value
    stop = start + datetime.timedelta(0.5, 0)
    gen.generate(start, stop)


if __name__ == "__main__":
    main()

'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw data generator, according to BIO-ESA-EOPG-EEGS-TN-0073,
'BIOMASS RAW Product Format Definition'.

The following data is generated:
- Instrument Science data (including high-rate Instrument Ancillary data)
- Recorded Platform Housekeeping TM (Platform HKTM)
- Recorded Instrument Housekeeping TM (Instrument HKTM)
- Platform Ancillary data
- Instrument Ancillary data (low-rate)

Settings:
- Mission phase

Assumptions:
- Data is 'downlinked' at the start of every orbit.
- Several data takes produce science data
'''
import datetime
import os
import sys

from biomass import constants, mph, product_name


def get_science_data_file_type(mode: str, polarization: str):
    # Science data
    if mode == 'MEASUREMENT' and polarization == 'H':
        return 'RAW_025_10'
    if mode == 'MEASUREMENT' and polarization == 'V':
        return 'RAW_026_10'
    if mode == 'RECEIVE_ONLY' and polarization == 'H':
        return 'RAW_027_10'
    if mode == 'RECEIVE_ONLY' and polarization == 'V':
        return 'RAW_028_10'
    if mode == 'CALIBRATION' and polarization == 'H':
        return 'RAW_035_10'
    if mode == 'CALIBRATION' and polarization == 'V':
        return 'RAW_036_10'


def get_ancillary_data_file_type(mode: str, polarization: str = None):
    if mode == 'PLATFORM_ANC':
        return 'RAW_022_10'
    if mode == 'INSTRUMENT_ANC' and polarization == 'H':
        return 'RAW_023_10'
    if mode == 'INSTRUMENT_ANC' and polarization == 'V':
        return 'RAW_024_10'


def get_housekeeping_type():
    return 'RAW___HKTM'


class RawProductGenerator:
    '''This class is responsible for generating raw Biomass data.'''
    def __init__(self, output_path, mission_phase='COMMISIONING', mode='MEASUREMENT'):
        self.orbit_nr = 0
        self.output_path = output_path
        self.mission_phase = mission_phase  # INTERFEROMETRIC, TOMOGRAPHIC
        self.mode = 'MEASUREMENT'
        self.hdr = mph.MainProductHeader()
        self.baseline_id = 1

        # Fill in some fixed data
        self.hdr.acquisition_station = ''

    def _generate_bin_file(self, file_name):
        file = open(file_name, 'w')
        file.write('test')

    def _generate_data_take(self, tstart, tend, tdownlink):
        # Generate data takes
        file_type = get_science_data_file_type(self.mode, 'H')
        self._write_product(file_type, tstart, tend, tdownlink)
        file_type = get_science_data_file_type(self.mode, 'V')
        self._write_product(file_type, tstart, tend, tdownlink)

    def _generate_anc_hk(self, tstart, tend, tdownlink):
        # Generate housekeeping and ancillary data
        file_type = get_housekeeping_type()
        self._write_product(file_type, tstart, tend, tdownlink)
        file_type = get_ancillary_data_file_type('PLATFORM_ANC')
        self._write_product(file_type, tstart, tend, tdownlink)
        file_type = get_ancillary_data_file_type('INSTRUMENT_ANC', 'H')
        self._write_product(file_type, tstart, tend, tdownlink)
        file_type = get_ancillary_data_file_type('INSTRUMENT_ANC', 'V')
        self._write_product(file_type, tstart, tend, tdownlink)

    def _write_product(self, file_type, start, stop, tdownlink):
        # Construct eop (file name), setup main product header
        name_gen = product_name.ProductName()
        tcreate = start  # HACK - use current date?
        name_gen.setup(file_type, start, stop, self.baseline_id, tcreate, tdownlink)
        self.hdr.set_product_type(file_type)
        self.hdr.eop_identifier = name_gen.generate_path_name()
        self.hdr.validity_start = start
        self.hdr.validity_end = stop
        self.hdr.downlink_date = tdownlink

        # Create directory and files
        dir_name = os.path.join(self.output_path, self.hdr.eop_identifier)
        os.makedirs(dir_name, exist_ok=True)
        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self.hdr.write(file_name)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
        self._generate_bin_file(file_name)
        print('Created directory {}'.format(dir_name))

    def generate(self, start_time: datetime.datetime, end_time: datetime.datetime):
        '''Generate raw data file(s) over the specified period'''
        self.orbit_nr = int((start_time - constants.ORBIT0_START).total_seconds() / constants.ORBIT_DURATION.total_seconds())
        data_take_start = constants.ORBIT_DURATION / 4
        max_data_takes = 5
        data_take_duration = datetime.timedelta(0, 300)  # 'several minutes'

        # Simulate orbits. During every orbit, multiple data takes are produced.
        # Assume tdonwlink is at the start of the next orbit.
        while (start_time < end_time):
            tdownlink = start_time + constants.ORBIT_DURATION
            self._generate_anc_hk(start_time, start_time + constants.ORBIT_DURATION, tdownlink)
            orbit_time = data_take_start
            nr_data_takes = 0
            while orbit_time + data_take_duration < constants.ORBIT_DURATION and nr_data_takes < max_data_takes:
                self._generate_data_take(start_time + orbit_time, start_time + orbit_time + data_take_duration, tdownlink)
                orbit_time += data_take_duration
                nr_data_takes += 1
            self.orbit_nr = self.orbit_nr + 1
            start_time += constants.ORBIT_DURATION


def main():
    args = sys.argv[1:]
    output_path = 'data'
    if len(args) > 0:
        output_path = args[0]

    gen = RawProductGenerator(output_path)
    start = datetime.datetime(2021, 2, 1, 0, 0, 0)    # Just some value
    stop = start + datetime.timedelta(0.1, 0)
    gen.generate(start, stop)


if __name__ == "__main__":
    main()

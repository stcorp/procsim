'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass product name generator/parser, according to
BIO-ESA-EOPG-EEGS-TN-0050, BIOMASS Products Naming Convention.
'''
import datetime
import os
import re

from biomass import constants


class ProductName:
    '''
    This class is responsible for creating and parsing directory/file names.
    '''
    DATETIME_FORMAT = '%Y%m%dT%H%M%S'

    @classmethod
    def str_to_time(cls, s):
        return datetime.datetime.strptime(s, cls.DATETIME_FORMAT)

    @classmethod
    def time_to_str(cls, t):
        return t.strftime(cls.DATETIME_FORMAT)

    def __init__(self):
        # Common
        self._file_type: str
        self._start_time: datetime.datetime
        self._stop_time: datetime.datetime
        self._baseline_identifier: int
        self._compact_create_date: str

        # Raw only
        self._downlink_time: datetime.datetime

        # Level 0/1/2a only
        self._mission_phase_id: str
        self._global_coverage_id: str
        self._major_cycle_id: str
        self._repeat_cycle_id: str
        self._track_nr: str
        self._frame_slice_nr: str

    def _set_compact_creation_date(self, time: datetime.datetime):
        '''The compact creation date is a string representing the elapsed seconds (as an integer
        number) of the creation event from a reference epoch date/time converted to the reference
        base 36 (i.e. all the numbers and letters [0-9, A-Z]). This mechanism allows to code a
        period of about 70 years with a granularity of one second. In the above example AFRS00
        corresponds to “00:00:00 01/01/2020” having as reference epoch “00:00:00 of
        01/01/2000”, i.e. there are 631152000 seconds between the two dates and such number is
        then converted to base 36. The reference epoch to be used for the BIOMASS data is TBD.'''
        sec = int((time - constants.COMPACT_DATE_EPOCH).total_seconds())
        date36 = ''
        for i in range(6):
            sec, x = divmod(sec, 36)
            if x < 10:
                date36 = str(x) + date36
            else:
                date36 = chr(x + 65 - 10) + date36
        self._compact_create_date = date36

    def get_level(self):
        # Return either 'raw' or 'level0_1_2a
        pattern_raw = 'RAW[_S][0-9]{3}_[0-9]{2}'
        # TODO: We should make a large table somewhere?!
        pattern_l012 = ['S[123]_RAW__0[SM]', 'RO_RAW__0[SM]', 'EC_RAW__0[SM]', 'S[123]_RAWP_0M', 'RO_RAWP_0M', 'EC_RAWP_0M']
        if self._file_type == 'RAW___HKTM' or re.match(pattern_raw, self._file_type):
            return 'raw'
        for pattern in pattern_l012:
            if re.match(pattern, self._file_type):
                return 'level0_1_2a'

    def _parse_raw(self, file):
        self._start_time = self.str_to_time(file[15:30])
        self._stop_time = self.str_to_time(file[31:46])
        self._downlink_time = self.str_to_time(file[48:63])
        self._baseline_identifier = int(file[64:66])
        self._compact_create_date = file[67:73]

    def _parse_level0_1_2a(self, file):
        # Format:
        # <MMM>_<TTTTTTTTTT>_<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>_<BB>_<DDDDDD>
        # We can't split using 'split', as the IDs can also contain underscores!
        self._start_time = self.str_to_time(file[15:30])
        self._stop_time = self.str_to_time(file[31:46])
        self._mission_phase_id = file[47]
        self._global_coverage_id = file[50:52]
        self._major_cycle_id = file[54:56]
        self._repeat_cycle_id = file[58:60]
        self._track_nr = file[62:65]
        self._frame_slice_nr = file[67:70]
        self._baseline_identifier = int(file[71:73])
        self._compact_create_date = file[74:80]

    def parse_path(self, path):
        # Extract parameters from path name, return True if succesfull.
        file = os.path.basename(path)
        if file[0:3] != constants.SATELLITE_ID:
            return False
        self._file_type = file[4:14]
        level = self.get_level()
        if level == 'raw':
            self._parse_raw(file)
        elif level == 'level0_1_2a':
            self._parse_level0_1_2a(file)
        else:
            return False
        return True

    def _generate_prefix(self):
        # First part is the same for raw and level0/1/2a
        # <MMM>_<TTTTTTTTTT>_<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_
        name = '{}_{}_{}_{}_'\
            .format(constants.SATELLITE_ID,
                    self._file_type,
                    self.time_to_str(self._start_time),
                    self.time_to_str(self._stop_time))
        return name

    def setup(self, file_type, tstart, tstop, baseline_id, create_date, tdownlink=None,
              mission_phase_id='C', global_coverage_id='__', major_cycle_id='__',
              repeat_cycle_id='__', track_nr='___', frame_slice_nr='___'):
        '''
        Setup path/filename generator.
        - start/stop are UTC start date and time:
            - Acquisition sensing time for L0
            - Acquisition Zero Doppler Time for L1
            - Acquisition Zero Doppler Time, start of first image in the Stack for L2A
        - mission_phase_id: C, I or T
        - global_coverage_id: 1-6 or __
        - major_cycle_id: 1-7 or __
        - track_nr: frame/slice id or ___
        - create_date: creation event time
        '''
        self._set_compact_creation_date(create_date)
        self._file_type = file_type
        self._start_time = tstart
        self._stop_time = tstop
        self._downlink_time = tdownlink
        self._baseline_identifier = baseline_id
        self._mission_phase_id = mission_phase_id
        self._global_coverage_id = global_coverage_id
        self._major_cycle_id = major_cycle_id
        self._repeat_cycle_id = repeat_cycle_id
        self._track_nr = track_nr
        self._frame_slice_nr = frame_slice_nr

    def generate_path_name(self):
        # Returns directory name
        if self.get_level() == 'raw':
            # Add D<yyyyMMddThhMMss>_<BB>_<DDDDDD>
            name = self._generate_prefix() + 'D{}_{:02}_{}'\
                .format(
                    self.time_to_str(self._downlink_time),
                    self._baseline_identifier,
                    self._compact_create_date
                )
        else:
            # Add <P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>_<BB>_<DDDDDD>
            name = self._generate_prefix() + '{}_G{:>02}_M{}_C{}_T{}_F{}_{:02}_{}'\
                .format(
                    self._mission_phase_id,
                    self._global_coverage_id,
                    self._major_cycle_id,
                    self._repeat_cycle_id,
                    self._track_nr,
                    self._frame_slice_nr,
                    self._baseline_identifier,
                    self._compact_create_date
                )
        return name

    def generate_mph_file_name(self):
        return self.generate_path_name().lower() + '.xml'

    def generate_binary_file_name(self, suffix=''):
        if self.get_level() == 'raw':
            name = self._generate_prefix() + 'D{}.dat'.format(
                self.time_to_str(self._downlink_time)
            )
        else:
            # Add <P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>
            name = self._generate_prefix() + '{}_G{}_M{}_C{}_T{}_F{}{}'\
                .format(
                    self._mission_phase_id,
                    self._global_coverage_id,
                    self._major_cycle_id,
                    self._repeat_cycle_id,
                    self._track_nr,
                    self._frame_slice_nr,
                    suffix
                )
        return name.lower()

    def dump_info(self, path=None):
        if path:
            self.parse_path(path)
            print('path:              ', path)
        print('type:              ', self._file_type)
        print('start:             ', self._start_time)
        print('stop:              ', self._stop_time)
        if self.get_level() == 'raw':
            print('downlink time:     ', self._downlink_time)
        else:
            print('phase ID:          ', self._mission_phase_id)
            print('global coverage ID:', self._global_coverage_id)
            print('major cycle ID:    ', self._major_cycle_id)
            print('repeat cycle ID:   ', self._repeat_cycle_id)
            print('track nr:          ', self._track_nr)
            print('frame/slice nr:    ', self._frame_slice_nr)
        print('baseline ID:       ', self._baseline_identifier)
        print('compact date:      ', self._compact_create_date)


if __name__ == "__main__":
    # Test parser
    gen = ProductName()
    gen.dump_info('data/raw/BIO_RAW_022_10_20210201T000000_20210201T013810_D20210201T013811_01_B09ZHL')
    gen.dump_info('data/raw/BIO_S1_RAW__0S_20210201T000000_20210201T013810_C_G___M___C___T____F____01_B0737M')

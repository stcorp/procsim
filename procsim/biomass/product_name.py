'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass product name generator/parser, according to BIO-ESA-EOPG-EEGS-TN-0050,
'BIOMASS Products Naming Convention'.
'''
import datetime
import os
import re
from biomass import constants


def get_compact_creation_date(time: datetime.datetime):
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
    return date36


def str_to_datetime(s):
    return datetime.datetime.strptime(s, '%Y%m%dT%H%M%S')


class ProductName:
    '''
    This class is responsible for creating and parsing directory/file names.
    '''
    SATELLITE_ID = 'BIO'   # FIXED

    def __init__(self):
        # Common
        self.file_type: str
        self.start_time: datetime.datetime
        self.stop_time: datetime.datetime
        self.baseline_identifier: int
        self.compact_create_date: str

        # Raw only
        self.downlink_time: datetime.datetime

        # Level 0/1/2a only
        self.mission_phase_id: str
        self.global_coverage_id: str
        self.major_cycle_id: str
        self.repeat_cycle_id: str
        self.track_nr: str
        self.frame_slice_nr: str

    def _get_level(self):
        # Return either 'raw' or 'level0_1_2a
        pattern_raw = 'RAW[_S][0-9]{3}_[0-9]{2}'
        pattern_l012 = ['S[123]_RAW__0[SM]', 'RO_RAW__0[SM]', 'EC_RAW__0[SM]']
        if self.file_type == 'RAW___HKTM' or re.match(pattern_raw, self.file_type):
            return 'raw'
        for pattern in pattern_l012:
            if re.match(pattern, self.file_type):
                return 'level0_1_2a'

    def _parse_raw(self, file):
        self.start_time = str_to_datetime(file[15:30])
        self.stop_time = str_to_datetime(file[31:46])
        self.downlink_time = str_to_datetime(file[48:63])
        self.baseline_identifier = int(file[64:66])
        self.compact_create_date = file[67:73]

    def _parse_level0_1_2a(self, file):
        # Format:
        # <MMM>_<TTTTTTTTTT>_<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>_<BB>_<DDDDDD>
        # We can't split using 'split', as the IDs can also contain underscores!
        self.start_time = str_to_datetime(file[15:30])
        self.stop_time = str_to_datetime(file[31:46])
        self.mission_phase_id = file[47]
        self.global_coverage_id = file[50:52]
        self.major_cycle_id = file[54:56]
        self.repeat_cycle_id = file[58:60]
        self.track_nr = file[62:65]
        self.frame_slice_nr = file[67:70]
        self.baseline_identifier = int(file[71:73])
        self.compact_create_date = file[74:80]

    def parse_path(self, path):
        # Extract parameters from path name, return True if succesfull.
        file = os.path.basename(path)
        if file[0:3] != self.SATELLITE_ID:
            return False
        self.file_type = file[4:14]
        level = self._get_level()
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
            .format(self.SATELLITE_ID,
                    self.file_type,
                    self.start_time.strftime('%Y%m%dT%H%M%S'),
                    self.stop_time.strftime('%Y%m%dT%H%M%S'))
        return name

    def setup(self, file_type, tstart, tstop, tdownlink, baseline_id,
              mission_phase_id='C', global_coverage_id='__', major_cycle_id='__',
              repeat_cycle_id='__', track_nr='___', frame_slice_nr='___'):
        # Todo: combine with generate path and generate mph etc.
        self.file_type = file_type
        self.start_time = tstart
        self.stop_time = tstop
        self.downlink_time = tdownlink
        self.baseline_identifier = baseline_id
        self.compact_create_date = get_compact_creation_date(self.downlink_time)    # TODO: for now.
        self.mission_phase_id = mission_phase_id
        self.global_coverage_id = global_coverage_id
        self.major_cycle_id = major_cycle_id
        self.repeat_cycle_id = repeat_cycle_id
        self.track_nr = track_nr
        self.frame_slice_nr = frame_slice_nr

    def generate_path(self):
        # Returns directory name
        if self._get_level() == 'raw':
            # Add D<yyyyMMddThhMMss>_<BB>_<DDDDDD>
            name = self._generate_prefix() + 'D{}_{:02}_{}'\
                .format(
                    self.downlink_time.strftime('%Y%m%dT%H%M%S'),
                    self.baseline_identifier,
                    self.compact_create_date
                )
        else:
            # Add <P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>_<BB>_<DDDDDD>
            name = self._generate_prefix() + '{}_G{}_M{}_C{}_T{}_F{}_{:02}_{}'\
                .format(
                    self.mission_phase_id,
                    self.global_coverage_id,
                    self.major_cycle_id,
                    self.repeat_cycle_id,
                    self.track_nr,
                    self.frame_slice_nr,
                    self.baseline_identifier,
                    self.compact_create_date
                )
        return name

    def generate_mph_file_name(self):
        return self.generate_path().lower() + '.xml'

    def generate_binary_file_name(self, suffix=''):
        if self._get_level() == 'raw':
            name = self._generate_prefix() + 'D{}.dat'.format(
                self.downlink_time.strftime('%Y%m%dT%H%M%S')
            )
        else:
            # Add <P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>
            name = self._generate_prefix() + '{}_G{}_M{}_C{}_T{}_F{}{}'\
                .format(
                    self.mission_phase_id,
                    self.global_coverage_id,
                    self.major_cycle_id,
                    self.repeat_cycle_id,
                    self.track_nr,
                    self.frame_slice_nr,
                    suffix
                )
        return name.lower()

    def dump_info(self, path=None):
        if path:
            self.parse_path(path)
            print('path:              ', path)
        print('type:              ', self.file_type)
        print('start:             ', self.start_time)
        print('stop:              ', self.stop_time)
        if self._get_level() == 'raw':
            print('downlink time:     ', self.downlink_time)
        else:
            print('phase ID:          ', self.mission_phase_id)
            print('global coverage ID:', self.global_coverage_id)
            print('major cycle ID:    ', self.major_cycle_id)
            print('repeat cycle ID:   ', self.repeat_cycle_id)
            print('track nr:          ', self.track_nr)
            print('frame/slice nr:    ', self.frame_slice_nr)
        print('baseline ID:       ', self.baseline_identifier)
        print('compact date:      ', self.compact_create_date)


if __name__ == "__main__":
    # Test parser
    gen = ProductName()
    gen.dump_info('data/raw/BIO_RAW_022_10_20210201T000000_20210201T013810_D20210201T013811_01_B09ZHL')
    gen.dump_info('data/raw/BIO_S1_RAW__0S_20210201T000000_20210201T013810_C_G___M___C___T____F____01_B0737M')

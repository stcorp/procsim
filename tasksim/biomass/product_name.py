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
        self.file_type: str
        self.start_time: datetime.datetime
        self.stop_time: datetime.datetime
        self.downlink_time: datetime.datetime
        self.baseline_identifier: int
        self.create_date: datetime.datetime

    def parse_path(self, path):
        # Extract parameters from path name, return True if succesfull.
        file = os.path.basename(path)
        if file[0:3] != self.SATELLITE_ID:
            return False
        self.file_type = file[4:14]
        pattern = 'RAW_[0-9]{3}_[0-9]{2}'
        if re.match(pattern, self.file_type):
            self.start_time = str_to_datetime(file[15:30])
            self.stop_time = str_to_datetime(file[31:46])
            self.downlink_time = str_to_datetime(file[48:63])
            self.baseline_identifier = file[64:66]
            self.compact_create_date = file[67:73]
        return True

    def _generate_prefix(self):
        # <MMM>_<TTTTTTTTTT>_<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_
        name = '{}_{}_{}_{}_'\
            .format(self.SATELLITE_ID,
                    self.file_type,
                    self.start_time.strftime('%Y%m%dT%H%M%S'),
                    self.stop_time.strftime('%Y%m%dT%H%M%S'))
        return name

    # def generate_l0l1(self):
    #     return self._generate_prefix() + '<P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>_<BB>_<DDDDDD>'
    def setup(self, file_type, tstart, tstop, tdownlink, baseline_id):
        # Todo: combine with generate path and generate mph etc.
        self.file_type = file_type
        self.start_time = tstart
        self.stop_time = tstop
        self.downlink_time = tdownlink
        self.baseline_identifier = baseline_id
        self.compact_create_date = get_compact_creation_date(self.downlink_time)    # TODO: for now.

    def generate_path(self):
        # D<yyyyMMddThhMMss>_<BB>_<DDDDDD>
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


if __name__ == "__main__":
    gen = ProductName()
    gen.parse_path('data/raw/BIO_RAW_022_10_20210201T000000_20210201T013810_D20210201T013811_01_B09ZHL')
    print(gen.file_type)
    print(gen.start_time)
    print(gen.stop_time)
    print(gen.downlink_time)
    print(gen.baseline_identifier)
    print(gen.compact_create_date)

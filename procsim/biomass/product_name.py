'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass product name generator/parser, according to
BIO-ESA-EOPG-EEGS-TN-0050, BIOMASS Products Naming Convention.
'''
import datetime
import os
import re
from typing import Optional

from procsim.core.exceptions import GeneratorError, ScenarioError

from . import constants, product_types

# REGEXes for Biomass product names.
# Note: the meaning of fields 'vstart' and 'vend' depends on the exact product type.
# For now, consider them all as 'validity'.
_REGEX_RAW_PRODUCT_NAME = re.compile(
    r'^BIO_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_(?P<vstop>[0-9]{8}T[0-9]{6})_'
    r'D(?P<downlink_time>[0-9]{8}T[0-9]{6})_(?P<baseline>[0-9]{2})_(?P<create_date>[0-9A-Z]{6})$')

_REGEX_L012_PRODUCT_NAME = re.compile(
    r'^BIO_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_(?P<vstop>[0-9]{8}T[0-9]{6})_'
    r'(?P<mission_phase>[CIT])_G(?P<global_cov>[0-9_]{2})_M(?P<major>[0-9_]{2})_C(?P<repeat>[0-9_]{2})_'
    r'T(?P<track>[0-9_]{3})_F(?P<frame_slice>[0-9_]{3})_(?P<baseline>[0-9]{2})_(?P<create_date>[0-9A-Z]{6})$')

_REGEX_AUX_NAME = re.compile(
    r'^BIO_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_(?P<vstop>[0-9]{8}T[0-9]{6})_(?P<baseline>[0-9]{2})_'
    r'(?P<create_date>[0-9A-Z]{6})$')

_REGEX_FOS_FILE_NAME = re.compile(
    r'^BIO_(?P<class>TEST|OPER)_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_'
    r'(?P<vstop>[0-9]{8}T[0-9]{6})_(?P<baseline>[0-9]{2})(?P<version>[0-9]{2})$')


class ProductName:
    '''
    This class is responsible for creating and parsing directory/file names.
    '''
    DEFAULT_COMPACT_DATE_EPOCH = datetime.datetime(2000, 1, 1, 0, 0, 0)
    DATETIME_FORMAT = '%Y%m%dT%H%M%S'
    MISSION_PHASES = [('Commissioning'), ('Interferometric'), ('Tomographic')]
    GLOBAL_COVERAGE_IDS = ['__', '01', '02', '03', '04', '05', '06']
    MAJOR_CYCLE_IDS = ['01', '02', '03', '04', '05', '06', '07']
    REPEAT_CYCLE_IDS = ['01', '02', '03', '04', '05', '06', '07', 'DR', '__']

    @classmethod
    def str_to_time(cls, s):
        return datetime.datetime.strptime(s, cls.DATETIME_FORMAT)

    @classmethod
    def time_to_str(cls, t):
        return t.strftime(cls.DATETIME_FORMAT)

    def __init__(self, compact_create_date_epoch: Optional[datetime.datetime] = None):
        # Common
        self.start_time: Optional[datetime.datetime]
        self.stop_time: Optional[datetime.datetime]
        self.baseline_identifier: Optional[int]
        self._compact_create_date_epoch = compact_create_date_epoch or self.DEFAULT_COMPACT_DATE_EPOCH
        self._file_type = None
        self._level = None
        self._compact_create_date = None

        # Raw only
        self.downlink_time: Optional[datetime.datetime]

        # Level 0/1/2a only
        self._mission_phase_id = None
        self._global_coverage_id_str = None
        self._major_cycle_id_str = None
        self._repeat_cycle_id_str = None
        self._track_nr = None
        self._frame_slice_nr_str = None

        # MPL only
        self._file_class = None
        self._version_nr = None

    @property
    def mission_phase(self):
        for phase in self.MISSION_PHASES:
            if phase[0].upper() == self._mission_phase_id:
                return phase
        return None

    @mission_phase.setter
    def mission_phase(self, phase: Optional[str]):
        if phase is not None:
            idx = self.MISSION_PHASES.index(phase.capitalize())
            self._mission_phase_id = self.MISSION_PHASES[idx][0]

    @property
    def file_type(self):
        return self._file_type

    @file_type.setter
    def file_type(self, type_code):
        type = product_types.find_product(type_code)
        if type is None:
            raise ScenarioError('Type code {} not valid for Biomass'.format(type_code))
        self._file_type = type.type
        self._level = type.level

    @property
    def level(self):
        return self._level

    @property
    def global_coverage_id(self):
        return self._global_coverage_id_str if not self._global_coverage_id_str == '__' else 'NA'

    @global_coverage_id.setter
    def global_coverage_id(self, id):
        if id is None or id == 'NA':
            id = '__'
        self.GLOBAL_COVERAGE_IDS.index(id)  # Test
        self._global_coverage_id_str = id

    @property
    def major_cycle_id(self):
        return self._major_cycle_id_str

    @major_cycle_id.setter
    def major_cycle_id(self, id):
        id = '{:>02}'.format(id)    # Add leading zeros if needed
        self.MAJOR_CYCLE_IDS.index(id)  # Test
        self._major_cycle_id_str = id

    @property
    def repeat_cycle_id(self):
        return self._repeat_cycle_id_str if self._repeat_cycle_id_str != '__' else None

    @repeat_cycle_id.setter
    def repeat_cycle_id(self, id):
        if id is None or id == 'NA':
            id = '__'
        id = '{:>02}'.format(id)    # Add leading zeros if needed
        self.REPEAT_CYCLE_IDS.index(id)  # Test
        self._repeat_cycle_id_str = id

    @property
    def track_nr(self):
        return self._track_nr

    @track_nr.setter
    def track_nr(self, nr: Optional[str]):
        if nr is None or nr == '___':
            self._track_nr = '___'
        else:
            if int(nr) < 0 or int(nr) > 999:
                raise GeneratorError('track_nr should be 0..999 or ___')
            self._track_nr = '{:03}'.format(int(nr))

    @property
    def frame_slice_nr(self):
        if self._frame_slice_nr_str is not None and self._frame_slice_nr_str != '___':
            return int(self._frame_slice_nr_str)
        return None

    @frame_slice_nr.setter
    def frame_slice_nr(self, nr):
        if nr is None:
            self._frame_slice_nr_str = '___'
        else:
            if int(nr) < 0 or int(nr) > 999:
                raise GeneratorError('frame_slice_nr should be 3 digits')
            self._frame_slice_nr_str = '{:03}'.format(int(nr))

    @property
    def file_class(self):
        return self._file_class

    @file_class.setter
    def file_class(self, class_type):
        if class_type != 'OPER' and class_type != 'TEST':
            raise GeneratorError('file_class should be OPER or TEST')
        self._file_class = class_type

    @property
    def version_nr(self):
        if self._version_nr is not None:
            return int(self._version_nr)
        return None

    @version_nr.setter
    def version_nr(self, nr):
        inr = int(nr)
        if inr < 0 or inr > 99:
            raise GeneratorError('version_nr should be 2 digits')
        self._version_nr = f'{inr:02}'

    def set_creation_date(self, time: Optional[datetime.datetime]):
        '''
        Convert to 'compact create date, see the spec.
        If set to None, use 'now'.
        '''
        if time is None:
            time = datetime.datetime.utcnow()
        sec = int((time - self._compact_create_date_epoch).total_seconds())
        date36 = ''
        for i in range(6):
            sec, x = divmod(sec, 36)
            if x < 10:
                date36 = str(x) + date36
            else:
                date36 = chr(x + 65 - 10) + date36
        self._compact_create_date = date36

    def _parse_raw(self, re_result):
        self.file_type = re_result['type']
        self.start_time = self.str_to_time(re_result['vstart'])
        self.stop_time = self.str_to_time(re_result['vstop'])
        self.downlink_time = self.str_to_time(re_result['downlink_time'])
        self.baseline_identifier = int(re_result['baseline'])
        self._compact_create_date = re_result['create_date']

    def _parse_aux(self, re_result):
        self.file_type = re_result['type']
        self.start_time = self.str_to_time(re_result['vstart'])
        self.stop_time = self.str_to_time(re_result['vstop'])
        self.baseline_identifier = int(re_result['baseline'])
        self._compact_create_date = re_result['create_date']

    def _parse_level0_1_2a(self, re_result):
        self.file_type = re_result['type']
        self.start_time = self.str_to_time(re_result['vstart'])
        self.stop_time = self.str_to_time(re_result['vstop'])
        self._mission_phase_id = re_result['mission_phase']
        self._global_coverage_id_str = re_result['global_cov']
        self._major_cycle_id_str = re_result['major']
        self._repeat_cycle_id_str = re_result['repeat']
        self._track_nr = re_result['track']
        self._frame_slice_nr_str = re_result['frame_slice']
        self.baseline_identifier = int(re_result['baseline'])
        self._compact_create_date = re_result['create_date']

    def _parse_mpl(self, re_result):
        self.file_class = re_result['class']
        self.file_type = re_result['type']
        self.start_time = self.str_to_time(re_result['vstart'])
        self.stop_time = self.str_to_time(re_result['vstop'])
        self.baseline_identifier = int(re_result['baseline'])
        self.version_nr = int(re_result['version'])

    def parse_path(self, path):
        # Extract parameters from path name, return True if successful.
        filename = os.path.basename(path)

        REGEX_PARSE_FUNCTIONS = [
            (_REGEX_RAW_PRODUCT_NAME, self._parse_raw),
            (_REGEX_AUX_NAME, self._parse_aux),
            (_REGEX_L012_PRODUCT_NAME, self._parse_level0_1_2a),
            (_REGEX_FOS_FILE_NAME, self._parse_mpl)]

        for regex, parse_function in REGEX_PARSE_FUNCTIONS:
            m = regex.match(filename)
            if m:
                parse_function(m.groupdict())
                return True

        raise GeneratorError(f'Cannot recognise file {filename}')

    def _generate_prefix(self):
        # First part is the same for raw and level0/1/2a
        # <MMM>_<TTTTTTTTTT>_<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>
        return f'{constants.SATELLITE_ID}_{self._file_type}_{self.time_to_str(self.start_time)}_{self.time_to_str(self.stop_time)}'

    def generate_path_name(self):
        # Returns directory name
        if self.baseline_identifier is None:
            raise ScenarioError('baseline_id must be set')
        if self._level == 'raw':
            if self.downlink_time is None:
                raise ScenarioError('acquisition_date must be set')
            # Add D<yyyyMMddThhMMss>_<BB>_<DDDDDD>
            name = self._generate_prefix() + '_D{}_{:02}_{}'.format(
                self.time_to_str(self.downlink_time),
                self.baseline_identifier,
                self._compact_create_date
            )
        elif self._level == 'aux':
            # Add _<BB>_<DDDDDD>
            name = self._generate_prefix() + '_{:02}_{}'.format(
                self.baseline_identifier,
                self._compact_create_date
            )
        elif self._level == 'mpl':
            name = f'{constants.SATELLITE_ID}_{self._file_class}_{self._file_type}'\
                + f'_{self.time_to_str(self.start_time)}_{self.time_to_str(self.stop_time)}'\
                + f'_{self.baseline_identifier:02}{self.version_nr:02}'
        else:
            if self._mission_phase_id is None:
                raise ScenarioError('mission_phase must be set')
            if self._global_coverage_id_str is None:
                raise ScenarioError('global_coverage_id must be set')
            if self._major_cycle_id_str is None:
                raise ScenarioError('major_cycle_id must be set')
            if self._repeat_cycle_id_str is None:
                raise ScenarioError('repeat_cycle_id_str must be set')
            if self._track_nr is None:
                raise ScenarioError('track_nr must be set')
            if self._frame_slice_nr_str is None:
                raise ScenarioError('frame_slice_nr must be set')
            # Add <P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>_<BB>_<DDDDDD>
            name = self._generate_prefix() + '_{}_G{:>02}_M{}_C{}_T{}_F{}_{:02}_{}'.format(
                self._mission_phase_id,
                self._global_coverage_id_str,
                self._major_cycle_id_str,
                self._repeat_cycle_id_str,
                self._track_nr,
                self._frame_slice_nr_str,
                self.baseline_identifier,
                self._compact_create_date
            )
        return name

    def generate_mph_file_name(self):
        return self.generate_path_name().lower() + '.xml'

    def generate_binary_file_name(self, suffix='', extension='.dat'):
        if suffix is None:
            suffix = ''
        if extension is None:
            extension = ''
        if len(extension) >= 1 and extension[0] != '.':
            extension = '.' + extension

        if self._level == 'raw':
            name = self._generate_prefix() + '_D{}.dat'.format(
                self.time_to_str(self.downlink_time)
            )
        elif self._level == 'aux':
            name = self._generate_prefix() + '{}{}'.format(
                suffix,
                extension
            )
        else:
            # Add <P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>
            name = self._generate_prefix() + '_{}_G{}_M{}_C{}_T{}_F{}{}{}'.format(
                self._mission_phase_id,
                self._global_coverage_id_str,
                self._major_cycle_id_str,
                self._repeat_cycle_id_str,
                self._track_nr,
                self._frame_slice_nr_str,
                suffix,
                extension
            )
        return name.lower()

    def dump_info(self, path=None):
        if path:
            self.parse_path(path)
            print('path:              ', path)
        print('type:              ', self._file_type)
        print('level:             ', self._level)
        print('start:             ', self.start_time)
        print('stop:              ', self.stop_time)
        if self._level == 'raw':
            print('downlink time:     ', self.downlink_time)
        else:
            print('mission phase ID:  ', self._mission_phase_id)
            print('global coverage ID:', self.global_coverage_id)
            print('major cycle ID:    ', self.major_cycle_id)
            print('repeat cycle ID:   ', self.repeat_cycle_id)
            print('track nr:          ', self.track_nr)
            print('frame/slice nr:    ', self.frame_slice_nr)
        print('baseline ID:       ', self.baseline_identifier)
        print('compact date:      ', self._compact_create_date)

'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex product name generator/parser, according to
ESA-EOPG-EEGS-TN-0015, FLEX Products Naming Convention.
'''
import datetime
import os
import re
from typing import Optional

from procsim.core.exceptions import GeneratorError, ScenarioError

from . import constants, product_types

# REGEXes for Flex product names.
# Note: the meaning of fields 'vstart' and 'vend' depends on the exact product type.
# For now, consider them all as 'validity'.
_REGEX_RAW_PRODUCT_NAME = re.compile(
    r'^BIO_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_(?P<vstop>[0-9]{8}T[0-9]{6})_'
    r'D(?P<downlink_time>[0-9]{8}T[0-9]{6})_(?P<baseline>[0-9]{2})_(?P<create_date>[0-9A-Z]{6})(?:.(?P<extension>[a-zA-Z]{3}))?$')

_REGEX_L012_PRODUCT_NAME = re.compile(
    r'^BIO_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_(?P<vstop>[0-9]{8}T[0-9]{6})_'
    r'(?P<mission_phase>[CIT])_G(?P<global_cov>[0-9_]{2})_M(?P<major>[0-9_]{2})_C(?P<repeat>[0-9_]{2})_'
    r'T(?P<track>[0-9_]{3})_F(?P<frame_slice>[0-9_]{3})_(?P<baseline>[0-9]{2})_(?P<create_date>[0-9A-Z]{6})(?:.(?P<extension>[a-zA-Z]{3}))?$')

_REGEX_VFRA_FILE_NAME = re.compile(
    r'^BIO_(?P<class>TEST|OPER)_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_'
    r'(?P<vstop>[0-9]{8}T[0-9]{6})_(?P<baseline>[0-9]{2})_(?P<create_date>[0-9A-Z]{6})(?:.(?P<extension>[a-zA-Z]{3}))$')

_REGEX_AUX_NAME = re.compile(
    r'^BIO_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_(?P<vstop>[0-9]{8}T[0-9]{6})_(?P<baseline>[0-9]{2})_'
    r'(?P<create_date>[0-9A-Z]{6})(?:.(?P<extension>[a-zA-Z]{3}))?$')

_REGEX_FOS_FILE_NAME = re.compile(
    r'^BIO_(?P<class>TEST|OPER)_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_'
    r'(?P<vstop>[0-9]{8}T[0-9]{6})_(?P<baseline>[0-9]{2})(?P<version>[0-9]{2})(?:.(?P<extension>[a-zA-Z]{3}))?$')


class ProductName:
    '''
    This class is responsible for creating and parsing directory/file names.
    '''
    DEFAULT_COMPACT_DATE_EPOCH = datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    DATETIME_FORMAT = '%Y%m%dT%H%M%S'
    MISSION_PHASES = [('Commissioning'), ('Interferometric'), ('Tomographic')]
    GLOBAL_COVERAGE_IDS = ['__', '01', '02', '03', '04', '05', '06']
    MAJOR_CYCLE_IDS = ['01', '02', '03', '04', '05', '06', '07']
    REPEAT_CYCLE_IDS = ['01', '02', '03', '04', '05', '06', '07', 'DR', '__']

    @classmethod
    def str_to_time(cls, s):
        return datetime.datetime.strptime(s, cls.DATETIME_FORMAT).replace(tzinfo=datetime.timezone.utc) if s else None

    @classmethod
    def str_to_int(cls, s):
        return int(s) if s else None

    @classmethod
    def time_to_str(cls, t):
        return t.strftime(cls.DATETIME_FORMAT)

    def __init__(self, compact_create_date_epoch: Optional[datetime.datetime] = None):
        # Common
        self.start_time: Optional[datetime.datetime] = None
        self.stop_time: Optional[datetime.datetime] = None
        self.baseline_identifier: Optional[str]
        self.relative_orbit_number: Optional[str]
        self.cycle_number: Optional[str]
        self.anx_elapsed: Optional[float] = None
        self._compact_create_date_epoch = compact_create_date_epoch or self.DEFAULT_COMPACT_DATE_EPOCH
        self._file_type = None
        self._level = None
        self._compact_create_date = None
        self._frame_slice_nr_str = None
        self.use_short_name = False

        # Raw only
        self.downlink_time: Optional[datetime.datetime]

        # Level 0/1/2a only
        self._mission_phase_id = None

        # MPL and VFRA only
        self._file_class = None
        self._version_nr = None

    @property
    def mission_phase(self):
        for phase in self.MISSION_PHASES:
            if phase[0].upper() == self._mission_phase_id:
                return phase
        return None

    @mission_phase.setter
    def mission_phase(self, phase):
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
            raise ScenarioError('Type code {} not valid for Flex'.format(type_code))
        self._file_type = type.type
        self._level = type.level

    @property
    def level(self):
        return self._level

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
        if class_type and class_type != 'OPER' and class_type != 'TEST':
            raise GeneratorError('file_class should be OPER or TEST')
        self._file_class = class_type

    @property
    def version_nr(self):
        if self._version_nr is not None:
            return int(self._version_nr)
        return None

    @version_nr.setter
    def version_nr(self, nr):
        if not nr:
            return
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
            time = datetime.datetime.now(tz=datetime.timezone.utc)
        self._creation_date = time
        sec = int((time - self._compact_create_date_epoch).total_seconds())
        date36 = ''
        for i in range(6):
            sec, x = divmod(sec, 36)
            if x < 10:
                date36 = str(x) + date36
            else:
                date36 = chr(x + 65 - 10) + date36
        self._compact_create_date = date36

    def parse_path(self, path):
        # Extract parameters from path name, return True if successful.
        filename = os.path.basename(path)

        # Set all fields that can be extracted from the filename; set others to None.
        for regex in [_REGEX_RAW_PRODUCT_NAME, _REGEX_AUX_NAME, _REGEX_L012_PRODUCT_NAME, _REGEX_VFRA_FILE_NAME, _REGEX_FOS_FILE_NAME]:
            match = regex.match(filename)
            if match:
                match_dict = match.groupdict()
                self.file_class = match_dict.get('class')
                self.file_type = match_dict.get('type')
                self.start_time = self.str_to_time(match_dict.get('vstart'))
                self.stop_time = self.str_to_time(match_dict.get('vstop'))
                self.downlink_time = self.str_to_time(match_dict.get('downlink_time'))
                self.baseline_identifier = match_dict.get('baseline')
                self._compact_create_date = match_dict.get('create_date')
                self._mission_phase_id = match_dict.get('mission_phase')
                self._global_coverage_id_str: Optional[str] = match_dict.get('global_cov')
                self._major_cycle_id_str = match_dict.get('major')
                self._repeat_cycle_id_str = match_dict.get('repeat')
                self._track_nr = match_dict.get('track')
                self._frame_slice_nr_str = match_dict.get('frame_slice')
                self.version_nr = self.str_to_int(match_dict.get('version'))
                return True

        raise GeneratorError(f'Cannot recognize file {filename}')

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
            if self._file_type == 'RAW___HKTM':
                name = self._generate_prefix() + '_O{}'.format(
                    constants.ABS_ORBIT,
                )
            else:
                name = self._generate_prefix() + '_{}'.format(
                    self.time_to_str(self.downlink_time),
                )

        elif self._level == 'aux':
            name = self._generate_prefix() + '_{}_{}'.format(
                self.time_to_str(self._creation_date),
                self.baseline_identifier,
            )

        elif self.use_short_name:  # raws, l0
            if self._level == 'raws':
                if self.downlink_time is None:
                    raise ScenarioError('acquisition_date must be set')

            name = self._generate_prefix() + '_{}_{}'.format(
                self.time_to_str(self.downlink_time),
                self.baseline_identifier,
            )

        elif not self.use_short_name:
            if self.downlink_time is None:
                raise ScenarioError('acquisition_date must be set')

            if self.stop_time is not None and self.start_time is not None:
                duration = int((self.stop_time - self.start_time).total_seconds())  # TODO now both here and in mph.. move to product_generator?
            else:
                duration = 0

            name = self._generate_prefix() + '_{}_{:04}_{}_{}_{:04}_{}'.format(
                self.time_to_str(self.downlink_time),
                duration,
                self.cycle_number,
                self.relative_orbit_number,
                int(self.anx_elapsed or 0),
                self.baseline_identifier,
            )
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
            name = self._generate_prefix() + '_{}_G{:>02}_M{}_C{}_T{}_F{}_{}_{}'.format(
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

    def generate_binary_file_name(self, suffix=None, extension='.dat'):
        if suffix is None:
            suffix = ''
        if extension is None:
            extension = ''
        if len(extension) >= 1 and extension[0] != '.':
            extension = '.' + extension

        if self._level == 'raw':
            if self._file_type == 'RAW___HKTM':
                name = self._generate_prefix() + '_O{}.dat'.format(
                    constants.ABS_ORBIT,
                )
            else:
                name = self._generate_prefix() + '_{}.dat'.format(
                    self.time_to_str(self.downlink_time),
                    constants.ABS_ORBIT,
                )

        elif self._level == 'aux':
            name = self._generate_prefix() + '_{}_{}{}{}'.format(
                self.time_to_str(self._creation_date),
                self.baseline_identifier,
                suffix,
                extension,
            )

        elif self.use_short_name: # raws, l0
            name = self._generate_prefix() + '_{}_{}.dat'.format(
                self.time_to_str(self.downlink_time),
                self.baseline_identifier,
            )


        elif not self.use_short_name: # raws, l0
            if self.stop_time is not None and self.start_time is not None:
                duration = int((self.stop_time - self.start_time).total_seconds())
            else:
                duration = 0

            name = self._generate_prefix() + '_{}_{:04}_{}_{}_{:04}_{}{}{}'.format(
                self.time_to_str(self.downlink_time),
                duration,
                self.cycle_number,
                self.relative_orbit_number,
                int(self.anx_elapsed or 0),
                self.baseline_identifier,
                suffix,
                extension,
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
            print('frame/slice nr:    ', self.frame_slice_nr)
        print('baseline ID:       ', self.baseline_identifier)
        print('compact date:      ', self._compact_create_date)

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

# FLX_RAW___HKTM_20170101T060131_20170101T060706_O12345
_REGEX_RAW_HKTM_PRODUCT_NAME = re.compile(
    r'^FLX_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_(?P<vstop>[0-9]{8}T[0-9]{6})_'
    r'O(?P<absorbit>[0-9]{5})(?:.(?P<extension>[a-zA-Z]{3}))?$')

# FLX_L0__DEFDAR_20170101T060131_20170101T060344_20230213T104618_0133_012_046_0090_1B
_REGEX_LONG_PRODUCT_NAME = re.compile(
    r'^FLX_(?P<type>.{10})_(?P<vstart>[0-9]{8}T[0-9]{6})_(?P<vstop>[0-9]{8}T[0-9]{6})_'
    r'(?P<create_date>[0-9]{8}T[0-9]{6})_(?P<duration>[0-9]{4})_(?P<cyclenr>[0-9]{3})_'
    r'(?P<relorbit>[0-9]{3})_(?P<anx_elapsed>[0-9]{4})_(?P<baseline>[0-9a-zA-Z]{2})'
    r'(?:.(?P<extension>[a-zA-Z]{3}))?$')


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
        self.suffix: Optional[str]
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

        # MPL and VFRA only
        self._file_class = None
        self._version_nr = None

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
        for regex in [_REGEX_RAW_HKTM_PRODUCT_NAME, _REGEX_LONG_PRODUCT_NAME]:  # TODO
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
                self.cycle_number = match_dict.get('cyclenr')

                return True

        raise GeneratorError(f'Cannot recognize file {filename}')

    def _generate_prefix(self):
        # First part is the same for raw and level0/1/2a
        # <MMM>_<TTTTTTTTTT>_<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>
        return f'{constants.SATELLITE_ID}_{self._file_type}_{self.time_to_str(self.start_time)}_{self.time_to_str(self.stop_time)}'

    def generate_path_name(self):
        # Returns directory name

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

        else:  # raws, l0
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

        elif self.use_short_name:  # raws, l0
            name = self._generate_prefix() + '_{}_{}{}.dat'.format(
                self.time_to_str(self.downlink_time),
                self.baseline_identifier,
                suffix,
            )

        else:  # raws, l0
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

        print('baseline ID:       ', self.baseline_identifier)
        print('compact date:      ', self._compact_create_date)

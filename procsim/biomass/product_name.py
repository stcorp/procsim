'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass product name generator/parser, according to
BIO-ESA-EOPG-EEGS-TN-0050, BIOMASS Products Naming Convention.
'''
import datetime
import os
from typing import Optional

from procsim.core.exceptions import GeneratorError, ScenarioError

from . import constants, product_types


class ProductName:
    '''
    This class is responsible for creating and parsing directory/file names.
    '''
    COMPACT_DATE_EPOCH = datetime.datetime(2000, 1, 1, 0, 0, 0)
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

    def __init__(self):
        # Common
        self.start_time: Optional[datetime.datetime]
        self.stop_time: Optional[datetime.datetime]
        self.baseline_identifier: Optional[int]
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
        self._track_nr_str = None
        self._frame_slice_nr_str = None

    @property
    def mission_phase(self):
        for phase in self.MISSION_PHASES:
            if phase[0].upper() == self._mission_phase_id:
                return phase
        return None

    @mission_phase.setter
    def mission_phase(self, phase: Optional[str]):
        if str is not None:
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
        if self._track_nr_str == '___':
            return None
        return self._track_nr_str

    @track_nr.setter
    def track_nr(self, nr):
        if nr is None:
            self._track_nr_str = '___'
        else:
            if int(nr) < 0 or int(nr) > 999:
                raise GeneratorError('track_nr should be 3 digits')
            self._track_nr_str = '{:03}'.format(int(nr))

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

    def set_creation_date(self, time: Optional[datetime.datetime]):
        # Convert to 'compact create date, see the spec.
        sec = int((time - self.COMPACT_DATE_EPOCH).total_seconds())
        date36 = ''
        for i in range(6):
            sec, x = divmod(sec, 36)
            if x < 10:
                date36 = str(x) + date36
            else:
                date36 = chr(x + 65 - 10) + date36
        self._compact_create_date = date36

    def _parse_raw(self, file):
        self.start_time = self.str_to_time(file[15:30])
        self.stop_time = self.str_to_time(file[31:46])
        self.downlink_time = self.str_to_time(file[48:63])
        self.baseline_identifier = int(file[64:66])
        self._compact_create_date = file[67:73]

    def _parse_aux(self, file):
        self.start_time = self.str_to_time(file[15:30])
        self.stop_time = self.str_to_time(file[31:46])
        self.baseline_identifier = int(file[47:49])
        self._compact_create_date = file[50:56]

    def _parse_level0_1_2a(self, file):
        # Format:
        # <MMM>_<TTTTTTTTTT>_<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>_<BB>_<DDDDDD>
        # We can't split using 'split', as the IDs can also contain underscores!
        self.start_time = self.str_to_time(file[15:30])
        self.stop_time = self.str_to_time(file[31:46])
        self._mission_phase_id = file[47]
        self._global_coverage_id_str = file[50:52]
        self._major_cycle_id_str = file[54:56]
        self._repeat_cycle_id_str = file[58:60]
        self._track_nr_str = file[62:65]
        self._frame_slice_nr_str = file[67:70]
        self.baseline_identifier = int(file[71:73])
        self._compact_create_date = file[74:80]

    def parse_path(self, path):
        # Extract parameters from path name, return True if succesfull.
        file = os.path.basename(path)
        id = file[0:3]
        if id != constants.SATELLITE_ID:
            raise GeneratorError('Incorrect satellite ID in file path {}, must be {}'.format(id, constants.SATELLITE_ID))
        self.file_type = file[4:14]
        if self._level == 'raw':
            self._parse_raw(file)
        elif self._level == 'aux':
            self._parse_aux(file)
        elif self._level == 'l0' or self._level == 'l1' or self._level == '2a' or self._level == 'aux':
            self._parse_level0_1_2a(file)
        else:
            raise GeneratorError('Cannot handle type {}'.format(self.file_type))

    def _generate_prefix(self):
        # First part is the same for raw and level0/1/2a
        # <MMM>_<TTTTTTTTTT>_<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>
        name = '{}_{}_{}_{}'\
            .format(constants.SATELLITE_ID,
                    self._file_type,
                    self.time_to_str(self.start_time),
                    self.time_to_str(self.stop_time))
        return name

    def generate_path_name(self):
        # Returns directory name
        if self.baseline_identifier is None:
            raise ScenarioError('baseline_id must be set')
        if self._level == 'raw':
            if self.downlink_time is None:
                raise ScenarioError('acquisition_date must be set')
            # Add D<yyyyMMddThhMMss>_<BB>_<DDDDDD>
            name = self._generate_prefix() + '_D{}_{:02}_{}'\
                .format(
                    self.time_to_str(self.downlink_time),
                    self.baseline_identifier,
                    self._compact_create_date
                )
        elif self._level == 'aux':
            # Add _<BB>_<DDDDDD>
            name = self._generate_prefix() + '_{:02}_{}'\
                .format(
                    self.baseline_identifier,
                    self._compact_create_date
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
            if self._track_nr_str is None:
                raise ScenarioError('track_nr must be set')
            if self._frame_slice_nr_str is None:
                raise ScenarioError('frame_slice_nr must be set')
            # Add <P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>_<BB>_<DDDDDD>
            name = self._generate_prefix() + '_{}_G{:>02}_M{}_C{}_T{}_F{}_{:02}_{}'\
                .format(
                    self._mission_phase_id,
                    self._global_coverage_id_str,
                    self._major_cycle_id_str,
                    self._repeat_cycle_id_str,
                    self._track_nr_str,
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
            name = self._generate_prefix() + '_{}_G{}_M{}_C{}_T{}_F{}{}{}'\
                .format(
                    self._mission_phase_id,
                    self._global_coverage_id_str,
                    self._major_cycle_id_str,
                    self._repeat_cycle_id_str,
                    self._track_nr_str,
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

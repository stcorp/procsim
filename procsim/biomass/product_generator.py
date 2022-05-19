'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import bisect
import datetime
from math import ceil
import os
import re
import shutil
from typing import Iterable, List, Optional, Tuple
from xml.etree import ElementTree as et

from procsim.biomass.product_types import ORBPRE_PRODUCT_TYPES
from procsim.core.exceptions import GeneratorError, ScenarioError
from procsim.core.iproduct_generator import IProductGenerator
from procsim.core.job_order import JobOrderInput, JobOrderOutput
from procsim.core.logger import Logger

from . import main_product_header, product_name


class GeneratedFile():
    '''Hold some information on a file that is to be generated.'''

    def __init__(self, path: List[str] = [], suffix: str = '', extension: str = '', representation: Optional['GeneratedFile'] = None) -> None:
        self.path: List[str] = path
        self.suffix: str = suffix
        self.extension: str = extension
        self.representation: Optional['GeneratedFile'] = representation

        self._name: Optional[str] = None  # Override automatic name generation.

    def set_name_information(self, new_name: str) -> None:
        dir_name, self._name = os.path.split(new_name)
        self.path = dir_name.split(os.sep)
        print(dir_name)
        base_name, self.extension = os.path.splitext(self._name)
        if self.extension:
            self.extension = self.extension[1:]  # Trim period off extension.
        self.suffix = base_name.rsplit('_')[-1]

    def get_full_path(self, name_gen: product_name.ProductName, base_dir: str = '') -> str:
        if self._name is None:
            self._name = name_gen.generate_binary_file_name('_' + self.suffix, self.extension)
        return os.path.join(base_dir, *self.path, self._name)


class ProductGeneratorBase(IProductGenerator):
    '''
    Biomass product generator (abstract) base class. This class is responsible
    for creating Biomass products.
    This base class handles parsing input products to retrieve metadata.
    '''
    ISO_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

    # These parameters are common for ALL product generators
    _COMMON_GENERATOR_PARAMS = [
        ('output_path', '_output_path', 'str'),
        ('compact_creation_date_epoch', '_compact_creation_date_epoch', 'date'),
        ('creation_date', '_creation_date', 'date'),
        ('zip_extension', '_zip_extension', 'str'),
        ('begin_end_position_from_toi', '_begin_end_position_from_toi', 'bool'),
        ('toi_start_offset', '_toi_start_offset', 'float'),
        ('toi_stop_offset', '_toi_stop_offset', 'float')
    ]

    _COMMON_HDR_PARAMS = [
        ('baseline', 'product_baseline', 'int'),
        ('begin_position', 'begin_position', 'date'),
        ('end_position', 'end_position', 'date')
    ]

    def __init__(self, logger, job_config: Optional[JobOrderOutput], scenario_config: dict, output_config: dict):
        self._scenario_config = scenario_config
        self._output_config = output_config
        self._job_config_baseline = None if job_config is None else job_config.baseline
        self._job_toi_start = None if job_config is None else job_config.toi_start
        self._job_toi_stop = None if job_config is None else job_config.toi_stop
        self._logger = logger
        self._output_type = output_config['type']
        self._size_mb = int(output_config.get('size', '0'))
        self._meta_data_source: Optional[str] = output_config.get('metadata_source')
        self._hdr = main_product_header.MainProductHeader()
        self._meta_data_source_file = None
        self._anx_list = []

        # Parameters related to virtual frames. TODO: Move to header?
        self._frame_id = None
        self._frame_start_time = None
        self._frame_stop_time = None
        self._frame_status = None

        # Parameters that can be set in scenario
        self._output_path: str = '.' if job_config is None else job_config.dir
        self._compact_creation_date_epoch = product_name.ProductName.DEFAULT_COMPACT_DATE_EPOCH
        self._creation_date: Optional[datetime.datetime] = None
        self._zip_extension = '.zip'
        self._begin_end_position_from_toi = False
        self._toi_start_offset = 0.0
        self._toi_stop_offset = 0.0

    def get_params(self) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        '''
        Returns lists with generator- and metadata parameters that can be used
        in the scenario.
        '''
        return self._COMMON_GENERATOR_PARAMS, self._COMMON_HDR_PARAMS, []

    def _create_name_generator(self, hdr: main_product_header.MainProductHeader) -> product_name.ProductName:
        '''
        Create product name generator and setup fields required for level0/1/2,
        using the metadata in hdr.

        The start/stop times are copied from the begin/end position fields,
        the 'phenomenon' times, which seem to contain the correct times.
        '''

        acq = hdr.acquisitions[0]
        name_gen = product_name.ProductName(self._compact_creation_date_epoch)
        name_gen.file_type = hdr.product_type
        name_gen.start_time = hdr.begin_position
        name_gen.stop_time = hdr.end_position
        name_gen.baseline_identifier = hdr.product_baseline
        name_gen.set_creation_date(hdr.processing_date)
        name_gen.mission_phase = acq.mission_phase
        name_gen.global_coverage_id = acq.global_coverage_id
        name_gen.major_cycle_id = acq.major_cycle_id
        name_gen.repeat_cycle_id = acq.repeat_cycle_id
        name_gen.track_nr = acq.track_nr
        name_gen.frame_slice_nr = acq.slice_frame_nr
        return name_gen

    def _resolve_wildcard_product_type(self) -> str:
        '''
        Type code can be a 'wildcard' type, such as Sx_RAW__0S.
        In that case, select the correct type using the swath (which must be known now).
        '''
        if self._output_type in ['Sx_RAW__0S', 'Sx_RAWP_0M', 'Sx_RAW__0M',
                                 'Sx_SCS__1S', 'Sx_SCS__1M', 'Sx_DGM__1S',
                                 'Sx_STA__1S', 'Sx_STA__1M']:
            swath = self._hdr.sensor_swath
            if swath is None:
                raise ScenarioError('Swath must be configured to resolve Sx_ type')
            if swath not in ['S1', 'S2', 'S3']:
                raise ScenarioError('Swath must be S1, S2 or S3')
            return self._output_type.replace('Sx', swath)
        else:
            return self._output_type

    def _time_from_iso_or_none(self, timestr):
        if timestr is None:
            return None
        return self._time_from_iso(timestr)

    def _time_from_iso(self, timestr):
        if timestr[-1] == 'Z':
            timestr = timestr[:-1]
        return datetime.datetime.strptime(timestr, self.ISO_TIME_FORMAT).replace(tzinfo=datetime.timezone.utc)

    def _add_file_to_product(self, file_path: str, size_mb: Optional[int] = None, representation_path: Optional[str] = None) -> None:
        '''Append a file to the MPH product list and generate it. Also generate a representation (i.e. schema) if indicated.'''
        try:
            mph_path = os.path.join(self._output_path, self._hdr.products[0]['file_name'])
        except (IndexError, KeyError) as e:
            self._logger.error("No MPH directory found. Set the product name via 'MainProductHeader.set_product_filename(filename)'.")
            raise e

        relative_file_path = './' + os.path.relpath(file_path, mph_path)
        relative_representation_path = None if representation_path is None else './' + os.path.relpath(representation_path, mph_path)
        self._hdr.append_file(relative_file_path, size_mb, relative_representation_path)
        # If this file is in the preview folder and has the png extension, set it as the browse file.
        if self._hdr.browse_image_filename == '' and relative_file_path.startswith('./preview/') and relative_file_path.endswith('.png'):
            self._hdr.browse_image_filename = relative_file_path

        if representation_path is not None:
            print(f'GENERATING REPRESENTATION {representation_path}')
            self._generate_bin_file(representation_path, 0)
        self._generate_bin_file(file_path, size_mb)

    def _generate_bin_file(self, file_path: str, size_mb: Optional[int]) -> None:
        '''Generate binary file starting with a short ASCII header, followed by
        size (in MB) random data bytes.'''
        # Make sure encompassing folder exists.
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        CHUNK_SIZE = 2**20
        size = size_mb * 2**20 if size_mb is not None else 0
        file = open(file_path, 'wb')
        while size > 0:
            amount = min(size, CHUNK_SIZE)
            file.write(os.urandom(max(amount, 0)))
            size -= amount
        file.close()

    @staticmethod
    def zip_folder(full_dir_name: str, extension: Optional[str] = None) -> None:
        root_dir, base_dir = os.path.split(os.path.normpath(full_dir_name))
        old_name = shutil.make_archive(full_dir_name, 'zip', root_dir, base_dir)
        if extension is not None:
            new_name = os.path.splitext(old_name)[0] + extension
            os.rename(old_name, new_name)
        shutil.rmtree(full_dir_name)

    @staticmethod
    def unzip(archive_path: str, keep_zip: bool = False, logger: Optional[Logger] = None) -> None:
        archive_dir, archive_name = os.path.split(archive_path)
        if logger is not None:
            logger.debug('Extract {}{}'.format(
                '(keep zip) ' if keep_zip else '',
                os.path.basename(archive_name)))
        shutil.unpack_archive(archive_path, archive_dir, 'zip')
        if not keep_zip:
            os.remove(archive_path)

    def parse_inputs(self, input_products: Iterable[JobOrderInput]) -> bool:
        '''
        For all files:
            - check if it is a (zipped) directory (all biomass products except MPL and VFRA are directories)
            - unzip product if it's a zip archive
            - extract metadata if this product matches self.meta_data_source
        '''
        gen = product_name.ProductName(self._compact_creation_date_epoch)
        pattern = self._meta_data_source
        mph_is_parsed = False
        for input in input_products:
            for file in input.file_names:
                root, ext = os.path.splitext(file)
                if os.path.isfile(file) and ext.lower() == self._zip_extension:
                    # Sanity check: only raw products should be zipped
                    name_gen = product_name.ProductName(self._compact_creation_date_epoch)
                    name_gen.parse_path(file)
                    if name_gen.level != 'raw':
                        self._logger.warning('{} should not be a zip!'.format(os.path.basename(file)))
                    keep_zip = self._output_config.get('keep_zip') or self._scenario_config.get('keep_zip', False)
                    self.unzip(file, keep_zip, logger=self._logger)
                if not os.path.isdir(root):
                    # Handle single file products.
                    if input.file_type in ORBPRE_PRODUCT_TYPES and not self._anx_list:
                        # Only parse orbit prediction files if no ANX information was present in the scenario.
                        self._parse_orbit_prediction_file(file)
                file = root
                if not mph_is_parsed and pattern is not None and re.match(pattern, file):
                    self._logger.debug('Parse {} for {}'.format(os.path.basename(file), self._output_type))
                    gen.parse_path(file)
                    # Derive mph file name from product name, parse header
                    hdr = self._hdr
                    mph_file_name = os.path.join(file, gen.generate_mph_file_name())
                    hdr.parse(mph_file_name)
                    mph_is_parsed = True
                    self._meta_data_source_file = file

        # The baseline ID is not copied from any source, but read from job order
        # (if available) or set in scenario config.
        self._hdr.product_baseline = self._job_config_baseline

        if (pattern is not None) and (not mph_is_parsed):
            self._logger.error('Cannot find matching product for [{}] to extract metdata from'.format(pattern))
            return False
        return True

    def _parse_orbit_prediction_file(self, file_name: str) -> List[datetime.datetime]:
        '''Get ANX timestamp information from orbit prediction file.'''
        root = et.parse(file_name).getroot()

        # Get the default namespace, if any.
        ns = {}
        if root.tag[0] == '{':
            uri = root.tag[1:root.tag.index('}')]
            ns['d'] = uri

        # Find all OSV elements containing ANX timestamps.
        self._anx_list = []
        for utc_timestamp in root.findall('d:Data_Block/d:List_of_OSVs/d:OSV/d:UTC', ns):
            if utc_timestamp.text is not None:
                # Trim 'UTC=' off the start of the timestamp and convert to datetime.
                self._anx_list.append(self._time_from_iso(utc_timestamp.text[4:]))

        self._anx_list.sort()

        return self._anx_list

    def _get_anx(self, t: datetime.datetime) -> Optional[datetime.datetime]:
        # Check whether a previous ANX can possibly be found.
        if not self._anx_list or t < self._anx_list[0]:
            self._logger.warning(f'No previous ANX found for {t} in ANX list {self._anx_list}.')
            return None
        # Returns the latest ANX before the given time
        idx = bisect.bisect(self._anx_list, t) - 1
        return self._anx_list[min(max(idx, 0), len(self._anx_list) - 1)]

    def _get_slice_frame_nr(self, start: datetime.datetime, spacing: datetime.timedelta) -> Optional[int]:
        previous_anx = self._get_anx(start)
        return (start - previous_anx) // spacing + 1 if previous_anx is not None else None

    def _get_slice_frame_interval(self,
                                  start: datetime.datetime,
                                  spacing: datetime.timedelta) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        previous_anx = self._get_anx(start)
        slice_frame_nr = self._get_slice_frame_nr(start, spacing)
        if previous_anx is None or slice_frame_nr is None:
            return None
        slice_frame_start = previous_anx + (slice_frame_nr - 1) * spacing
        slice_frame_end = previous_anx + slice_frame_nr * spacing
        return slice_frame_start, slice_frame_end

    def _get_slice_frame_boundaries_in_interval(self, start: datetime.datetime,
                                                stop: datetime.datetime,
                                                spacing: datetime.timedelta) -> List[datetime.datetime]:
        boundaries = []

        previous_anx = self._get_anx(start)
        if previous_anx:
            # Get the first slice/frame boundary >= the start time.
            start_slice_frame_idx = ceil((start - previous_anx) / spacing)
            boundary = previous_anx + start_slice_frame_idx * spacing
            while boundary <= stop:
                boundaries.append(boundary)
                boundary += spacing

        return boundaries

    def _read_config_param(self, config: dict, param_name: str, obj: object, hdr_field: str, ptype):
        '''
        If param_name is in config, read and set in obj.field.
        '''
        val = config.get(param_name)
        if val is None:
            return
        if not hasattr(obj, hdr_field):
            raise GeneratorError('Error: attribute {} not present in {}'.format(hdr_field, obj))
        old_val = getattr(obj, hdr_field)
        if ptype == 'date':
            val = self._time_from_iso_or_none(val)
        elif ptype == 'int':
            val = int(val)
        elif ptype == 'float':
            val = float(val)
            if type(old_val) == datetime.timedelta:
                val = datetime.timedelta(0, val)    # We expect seconds here
        elif ptype == 'array of str':
            pass
        else:
            pass
        self._logger.debug('{} {}{} to {}'.format(
            'Set' if old_val is None else 'Overwrite',
            param_name,
            '' if old_val is None else ' from {}'.format(old_val),
            val))
        setattr(obj, hdr_field, val)

    def list_scenario_parameters(self):
        gen_params, hdr_params, acq_params = self.get_params()
        return [(param, ptype) for param, _, ptype in hdr_params + acq_params + gen_params]

    def _apply_begin_end_position_from_toi(self):
        """
        Override begin/end position with values read from the job order, if present.
        Apply adjustable offset, in seconds.
        """
        if not self._job_toi_start:
            raise ScenarioError('No TOI start in jobOrder')
        if not self._job_toi_stop:
            raise ScenarioError('No TOI stop in jobOrder')
        self._hdr.begin_position = self._job_toi_start - datetime.timedelta(seconds=self._toi_start_offset)
        self._hdr.end_position = self._job_toi_stop + datetime.timedelta(seconds=self._toi_stop_offset)

    def read_scenario_parameters(self):
        '''
        Parse metadata parameters from scenario_config (either 'global' or for this output).
        '''
        gen_params, hdr_params, acq_params = self.get_params()
        for config in self._scenario_config, self._output_config:
            for param, hdr_field, type in hdr_params:
                self._read_config_param(config, param, self._hdr, hdr_field, type)
            for param, acq_field, type in acq_params:
                self._read_config_param(config, param, self._hdr.acquisitions[0], acq_field, type)
            for param, self_field, type in gen_params:
                self._read_config_param(config, param, self, self_field, type)

        if self._begin_end_position_from_toi:
            self._apply_begin_end_position_from_toi()

    def generate_output(self):
        '''
        Setup some mandatory metadata
        '''
        if self._creation_date is None:
            self._creation_date = datetime.datetime.now(tz=datetime.timezone.utc)

        self._hdr.set_processing_parameters(
            self._scenario_config['processor_name'],
            self._scenario_config['processor_version'])
        self._hdr.processing_date = self._creation_date

        self._logger.debug('Output directory is {}'.format(
            os.path.abspath(self._output_path)))

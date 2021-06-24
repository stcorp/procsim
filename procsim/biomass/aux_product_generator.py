'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Aux product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0054
'''
import os

from . import product_generator, product_name


_GENERATOR_PARAMS = [
    ('output_path', '_output_path', 'str'),
    ('compact_creation_date_epoch', '_compact_creation_date_epoch', 'date'),
]
_HDR_PARAMS = [
    ('baseline', 'product_baseline', 'int'),
    ('begin_position', 'begin_position', 'date'),
    ('end_position', 'end_position', 'date'),
]
_ACQ_PARAMS = [
    # Only for AUX_ORB and AUX_ATT
    ('data_take_id', 'data_take_id', 'int'),
]


class Aux(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 Auxiliary products.

    Currently, all AUX products consist of the MPH and a single XML + XSD
    representing the data and the XML schema respective.
    The suffixes used in the name of the data files are derived from the product
    type description, and are just examples!
    '''

    PRODUCTS = [
        'AUX_ATT___', 'AUX_CAL_AB', 'AUX_ERP___', 'AUX_GMF___', 'AUX_INS___',
        'AUX_ORB___', 'AUX_PP1___', 'AUX_PP2_2A', 'AUX_PP2_FH', 'AUX_PP2_FD',
        'AUX_PP2_AB', 'AUX_PP3___', 'AUX_PPS___', 'AUX_TEC___',
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._files = []    # Files to generate, including paths.

    def _generate_default_file_list(self):
        '''
        Generates a default file list for AUX products.
        Common rules:
        If a file is of type xml, a related xsd is placed in
        a 'support/' dir. A dataset suffix, e.g. _attitude', is added only if
        more than 1 file is in the data directory.
        '''
        DEFAULT_SUFFIX_EXTENSION = {
            'AUX_ATT___': ('attitude', 'xml'),
            'AUX_CAL_AB': ('above_ground', 'xml'),
            'AUX_ERP___': ('rotation', 'txt'),
            'AUX_GMF___': ('mag', 'txt'),
            'AUX_INS___': ('insparam', 'xml'),
            'AUX_ORB___': ('orbit', 'xml'),
            'AUX_PP1___': ('l1params', 'xml'),
            'AUX_PP2_2A': ('l2aparams', 'xml'),
            'AUX_PP2_FH': ('forestheight', 'xml'),
            'AUX_PP2_FD': ('forestdist', 'xml'),
            'AUX_PP2_AB': ('l2above_ground', 'xml'),
            'AUX_PP3___': ('l3params', 'xml'),
            'AUX_PPS___': ('stackparams', 'xml'),
            'AUX_TEC___': ('tec', 'txt')
        }
        suffix, extension = DEFAULT_SUFFIX_EXTENSION[self._output_type]
        self._files.append('data/$NAME.{}'.format(extension))
        if extension == 'xml':
            self._files.append('support/{}.xsd'.format(suffix))

    def get_params(self):
        return _GENERATOR_PARAMS, _HDR_PARAMS, _ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        if self._files == []:
            self._generate_default_file_list()

        # Setup MPH
        self._hdr.product_type = self._output_type

        start, stop = self._hdr.begin_position, self._hdr.end_position
        if self._hdr.validity_start is None:
            self._hdr.validity_start = start
        if self._hdr.validity_stop is None:
            self._hdr.validity_stop = stop

        name_gen = product_name.ProductName(self._compact_creation_date_epoch)
        name_gen.file_type = self._output_type
        name_gen.start_time = start
        name_gen.stop_time = stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(self._creation_date)

        dir_name = name_gen.generate_path_name()
        self._hdr.set_product_filename(dir_name)

        # Create root directory and header
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_name)

        # Create aux files
        base_name = name_gen.generate_binary_file_name('', '')
        for file in self._files:
            file = file.replace('$NAME', base_name)
            full_dirname = os.path.join(dir_name, os.path.dirname(file))
            os.makedirs(full_dirname, exist_ok=True)
            full_filename = os.path.join(dir_name, file)
            self._generate_bin_file(full_filename, self._size_mb / len(self._files))

'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex Aux product generators,
format according to ESA-EOPG-EOEP-TN-0026
'''
import os
from typing import List

from . import product_generator, product_name
from .product_generator import GeneratedFile

_GENERATOR_PARAMS = [
    ('output_path', '_output_path', 'str'),
    ('files', '_files', 'array of str'),
    ('zip_output', '_zip_output', 'bool'),
]

_HDR_PARAMS = [
    ('baseline', 'product_baseline', 'str'),
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

    By default, all AUX products consist of the MPH and subdirectories data/ and
    support/, containing a single XML file and the XML schema respective.
    The suffix used in the name of the data file is derived from the product
    type description, and is just an example.

    This behavior can be overruled by adding a "files" section, specifying for
    each file its full name and path (relative to the root of the product
    directory). You can use the $NAME variable, which expands to the full
    product name, in lowercase, as defined in BIO-ESA-EOPG-EEGS-TN-0050.
    Example:

      "outputs": [
        {
          "type": "AUX_PP1___",
          "files": [
              "data/$NAME_l1params.xml",
              "support/l1params.xsd"
          ]
        },
        ...

    For AUX_ATT___ and AUX_ORB___ products, an array "data_takes" with one or
    more data take objects can be specified in the scenario. Each data take
    object must contain at least the ID and start/stop times, and can contain
    other metadata fields. For example:

      "data_takes": [
        {
          "data_take_id": 15,
          "start": "2021-02-01T00:24:32.000Z",
          "stop": "2021-02-01T00:29:32.000Z",
          "swath": "S1",
          "operational_mode": "SM"  // example of an optional field
        },
    '''

    PRODUCTS = [
        'AUX_GCP_DB',

        'CFG_TSKTBL',
        'CFG_PF_BC_',
        'CFG_L0__PF',

        'AUX_IERS_B',
        'AUX_MET_A_',
        'AUX_MET_F_',
        'AUX_CCPOIV',
        'AUX_CCTEM_',
        'AUX_CCCHDC',
        'AUX_CCCHRF',
        'AUX_CCCACF',
        'AUX_CCCHNL',
        'AUX_CCCASI',
        'AUX_CCCHST',
        'AUX_CCCHSD',
        'AUX_CCFOCP',
        'AUX_CCCALN',
        'AUX_CCGAIN',
        'AUX_IERS_A',
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._generated_files: List[GeneratedFile] = []  # GeneratedFile objects to facilitate linking representations
        self._zip_output = False

    def _generate_default_file_list(self):
        '''
        Generates a default file list for AUX products.
        Common rules:
        If a file is of type xml, a related xsd is placed in
        a 'support/' dir. A dataset suffix, e.g. _attitude', is added only if
        more than 1 file is in the data directory.
        '''
        DEFAULT_SUFFIX_EXTENSION = {
            'AUX_GCP_DB': ('gcp_database', 'xml'),

            'CFG_PF_BC_': ('products_baseline', 'xml'),
            'CFG_TSKTBL': ('tasktables', 'xml'),
            'CFG_L0__PF': ('l0params', 'xml'),

            'AUX_IERS_A': ('data', 'txt'),
            'AUX_IERS_B': ('data', 'txt'),

            'AUX_CCPOIV': ('data', 'nc'),
            'AUX_CCTEM_': ('data', 'nc'),
            'AUX_CCCHDC': ('data', 'nc'),
            'AUX_CCCHRF': ('data', 'nc'),
            'AUX_CCCACF': ('data', 'nc'),
            'AUX_CCCHNL': ('data', 'nc'),
            'AUX_CCCASI': ('data', 'nc'),
            'AUX_CCCHST': ('data', 'nc'),
            'AUX_CCCHSD': ('data', 'nc'),
            'AUX_CCFOCP': ('data', 'nc'),
            'AUX_CCCALN': ('data', 'nc'),
            'AUX_CCGAIN': ('data', 'nc'),

            'AUX_MET_A_': ('data', 'grb'),
            'AUX_MET_F_': ('data', 'grb'),
        }
        suffix, extension = DEFAULT_SUFFIX_EXTENSION[self._output_type]
#
#        file = GeneratedFile(['data'], suffix, extension)
#        if extension == 'xml':
#            file.representation = GeneratedFile(['support'], suffix, 'xsd')

        file = GeneratedFile([], suffix, extension)
        self._generated_files.append(file)

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + _GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        # Setup MPH
        self._hdr.product_type = self._output_type

        # AUX_ATT___ and AUX_ORB___ types require data take information.
        if self._output_type in ['AUX_ATT___', 'AUX_ORB___']:
            for data_take_config, data_take_start, data_take_stop in self._get_data_takes_with_bounds():
                self.read_scenario_parameters(data_take_config)
                self._hdr.set_phenomenon_times(data_take_start, data_take_stop)

                self._generate_product()
        else:
            self._generate_product()

    def _generate_product(self) -> None:
        start, stop = self._hdr.begin_position, self._hdr.end_position

        name_gen = product_name.ProductName()
        name_gen.file_type = self._output_type
        name_gen.start_time = start
        name_gen.stop_time = stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(self._creation_date)

        dir_name = name_gen.generate_path_name()
        self._hdr.initialize_product_list(dir_name)

        # Create root directory and header
        self._logger.info(f'Create {dir_name}')
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        # Create aux files
        self._generate_default_file_list()

        for file in self._generated_files:
            representation_path = file.representation.get_full_path(name_gen, dir_name) if file.representation else None
            self._add_file_to_product(file.get_full_path(name_gen, dir_name), self._size_mb // len(self._generated_files), representation_path)

        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_name)

        if self._zip_output:
            self.zip_folder(dir_name, self._zip_extension)

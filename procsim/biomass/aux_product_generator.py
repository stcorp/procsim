'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Aux product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0054
'''
import os
from typing import List

from . import product_generator, product_name
from .product_generator import GeneratedFile

_GENERATOR_PARAMS = [
    ('output_path', '_output_path', 'str'),
    ('compact_creation_date_epoch', '_compact_creation_date_epoch', 'date'),
    ('files', '_files', 'array of str')
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
        'AUX_ATT___', 'AUX_CAL_AB', 'AUX_ERP___', 'AUX_GMF___', 'AUX_INS___',
        'AUX_ORB___', 'AUX_PP0___', 'AUX_PP1___', 'AUX_PP2_2A', 'AUX_PP2_FH',
        'AUX_PP2_FD', 'AUX_PP2_AB', 'AUX_PP3___', 'AUX_PPS___', 'AUX_TEC___',
    ]

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._files: List[str] = []  # Files to generate, including paths.
        self._generated_files: List[GeneratedFile] = []  # GeneratedFile objects to facilitate linking representations

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
            'AUX_PP0___': ('l0params', 'xml'),
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

        file = GeneratedFile(['data'], suffix, extension)
        if extension == 'xml':
            file.representation = GeneratedFile(['support'], suffix, 'xsd')
        self._generated_files.append(file)

    def _generate_files_from_names(self, name_gen: product_name.ProductName) -> None:
        for filename in self._files:
            file = GeneratedFile()
            file.set_name_information(filename.replace('$NAME', name_gen.generate_binary_file_name('', '')))

            # If the file is a schema, find the first element in the list that is an xml file and attach it as representation.
            if os.path.splitext(filename)[1] == '.xsd':
                for i, possible_xml in enumerate(self._generated_files):
                    if possible_xml.extension == 'xml' and possible_xml.representation is None:
                        self._generated_files[i].representation = file
                        break
            else:
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
        self._hdr.initialize_product_list(dir_name)

        # Create root directory and header
        self._logger.info(f'Create {dir_name}')
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        # Create aux files
        if self._files:
            self._generate_files_from_names(name_gen)
        else:
            self._generate_default_file_list()

        for file in self._generated_files:
            representation_path = file.representation.get_full_path(name_gen, dir_name) if file.representation else None
            self._add_file_to_product(file.get_full_path(name_gen, dir_name), self._size_mb // len(self._generated_files), representation_path)

        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_name)

'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Aux product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0054
'''
import os
from typing import List

from biomass import product_generator, product_name


_GENERATOR_PARAMS = [
    ('output_path', '_output_path', 'str'),
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

    def get_params(self):
        return _GENERATOR_PARAMS, _HDR_PARAMS, _ACQ_PARAMS

    def generate_output(self):
        super().generate_output()
        self._create_date = self._hdr.end_position   # HACK: fill in current date?

        SUFFIXES = {
            'AUX_ATT___': 'attitude',
            'AUX_CAL_AB': 'above_ground',
            'AUX_ERP___': 'rotation',
            'AUX_GMF___': 'mag',
            'AUX_INS___': 'insparam',
            'AUX_ORB___': 'orbit',
            'AUX_PP1___': 'l1params',
            'AUX_PP2_2A': 'l2aparams',
            'AUX_PP2_FH': 'forestheight',
            'AUX_PP2_FD': 'forestdist',
            'AUX_PP2_AB': 'l2above_ground',
            'AUX_PP3___': 'l3params',
            'AUX_PPS___': 'stackparams',
            'AUX_TEC___': 'tec',
        }
        self._create_aux_product(SUFFIXES[self._output_type], '.xml')

    def _create_aux_product(self, suffix, extension):
        # Setup MPH
        self._hdr.product_type = self._output_type

        start, stop = self._hdr.begin_position, self._hdr.end_position
        if self._hdr.validity_start is None:
            self._hdr.validity_start = start
        if self._hdr.validity_stop is None:
            self._hdr.validity_stop = stop

        name_gen = product_name.ProductName()
        name_gen.file_type = self._output_type
        name_gen.start_time = start
        name_gen.stop_time = stop
        name_gen.baseline_identifier = self._hdr.product_baseline
        name_gen.set_creation_date(self._create_date)

        dir_name = name_gen.generate_path_name()
        self._hdr.set_product_filename(dir_name)

        # Create directories and files
        self._logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self._output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self._hdr.write(file_name)

        data_dir = os.path.join(dir_name, 'data')
        os.makedirs(data_dir, exist_ok=True)
        file_name = os.path.join(data_dir, name_gen.generate_binary_file_name('_' + suffix, extension))
        self._generate_bin_file(file_name, self._size_mb)

        # This component has to be considered optional because
        # it shall not be used in case AUX data format is not XML
        if extension == '.xml':
            support_dir = os.path.join(dir_name, 'support')
            os.makedirs(support_dir, exist_ok=True)
            file_name = os.path.join(support_dir, suffix + '.xsd')
            self._generate_bin_file(file_name, 0)

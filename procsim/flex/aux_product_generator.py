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
    PRODUCTS = [
        'AUX_OBSMSK',
        'AUX_GCP_DB',
        'AUX_PF_BC_',
        'AUX_TSKTBL',
        'AUX_L0__PF',
    ]

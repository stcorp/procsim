'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 0 product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0073
'''
import datetime
import os
from typing import Iterable

from procsim.biomass import constants
from procsim.core.exceptions import ScenarioError
from procsim.core.job_order import JobOrderInput

from . import main_product_header, product_generator, product_name

_HDR_PARAMS = [
    # Level 0 only
    ('num_l0_lines', 'nr_l0_lines', 'str'),
    ('num_l0_lines_corrupt', 'nr_l0_lines_corrupt', 'str'),
    ('num_l0_lines_missing', 'nr_l0_lines_missing', 'str'),
    ('swath', 'sensor_swath', 'str'),
    ('operational_mode', 'sensor_mode', 'str'),
]
_ACQ_PARAMS = [
    # Level 0, 1, 2a only
    ('mission_phase', 'mission_phase', 'str'),
    ('data_take_id', 'data_take_id', 'int'),
    ('global_coverage_id', 'global_coverage_id', 'str'),
    ('major_cycle_id', 'major_cycle_id', 'str'),
    ('repeat_cycle_id', 'repeat_cycle_id', 'str'),
    ('track_nr', 'track_nr', 'str'),
]


class EO(product_generator.ProductGeneratorBase):
    PRODUCTS = [
        'L0_OBS___',
    ]

class CAL(product_generator.ProductGeneratorBase):
    PRODUCTS = [
        'L0_DARKNP',
        'L0_DARKNP',
        'L0_DARKSR',
        'L0_DARKSS',
        'L0_DEFDAR',
        'L0_DARKOC',
        'L0_DRKMTF',
        'L0_DRKSTR',
        'L0_SPECSD',
        'L0_SUN___',
        'L0_DEFSUN',
        'L0_MOON__',
        'L0_MOONSL',
        'L0_LINDES',
        'L0_LINSEA',
        'L0_LINSUN',
        'L0_LINDAR',
        'L0_CTE___',
        'L0_SCNVAL',
        'L0_COREG_',
        'L0_SPECEO',
        'L0_CLOUD_',
    ]

class ANC(product_generator.ProductGeneratorBase):
    PRODUCTS = [
        'L0_SAT_TM',
        'L0_NAVATT',
        'L0_PDHUTM',
        'L0_ICUDTM',
        'L0_VAU_TM',
        'L0_INSTTM',

        'L0_TST___',  # TODO ?
        'L0_UNK___',
    ]

'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass output product generator factory.
'''

from typing import Optional

from procsim.core.exceptions import ScenarioError
from procsim.core.iproduct_generator import IProductGenerator

from . import aux_product_generator as aux
from . import level0_product_generator as level0
from . import level1_product_generator as level1
from . import level2_product_generator as level2
from . import raw_product_generator as raw
from . import mpl_product_generator as mpl

_GENERATORS = [
    aux.Aux,
    mpl.Mpl,
    raw.RAW_xxx_10, raw.RAW___HKTM, raw.RAWSxxx_10,
    level0.Sx_RAW__0x, level0.Sx_RAW__0M, level0.AC_RAW__0A,
    level1.Level1Stripmap, level1.Level1Stack,
    level2.Level2a
]


def list_supported_products():
    list = []
    for gen in _GENERATORS:
        list.append(gen.PRODUCTS)
    return list


def product_generator_factory(logger, job_config, scenario_config, output_config) -> Optional[IProductGenerator]:
    product_type = output_config.get('type')
    if product_type is None:
        raise ScenarioError('Output product type ("type": ...) must be specified')
    for gen in _GENERATORS:
        if product_type in gen.PRODUCTS:
            return gen(logger, job_config, scenario_config, output_config)
    logger.error('No generator for product \'{}\' in Biomass plugin. Supported types are: {}'.format(
        product_type, list_supported_products()))
    return None

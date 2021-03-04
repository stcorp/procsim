'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass output product generator factory.
'''

from typing import Optional, List

from procsim import IProductGenerator

from biomass import level0_product_generator as level0
from biomass import raw_product_generator as raw

_GENERATORS = [
    raw.RAW_xxx_10, raw.RAWSxxx_10,
    level0.Sx_RAW__0x, level0.Sx_RAW__0M, level0.AC_RAW__0A, level0.Aux
]


def list_supported_products():
    list = []
    for gen in _GENERATORS:
        list.extend(gen.PRODUCTS)
    return list


def product_generator_factory(logger, job_config, scenario_config, output_config) -> Optional[IProductGenerator]:
    product_type = output_config['type']
    for gen in _GENERATORS:
        if product_type in gen.PRODUCTS:
            return gen(logger, job_config, scenario_config, output_config)
    logger.error('No generator for product \'{}\' in Biomass plugin. Supported types are: {}'.format(
        product_type, list_supported_products()))
    return None

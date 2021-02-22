'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass output product generator factory.
'''

from typing import Optional

from procsim import IProductGenerator

from biomass import constants
from biomass import level0


def OutputGeneratorFactory(logger, job_config, scenario_config) -> Optional[IProductGenerator]:
    generator = None
    product_type = scenario_config['type']

    if product_type in level0.RAWSxxx_10.PRODUCTS:
        generator = level0.RAWSxxx_10(logger, job_config, scenario_config)
    elif product_type in level0.Sx_RAW__0x_generator.PRODUCTS:
        generator = level0.Sx_RAW__0x_generator(logger, job_config, scenario_config)
    else:
        logger.error('No generator for product type {} in Biomass plugin'.format(product_type))
    return generator

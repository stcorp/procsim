'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass output product generator factory.
'''

from typing import Optional

from procsim import IProductGenerator

from biomass import raw_product_generator as raw
from biomass import level0_product_generator as level0


def OutputGeneratorFactory(logger, job_config, scenario_config, output_config) -> Optional[IProductGenerator]:
    generator = None
    product_type = output_config['type']

    if product_type in raw.RAWSxxx_10.PRODUCTS:
        generator = raw.RAWSxxx_10(logger, job_config, scenario_config, output_config)
    elif product_type in level0.Sx_RAW__0x_generator.PRODUCTS:
        generator = level0.Sx_RAW__0x_generator(logger, job_config, scenario_config, output_config)
    else:
        logger.error('No generator for product type {} in Biomass plugin'.format(product_type))
    return generator

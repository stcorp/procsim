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

    if product_type in ['RAWS022_10', 'RAWS023_10', 'RAWS024_10', 'RAWS025_10', 'RAWS026_10', 'RAWS027_10', 'RAWS028_10', 'RAWS035_10', 'RAWS036_10']:
        generator = level0.RAWSxxx_10(logger, job_config, scenario_config)
    elif product_type in ['Sx_RAW__0S', 'Sx_RAWP_0M', 'Sx_RAW__0M']:
        generator = level0.Sx_RAW__0x_generator(logger, job_config, scenario_config)
    else:
        logger.error('No generator for product type {} in Biomass plugin'.format(product_type))
    return generator

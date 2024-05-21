'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex output product generator factory.
'''

from typing import Optional

from procsim.core.exceptions import ScenarioError
from procsim.core.iproduct_generator import IProductGenerator

from . import aux_product_generator as aux
from . import level0_product_generator as level0
from . import level1_2_product_generator as level12
from . import raw_product_generator as raw

_GENERATORS = [
    aux.Aux,
    raw.RAW, raw.RAW_HKTM, raw.RWS_EO, raw.RWS_CAL, raw.RWS_ANC, raw.RWS_ANC_ITM, raw.RWS_ANC_OBC,
    level0.EO, level0.CAL, level0.ANC, level0.ANC_INSTTM, level0.ANC_OBC,
    level12.EO, level12.CAL,
]


def list_supported_products():
    list = []
    for gen in _GENERATORS:
        list.append(gen.PRODUCTS)  # type: ignore
    return list


def product_generator_factory(logger, job_config, scenario_config, output_config) -> Optional[IProductGenerator]:
    product_type = output_config.get('type')
    if product_type is None:
        raise ScenarioError('Output product type ("type": ...) must be specified')
    for gen in _GENERATORS:
        if product_type in gen.PRODUCTS:  # type: ignore
            if job_config is None or product_type == job_config.type:
                return gen(logger, job_config, scenario_config, output_config)
            else:
                return None
    logger.error('No generator for product \'{}\' in Flex plugin. Supported types are: {}'.format(
        product_type, list_supported_products()))
    return None

'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Flex products.
'''
from typing import List, Optional


class ProductType():
    def __init__(self, type, level, description):
        self.type: str = type
        self.level: str = level
        self.description: str = description


# Lists all FLEX products
PRODUCT_TYPES: List[ProductType] = [
    ProductType('RAW___HKTM', 'raw', 'Housekeeping Telemetry RAW product'),
    ProductType('RAW_XS_LR_', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_XS_HR1', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_XS_HR2', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_XS_OBC', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RWS_XS_OBS', 'raw', 'Complete Sliced RAW Product'),
    ProductType('RWS_XSPOBS', 'raw', 'Partial Sliced RAW Product'),

    ProductType('AUX_OBSMSK', 'aux', 'Observation Mask'),
    ProductType('AUX_GCP_DB', 'aux', 'GCP Database'),
    ProductType('AUX_PF_BC_', 'aux', 'Products Baseline'),
    ProductType('AUX_TSKTBL', 'aux', 'Processors Task Tables'),
    ProductType('AUX_L0__PF', 'aux', 'PDGS L0 Operational Processors Parameters File'),

]

RAWS_PRODUCT_TYPES = []
L1S_PRODUCTS = []
ORBPRE_PRODUCT_TYPES = []
VFRA_PRODUCT_TYPES = []


def find_product(product_type_code: str) -> Optional[ProductType]:
    '''Return ProductType for a given product_type_code, or None if not found'''
    for pt in PRODUCT_TYPES:
        if pt.type == product_type_code:
            return pt
    return None

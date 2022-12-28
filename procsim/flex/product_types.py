'''
Copyright (C) 2021 S[&]T, The Netherlands.

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

]

def find_product(product_type_code: str) -> Optional[ProductType]:
    '''Return ProductType for a given product_type_code, or None if not found'''
    for pt in PRODUCT_TYPES:
        if pt.type == product_type_code:
            return pt
    return None

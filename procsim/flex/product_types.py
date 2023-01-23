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

    ProductType('RWS_XS_OBS', 'raws', 'Complete Sliced RAW Observation Product'),
    ProductType('RWS_XSPOBS', 'raws', 'Partial Sliced RAW Observation Product'),
    ProductType('RWS_XSIOBS', 'raws', 'Intermediate Sliced RAW Observation Product'),
    ProductType('RWS_XS_CAL', 'raws', 'Complete Sliced RAW Calibration Product'),
    ProductType('RWS_XSPCAL', 'raws', 'Partial Sliced RAW Calibration Product'),
    ProductType('RWS_XSICAL', 'raws', 'Intermediate Sliced RAW Calibration Product'),
    ProductType('RWS_XS_ANC', 'raws', 'Complete Sliced RAW Ancillary Product'),
    ProductType('RWS_XSPANC', 'raws', 'Partial Sliced RAW Ancillary Product'),

    ProductType('AUX_OBSMSK', 'aux', 'Observation Mask'),
    ProductType('AUX_GCP_DB', 'aux', 'GCP Database'),
    ProductType('AUX_PF_BC_', 'aux', 'Products Baseline'),
    ProductType('AUX_TSKTBL', 'aux', 'Processors Task Tables'),
    ProductType('AUX_L0__PF', 'aux', 'PDGS L0 Operational Processors Parameters File'),

    ProductType('L0__OBS___', 'l0', 'Level-0 Observation Product'),

    ProductType('L0__DARKNP', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DARKSR', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DARKSS', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DEFDAR', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DARKOC', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DRKMTF', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DRKSTR', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__SPECSD', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__SUN___', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DEFSUN', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__MOON__', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__MOONSL', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__LINDES', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__LINSEA', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__LINSUN', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__LINDAR', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__CTE___', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__SCNVAL', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__COREG_', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__SPECEO', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__CLOUD_', 'l0', 'Level-0 Calibration Product'),

    ProductType('L0__SAT_TM', 'l0', 'Level-0 Ancillary Product'),
    ProductType('L0__NAVATT', 'l0', 'Level-0 Ancillary Product'),
    ProductType('L0__PDHUTM', 'l0', 'Level-0 Ancillary Product'),
    ProductType('L0__ICUDTM', 'l0', 'Level-0 Ancillary Product'),
    ProductType('L0__VAU_TM', 'l0', 'Level-0 Ancillary Product'),
    ProductType('L0__INSTTM', 'l0', 'Level-0 Ancillary Product'),
    ProductType('L0__TST___', 'l0', 'Level-0 Ancillary Product'),
    ProductType('L0__UNK___', 'l0', 'Level-0 Ancillary Product'),

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

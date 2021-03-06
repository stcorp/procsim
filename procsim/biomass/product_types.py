'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass products.
'''
from typing import List, Optional


class ProductType():
    def __init__(self, type, level, description):
        self.type: str = type
        self.level: str = level
        self.description: str = description


# Lists all BIOMASS products
PRODUCT_TYPES: List[ProductType] = [
    ProductType('RAW___HKTM', 'raw', 'Housekeeping Telemetry RAW product'),
    ProductType('RAW_022_10', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_023_10', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_024_10', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_025_10', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_026_10', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_027_10', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_028_10', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_035_10', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAW_036_10', 'raw', 'Science and Ancillary RAW products'),
    ProductType('RAWS022_10', 'raw', 'Sliced RAW product'),
    ProductType('RAWS023_10', 'raw', 'Sliced RAW product'),
    ProductType('RAWS024_10', 'raw', 'Sliced RAW product'),
    ProductType('RAWS025_10', 'raw', 'Sliced RAW product'),
    ProductType('RAWS026_10', 'raw', 'Sliced RAW product'),
    ProductType('RAWS027_10', 'raw', 'Sliced RAW product'),
    ProductType('RAWS028_10', 'raw', 'Sliced RAW product'),
    ProductType('RAWS035_10', 'raw', 'Sliced RAW product'),
    ProductType('RAWS036_10', 'raw', 'Sliced RAW product'),

    ProductType('S1_RAW__0S', 'l0', 'Stripmap Level-0 – Standard product'),
    ProductType('S2_RAW__0S', 'l0', 'Stripmap Level-0 – Standard product'),
    ProductType('S3_RAW__0S', 'l0', 'Stripmap Level-0 – Standard product'),
    ProductType('S1_RAWP_0M', 'l0', 'Intermediate product'),
    ProductType('S2_RAWP_0M', 'l0', 'Intermediate product'),
    ProductType('S3_RAWP_0M', 'l0', 'Intermediate product'),
    ProductType('RO_RAWP_0M', 'l0', 'Intermediate product'),
    ProductType('EC_RAWP_0M', 'l0', 'Intermediate product'),
    ProductType('EC_RAWP_0S', 'l0', 'Intermediate product'),
    ProductType('S1_RAW__0M', 'l0', 'Stripmap Level-0 - Monitoring product'),
    ProductType('S2_RAW__0M', 'l0', 'Stripmap Level-0 - Monitoring product'),
    ProductType('S3_RAW__0M', 'l0', 'Stripmap Level-0 - Monitoring product'),
    ProductType('RO_RAW__0S', 'l0', 'RX Only Mode Level-0 – Standard product'),
    ProductType('RO_RAW__0M', 'l0', 'RX Only Mode Level-0 – Monitoring product'),
    ProductType('EC_RAW__0S', 'l0', 'EXTCAL Mode Level 0 – Standard product'),
    ProductType('EC_RAW__0M', 'l0', 'EXTCAL Mode Level 0– Monitoring product'),
    ProductType('AC_RAW__0A', 'l0', 'Platform Ancillary Level-0 product (Orbit and Attitude)'),

    ProductType('CPF_L1VFRA', 'l1fvra', 'L1 Virtual Frame'),

    ProductType('S1_SCS__1S', 'l1', 'Stripmap L1 Single look Complex Slant range – Standard product'),
    ProductType('S2_SCS__1S', 'l1', 'Stripmap L1 Single look Complex Slant range – Standard product'),
    ProductType('S3_SCS__1S', 'l1', 'Stripmap L1 Single look Complex Slant range – Standard product'),
    ProductType('S1_DGM__1S', 'l1', 'Stripmap L1 Multilook Detected and Ground projected – Standard product'),
    ProductType('S2_DGM__1S', 'l1', 'Stripmap L1 Multilook Detected and Ground projected – Standard product'),
    ProductType('S3_DGM__1S', 'l1', 'Stripmap L1 Multilook Detected and Ground projected – Standard product'),
    ProductType('S1_SCS__1M', 'l1', 'Stripmap L1 Single look Complex Slant range - Monitoring Product'),
    ProductType('S2_SCS__1M', 'l1', 'Stripmap L1 Single look Complex Slant range - Monitoring Product'),
    ProductType('S3_SCS__1M', 'l1', 'Stripmap L1 Single look Complex Slant range - Monitoring Product'),
    ProductType('S1_STA__1S', 'l1', 'Stripmap L1 Coregistered stack – Standard product'),
    ProductType('S2_STA__1S', 'l1', 'Stripmap L1 Coregistered stack – Standard product'),
    ProductType('S3_STA__1S', 'l1', 'Stripmap L1 Coregistered stack – Standard product'),
    ProductType('S1_STA__1M', 'l1', 'Stripmap L1 Coregistered stack – Monitoring product'),
    ProductType('S2_STA__1M', 'l1', 'Stripmap L1 Coregistered stack – Monitoring product'),
    ProductType('S3_STA__1M', 'l1', 'Stripmap L1 Coregistered stack – Monitoring product'),
    ProductType('RO_SCS__1S', 'l1', 'RX Only L1 Single look Complex Slant range – Standard product'),

    ProductType('FP_GN__L2A', 'l2a', 'L2a Ground Notched product: geocoded, ground cancelled, calibrated and multilooked image product'),
    ProductType('FP_FD__L2A', 'l2a', 'L2a Forest Disturbance product: covariance of ground cancelled image'),
    ProductType('FP_FH__L2A', 'l2a', 'L2a Forest Height product'),

    ProductType('AUX_ATT___', 'aux', 'Attitude Product'),
    ProductType('AUX_CAL_AB', 'aux', 'Calibration Parameters for L2-Above Ground Biomass Processor Product'),
    ProductType('AUX_ERP___', 'aux', 'Earth Rotation Parameters Product'),
    ProductType('AUX_GMF___', 'aux', 'Geomagnetic Field Product'),
    ProductType('AUX_INS___', 'aux', 'Instrument Parameter Product'),
    ProductType('AUX_ORB___', 'aux', 'Orbit Product'),
    ProductType('AUX_PP0___', 'aux', 'Processing Parameters for L0-Processor Product'),
    ProductType('AUX_PP1___', 'aux', 'Processing Parameters for L1-Processor Product'),
    ProductType('AUX_PP2_2A', 'aux', 'Processing Parameters for L2a-Processor Product'),
    ProductType('AUX_PP2_FH', 'aux', 'Processing Parameters for L2-Forest Height Processor Product'),
    ProductType('AUX_PP2_FD', 'aux', 'Processing Parameters for L2-Forest Disturbance Processor Product'),
    ProductType('AUX_PP2_AB', 'aux', 'Processing Parameters for L2-Above Ground Biomass Processor Product'),
    ProductType('AUX_PP3___', 'aux', 'Processing Parameters for L3 Processor Product'),
    ProductType('AUX_PPS___', 'aux', 'Processing Parameters for Stack-Processor Product'),
    ProductType('AUX_TEC___', 'aux', 'Total Electron Content Product'),

    ProductType('MPL_ORBREF', 'mpl', 'Reference Orbit File'),
    ProductType('MPL_REFAUX', 'mpl', 'Reference Orbit Auxiliary File, times and orbit numbers'),
    ProductType('MPL_ORBPRE', 'mpl', 'Reference Orbit File, orbit state vectors'),
]

RAWS_PRODUCT_TYPES: List[str] = [
    'RAWS022_10',
    'RAWS023_10',
    'RAWS024_10',
    'RAWS025_10',
    'RAWS026_10',
    'RAWS027_10',
    'RAWS028_10',
    'RAWS035_10',
    'RAWS036_10',
]


L1S_PRODUCTS: List[str] = [
    'S1_SCS__1S', 'S2_SCS__1S', 'S3_SCS__1S',
    'S1_DGM__1S', 'S2_DGM__1S', 'S3_DGM__1S',
    'S1_STA__1S', 'S2_STA__1S', 'S3_STA__1S'
]

ORBPRE_PRODUCT_TYPES: List[str] = ['MPL_ORBPRE']

VFRA_PRODUCT_TYPES: List[str] = ['CPF_L1VFRA']


def find_product(product_type_code: str) -> Optional[ProductType]:
    '''Return ProductType for a given product_type_code, or None if not found'''
    for pt in PRODUCT_TYPES:
        if pt.type == product_type_code:
            return pt
    return None

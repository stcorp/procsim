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

    ProductType('RWS_LR_OBS', 'raws', 'Complete Sliced RAW Observation Product'),
    ProductType('RWS_LRPOBS', 'raws', 'Partial Sliced RAW Observation Product'),
    ProductType('RWS_LRIOBS', 'raws', 'Intermediate Sliced RAW Observation Product'),
    ProductType('RWS_H1_OBS', 'raws', 'Complete Sliced RAW Observation Product'),
    ProductType('RWS_H1POBS', 'raws', 'Partial Sliced RAW Observation Product'),
    ProductType('RWS_H1IOBS', 'raws', 'Intermediate Sliced RAW Observation Product'),
    ProductType('RWS_H2_OBS', 'raws', 'Complete Sliced RAW Observation Product'),
    ProductType('RWS_H2POBS', 'raws', 'Partial Sliced RAW Observation Product'),
    ProductType('RWS_H2IOBS', 'raws', 'Intermediate Sliced RAW Observation Product'),

    ProductType('RWS_LR_CAL', 'raws', 'Complete Sliced RAW Calibration Product'),
    ProductType('RWS_LRPCAL', 'raws', 'Partial Sliced RAW Calibration Product'),
    ProductType('RWS_LRICAL', 'raws', 'Intermediate Sliced RAW Calibration Product'),
    ProductType('RWS_H1_CAL', 'raws', 'Complete Sliced RAW Calibration Product'),
    ProductType('RWS_H1PCAL', 'raws', 'Partial Sliced RAW Calibration Product'),
    ProductType('RWS_H1ICAL', 'raws', 'Intermediate Sliced RAW Calibration Product'),
    ProductType('RWS_H2_CAL', 'raws', 'Complete Sliced RAW Calibration Product'),
    ProductType('RWS_H2PCAL', 'raws', 'Partial Sliced RAW Calibration Product'),
    ProductType('RWS_H2ICAL', 'raws', 'Intermediate Sliced RAW Calibration Product'),

    ProductType('RWS_XS_ANC', 'raws', 'Complete Sliced RAW Ancillary Product'),
    ProductType('RWS_XSPANC', 'raws', 'Partial Sliced RAW Ancillary Product'),

    ProductType('RWS_LR_VAU', 'raws', 'Complete VAU_TM RAW slice for LR Sensor'),
    ProductType('RWS_H1_VAU', 'raws', 'Complete VAU_TM RAW slice for HR1 Sensor'),
    ProductType('RWS_H2_VAU', 'raws', 'Complete VAU_TM RAW slice for HR2 Sensor'),
    ProductType('RWS_LRPVAU', 'raws', 'Partial VAU_TM RAW slice for LR sensor'),
    ProductType('RWS_H1PVAU', 'raws', 'Partial VAU_TM RAW slice for HR1 sensor'),
    ProductType('RWS_H2PVAU', 'raws', 'Partial VAU_TM RAW slice for HR2 sensor'),

    ProductType('RWS_XS_OBC', 'raws', 'Complete OBC RAW slice'),
    ProductType('RWS_XSPOBC', 'raws', 'Partial OBC RAW slice'),

    ProductType('RWS_XS_ITM', 'raws', 'Complete INST TM RAW slice'),
    ProductType('RWS_XSPITM', 'raws', 'Partial INST TM RAW slice'),

    ProductType('AUX_GCP_DB', 'aux', 'Ground Control Point Database'),

    ProductType('CFG_TSKTBL', 'aux', 'Processors Task Tables'),
    ProductType('CFG_PF_BC_', 'aux', 'Products Baseline Configuration'),
    ProductType('CFG_L0__PF', 'aux', 'PDGS L0 Operational Processor Parameters File'),

    ProductType('L0__OBS___', 'l0', 'Level-0 FLORIS Instrument Measurement Data Product'),
    ProductType('L0__OBSMON', 'l0', 'Level-0 FLORIS Monitoring Instrument Measurement Data Product'),

    ProductType('L0__DARKNP', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DARKSR', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DEFDAR', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DARKOC', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DRKMTF', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DRKSTR', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__SUN___', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__DEFSUN', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__MOON__', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__MOONSL', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__LINDES', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__LINSEA', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__LINSUN', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__LINDAR', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__CTE___', 'l0', 'Level-0 Calibration Product'),
    ProductType('L0__CLOUD_', 'l0', 'Level-0 Calibration Product'),

    ProductType('L0__SAT_TM', 'l0', 'Level-0 Satellite Telemetry Data Product'),
    ProductType('L0__NAVATT', 'l0', 'Level-0 Navigation & Attitude Data Product'),
    ProductType('L0__PDHUTM', 'l0', 'Level-0 Nom/Red PDHU TM(3,25) Product'),
    ProductType('L0__ICUDTM', 'l0', 'Level-0 Duplicated ICU TM(3,25) Product'),
    ProductType('L0__INSTTM', 'l0', 'Level-0 Instrument Telemetry Data Product'),

    ProductType('L0__VAU_TM', 'l0', 'Level-0 Ancillary Product'),

    ProductType('L0__TST___', 'l0', 'Level-0 Test Data Product'),
    ProductType('L0__WRN___', 'l0', 'Level-0 Warning Data Product'),
    ProductType('L0__INV___', 'l0', 'Level-0 Invalid Data Product'),
    ProductType('L0__UNK___', 'l0', 'Level-0 Unknown Data Product'),

    ProductType('AUX_IERS_B', 'aux', 'Auxiliary Product'),
    ProductType('AUX_MET_A_', 'aux', 'Auxiliary Product'),
    ProductType('AUX_MET_F_', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCPOIV', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCTEM_', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCCHDC', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCCHRF', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCCACF', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCCHNL', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCCASI', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCCHST', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCCHSD', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCFOCP', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCCALN', 'aux', 'Auxiliary Product'),
    ProductType('AUX_CCGAIN', 'aux', 'Auxiliary Product'),
    ProductType('AUX_IERS_A', 'aux', 'Auxiliary Product'),

    ProductType('L1B_OBS___', 'l1', 'Level-1 Observation Product'),

    ProductType('ANC_ROTLOS', 'l1', 'Level-1 Ancillary Product'),
    ProductType('ANC_ATTRES', 'l1', 'Level-1 Ancillary Product'),
    ProductType('ANC_ORBRES', 'l1', 'Level-1 Ancillary Product'),

    ProductType('RAC_DARKNP', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_DARKSR', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_DEFDAR', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_DEFSTR', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_DARKOC', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_DRKMTF', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_DRKSTR', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_SUN___', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_DEFSUN', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_MOON__', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_MOONSL', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_LINDES', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_LINSEA', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_LINSUN', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_LINDAR', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_CTE___', 'l1', 'Level-1 Calibration Product'),
    ProductType('RAC_CLOUD_', 'l1', 'Level-1 Calibration Product'),

    ProductType('SPC_SPECEO', 'l1', 'Level-1 Calibration Product'),

    # Level 1C/2 products
    ProductType('L1C_FLORIS', 'l1c', 'Level-1C Observation Product'),
    ProductType('L1C_FLXSYN', 'l1c', 'Level-2 Observation Product'),
    ProductType('L1C_OBS___', 'l1c', 'Level-2 Observation Product'),

    ProductType('L2__OBS___', 'l2', 'Level-2 Observation Product'),
    ProductType('L2__FLORIS', 'l2', 'Level-1 Observation Product'),
]


def find_product(product_type_code: str) -> Optional[ProductType]:
    '''Return ProductType for a given product_type_code, or None if not found'''
    for pt in PRODUCT_TYPES:
        if pt.type == product_type_code:
            return pt
    return None

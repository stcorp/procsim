'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Level 2a product generators, format according to
- BIO-ESA-EOPG-EEGS-TN-0115 'L2a Product Guidelines'.
- BIO-ESA-EOPG-EEGS-TN-0046 'BIOMASS Production Model'.
'''
import os
from typing import List, Tuple

from procsim.core.exceptions import ScenarioError

from . import product_generator

_HDR_PARAMS = [
    ('swath', 'sensor_swath', 'str'),
    ('operational_mode', 'sensor_mode', 'str'),
    ('footprint_polygon', 'footprint_polygon', 'str'),
    ('center_points', 'center_points', 'str'),
]
_ACQ_PARAMS = [
    ('mission_phase', 'mission_phase', 'str'),
    ('data_take_id', 'data_take_id', 'int'),
    ('global_coverage_id', 'global_coverage_id', 'str'),
    ('major_cycle_id', 'major_cycle_id', 'str'),
    ('track_nr', 'track_nr', 'str'),
]


class Level2a(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating dummy Biomass level 2a products.

    The l2a processor input is an interferometric stack, with up to 3/7 L1c
    (Sx_STA__1S) products for a given frame. Additionally aux products:
    AUX_PP2_2A (processing parameters) and AUX_DEM (Copernicus DEM).
    '''
    PRODUCTS = ['AGB_GN_L2A', 'FD_COV_L2A', 'FH_COH_L2A',
                'FP_VBG_L2A', 'FP_FD__L2A', 'FP_FH__L2A', 'FP_ACM_L2A']

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)

    def get_params(self) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        gen, hdr, acq = super().get_params()
        return gen, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def generate_output(self):
        super().generate_output()

        # Sanity check
        if self._hdr.begin_position is None or self._hdr.end_position is None:
            raise ScenarioError('Begin/end position must be set')

        # If not read from an input product, use begin/end position as starting point
        if self._hdr.validity_start is None:
            self._hdr.validity_start = self._hdr.begin_position
        if self._hdr.validity_stop is None:
            self._hdr.validity_stop = self._hdr.end_position

        self._hdr.product_type = self._resolve_wildcard_product_type()

        name_gen = self._create_name_generator(self._hdr)
        dir_name = name_gen.generate_path_name()
        self._hdr.set_product_filename(dir_name)
        self._logger.info('Create {}'.format(dir_name))

        # Full specs are not known yet. For now, generate MPH and one data file.
        base_path = os.path.join(self._output_path, dir_name)
        print('here. make {}'.format(base_path))
        os.makedirs(base_path, exist_ok=True)
        file_name = os.path.join(base_path, name_gen.generate_mph_file_name())
        self._hdr.write(file_name)
        file_name = os.path.join(base_path, name_gen.generate_binary_file_name())
        self._generate_bin_file(file_name, self._size_mb)


class Level2b(product_generator.ProductGeneratorBase):
    """
    This class implements the ProductGeneratorBase and is responsible for
    generating dummy Biomass level 2b products.

    L2 products describe 'tiles' of 5x5 degrees. The tile based processing has
    as input all L2a products intersecting the tile.
    """
    pass

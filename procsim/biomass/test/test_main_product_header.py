'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
from ssl import get_default_verify_paths
import tempfile
import os
import unittest

from biomass.main_product_header import MainProductHeader

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def get_l1_test_mph():
    mph = MainProductHeader()

    # Derived from XML by hand...
    mph._eop_identifier = 'BIO_S2_SCS__1S_20230101T120000_20230101T120021_I_G03_M03_C03_T131_F155_01_ACZ976'
    mph._begin_position = mph._validity_start = datetime.datetime(2023, 1, 1, 12, 0)
    mph._time_position = mph._end_position = mph._validity_stop = datetime.datetime(2023, 1, 1, 12, 0, 21)
    mph.set_product_type('S2_SCS__1S', 1)
    mph.product_status = 'ARCHIVED'
    mph.doi = 'DOI'
    mph.acquisition_type = 'NOMINAL'
    mph.set_processing_parameters('L1 Processor', '1.0', datetime.datetime(2023, 1, 1, 12, 12, 53))
    mph.processing_centre_code = 'ESR'
    mph.auxiliary_ds_file_names = ['AUX_ORB_Filename', 'AUX_ATT_Filename', 'AUX_GMF_Filename', 'AUX_INS_Filename',
                                   'AUX_TEC_Filename', 'AUX_PP1_Filename']
    mph._processing_mode = 'OPERATIONAL'
    mph.biomass_source_product_ids = ['BIO_S2_RAW__0S_20230101T120000_20230101T120203_I_G03_M03_C03_T131_F026']

    mph.reference_documents = ['BIOMASS L1 PRODUCT FORMAT SPECIFICATION', 'BIOMASS L1 PRODUCT FORMAT DEFINITION']

    mph._platform_shortname = 'Biomass'
    mph._sensor_name = 'P-SAR'
    mph._sensor_type = 'RADAR'
    mph.sensor_mode = 'SM'
    mph.sensor_swath = 'S2'

    mph.browse_ref_id = 'EPSG:4326'
    mph.browse_image_filename = './preview/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_ql.png'
    mph.footprint_polygon = '-8.015716 -63.764648 -6.809171 -63.251038 -6.967323 -62.789612 -8.176149 -63.278503 -8.015716 -63.764648'
    mph.center_points = '-7.492090 -63.27095'

    mph.tai_utc_diff = 37
    mph.incomplete_l1_frame = False
    mph.partial_l1_frame = False

    acq = mph.acquisitions[0]
    acq.orbit_number = 1
    acq.last_orbit_number = 1
    acq.orbit_direction = 'ASCENDING'
    acq.track_nr = 131
    acq.slice_frame_nr = 155
    acq.mission_phase = 'INTERFEROMETRIC'
    acq.instrument_config_id = 1
    acq.data_take_id = 1234
    acq.anx_date = datetime.datetime(2023, 1, 1, 10, 54, 37, 264000)
    acq.start_time = 3922736
    acq.completion_time = 3943736
    acq.instrument_config_id = 1
    acq.orbit_drift_flag = False
    acq.global_coverage_id = '3'
    acq.major_cycle_id = '3'
    acq.repeat_cycle_id = '3'

    return 'bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_01_acz976.xml', mph


class MphTest(unittest.TestCase):
    def testParse(self):
        filename, ref_mph = get_l1_test_mph()
        mph = MainProductHeader()
        mph.parse(os.path.join(THIS_DIR, filename))
        self.assertEqual(mph, ref_mph)

    def testCreateParse(self):
        filename, _ = get_l1_test_mph()
        mph = MainProductHeader()
        mph.parse(os.path.join(THIS_DIR, filename))
        outfile_path = tempfile.mkstemp(suffix='mph.xml', dir=THIS_DIR)[1]
        try:
            mph.write(outfile_path)
            mph2 = MainProductHeader()
            mph2.parse(outfile_path)
        finally:
            # NOTE: To retain the tempfile if the test fails, remove
            # the try-finally clauses
            os.remove(outfile_path)

        self.assertEqual(mph, mph2)
        self.assertEqual(mph.acquisitions, mph2.acquisitions)


if __name__ == '__main__':
    unittest.main()

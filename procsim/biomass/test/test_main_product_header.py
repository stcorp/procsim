'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import List, Set, Tuple, Type, Union
from xml.etree import ElementTree as et

from procsim.biomass.main_product_header import (MainProductHeader, bio, eop,
                                                 om, ows, xlink)
from procsim.biomass.mpl_product_generator import Mpl
from procsim.biomass.raw_product_generator import (RAW_xxx_10,
                                                   RawProductGeneratorBase,
                                                   RAWSxxx_10)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

TEST_DIR = os.path.join(THIS_DIR, 'tmp')


class _Logger:
    def __init__(self):
        self.count = 0

    def debug(self, *args, **kwargs):
        # print(*args, **kwargs)
        pass

    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        print(*args, **kwargs)


def assertMPHMatchesProductRecursive(directory_path: str) -> None:
    '''Check whether product files and MPHs correspond in all Biomass product directories.'''
    product_directories = list(Path(directory_path).glob('**/BIO_*[!.zip]'))
    for product_directory in product_directories:
        assertMPHMatchesProduct(product_directory)


def assertMPHMatchesProduct(product_folder_path: Union[str, Path]) -> None:
    '''Check whether the product files in a folder correspond with those in the MPH.'''

    mph_filename = (os.path.basename(product_folder_path)).lower() + '.xml'
    xml = et.parse(os.path.join(product_folder_path, mph_filename))

    # Check validity of first "file" in product list, which should be the name of the folder.
    product_information = xml.getroot().findall(om + 'result/' + eop + 'EarthObservationResult/' + eop + 'product/' + bio + 'ProductInformation')
    assert len(product_information) > 1, 'MPH does not contain product name and at least one product file.'
    product_service_reference = product_information[0].find(eop + 'fileName/' + ows + 'ServiceReference')
    assert product_service_reference is not None
    product_name = product_service_reference.get(xlink + 'href')
    assert product_name == os.path.basename(product_folder_path), 'Product folder name and product name in MPH do not match.'

    # Gather information of all files in the product.
    files_in_mph: Set[Tuple[str, int]] = set()
    representations_in_mph: Set[str] = set()
    for product_info in product_information[1:]:
        service_reference = product_info.find(eop + 'fileName/' + ows + 'ServiceReference')
        assert service_reference is not None
        filename = service_reference.get(xlink + 'href')
        assert filename is not None
        size_element = product_info.find(eop + 'size')
        assert size_element is not None and size_element.text is not None
        size = int(size_element.text)

        files_in_mph.add((filename, size))

        representation_element = product_info.find(bio + 'rds')
        if representation_element is not None and representation_element.text is not None:
            representations_in_mph.add(representation_element.text)
        else:
            assert os.path.splitext(filename)[1] != '.xml', f'Found xml file {filename} without representation.'

    # Gather information of files actually in the directory and check if these correspond to MPH.
    files_in_directory: Set[Tuple[str, int]] = set()
    file_paths = list(Path(product_folder_path).rglob('*.*'))  # Assume that all files and only files contain a period in their name.
    file_paths.remove(Path(os.path.join(product_folder_path, mph_filename)))
    for file_path in file_paths:
        file_size = os.stat(file_path).st_size
        files_in_directory.add(('./' + os.path.relpath(file_path, product_folder_path), file_size))

    # Check whether directory files are listed in MPH.
    for dir_file in files_in_directory:
        assert dir_file in files_in_mph or dir_file[0] in representations_in_mph, f'Found {dir_file} in directory {product_folder_path} but not in MPH.'
    # Check whether MPH files are in directory.
    for mph_file in files_in_mph:
        assert mph_file in files_in_directory, f'Found file {mph_file} in MPH but not in directory {product_folder_path}.'
    filenames_in_directory = {file[0] for file in files_in_directory}
    for mph_represenation in representations_in_mph:
        assert mph_represenation in filenames_in_directory, f'Found representation {mph_represenation} in MPH but not in directory {product_folder_path}.'


def get_l1_test_mph():
    mph = MainProductHeader()

    # Derived from XML by hand...
    mph.eop_identifier = 'BIO_S2_SCS__1S_20230101T120000_20230101T120021_I_G03_M03_C03_T131_F155_01_ACZ976'
    mph.begin_position = mph.validity_start = datetime.datetime(2023, 1, 1, 12, 0)
    mph.time_position = mph.end_position = mph.validity_stop = datetime.datetime(2023, 1, 1, 12, 0, 21)
    mph.product_type = 'S2_SCS__1S'
    mph.product_baseline = 1
    mph.product_status = 'ARCHIVED'
    mph.doi = 'DOI'
    mph.acquisition_type = 'NOMINAL'
    mph.set_processing_parameters('L1 Processor', '1.0')
    mph.processing_date = datetime.datetime(2023, 1, 1, 12, 12, 53)
    mph.processing_centre_code = 'ESR'
    mph.auxiliary_ds_file_names = ['AUX_ORB_Filename', 'AUX_ATT_Filename', 'AUX_GMF_Filename', 'AUX_INS_Filename',
                                   'AUX_TEC_Filename', 'AUX_PP1_Filename']
    mph.processing_mode = 'OPERATIONAL'
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

    mph.products = [
        {'file_name': 'BIO_S2_SCS__1S_20230101T120000_20230101T120021_I_G03_M03_C03_T131_F155_01_ACZ976'},
        {'file_name': './annotation/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_annot.xml',
         'representation': './schema/bio_l1_product.xsd',
         'size': 1721590},
        {'file_name': './annotation/calibration/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_cal.xml',
         'representation': './schema/bio_l1_cal.xsd',
         'size': 1024231},
        {'file_name': './annotation/calibration/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_noise.dat',
         'representation': None,
         'size': 101940516},
        {'file_name': './annotation/calibration/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_ant.dat',
         'representation': None,
         'size': 101940516},
        {'file_name': './annotation/navigation/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_att.xml',
         'representation': './schema/bio_l1_attitude.xsd',
         'size': 1339130},
        {'file_name': './annotation/navigation/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_orb.xml',
         'representation': './schema/bio_l1_orbit.xsd',
         'size': 1258937},
        {'file_name': './annotation/geometry/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_geoloc.xml',
         'representation': './schema/bio_l1_geoloc.xsd',
         'size': 2000},
        {'file_name': './annotation/geometry/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_geoloc.tiff',
         'representation': None,
         'size': 976000},
        {'file_name': './measurement/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_i_hh.tiff',
         'representation': None,
         'size': 407762064},
        {'file_name': './measurement/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_i_hv.tiff',
         'representation': None,
         'size': 407762064},
        {'file_name': './measurement/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_i_vv.tiff',
         'representation': None,
         'size': 407762064},
        {'file_name': './measurement/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_i_vh.tiff',
         'representation': None,
         'size': 407762064},
        {'file_name': './measurement/ionosphere/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_iono.tiff',
         'representation': None,
         'size': 50970258},
        {'file_name': './measurement/rfi/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_rfi.tiff',
         'representation': None,
         'size': 6796034},
        {'file_name': './preview/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_ql.png',
         'representation': None,
         'size': 290816},
        {'file_name': './preview/bio_s2_scs__1s_20230101t120000_20230101t120021_i_g03_m03_c03_t131_f155_map.kml',
         'representation': None,
         'size': 1016}
    ]

    acq = mph.acquisitions[0]
    acq.orbit_number = 1
    acq.last_orbit_number = 1
    acq.orbit_direction = 'ASCENDING'
    acq.track_nr = '131'
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

    def testFilesInMPHFromRAW(self):
        raw_generator_classes: List[Type[RawProductGeneratorBase]] = [RAW_xxx_10, RAWSxxx_10]
        for raw_generator_class in raw_generator_classes:
            config = {
                'anx': ['2021-01-31T22:47:21.765Z'],
                'output_path': TEST_DIR,
                'type': 'RAWS025_10',
                'processor_name': 'unittest',
                'processor_version': '01.01',
                'baseline': 10,
                'acquisition_date': '2021-01-01T00:00:00.000Z',
                'acquisition_station': 'unittest',
            }
            raw_gen = raw_generator_class(_Logger(), None, config, config)

            # Normally we read this from input products, but now we set it by hand.
            begin = datetime.datetime(2021, 2, 1, 0, 24, 32, 0)
            end = datetime.datetime(2021, 2, 1, 0, 29, 32, 0)
            raw_gen._hdr.validity_start = raw_gen._hdr.begin_position = begin
            raw_gen._hdr.validity_stop = raw_gen._hdr.end_position = end

            raw_gen.read_scenario_parameters()
            raw_gen.generate_output()

            assertMPHMatchesProductRecursive(TEST_DIR)

            # Header products should contain two elements: folder and file.
            self.assertEqual(len(raw_gen._hdr.products), 2)
            self.assertEqual(raw_gen._hdr.products[1]['size'], 0)
            self.assertEqual(raw_gen._hdr.products[1]['representation'], None)

            shutil.rmtree(TEST_DIR)


if __name__ == '__main__':
    unittest.main()

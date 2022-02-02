'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import tempfile
from typing import Dict, List
import unittest

from procsim.biomass.product_generator import ProductGeneratorBase
from procsim.biomass.raw_product_generator import RAWSxxx_10
from procsim.core.exceptions import ScenarioError
from procsim.core.job_order import JobOrderInput, JobOrderOutput
from procsim.core.logger import Logger

TEST_DIR = tempfile.TemporaryDirectory()


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


ORBPRE_DATA = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<Earth_Explorer_File schemaVersion="2.1" xmlns="http://eop-cfi.esa.int/CFI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://eop-cfi.esa.int/CFI http://eop-cfi.esa.int/CFI/EE_CFI_SCHEMAS/EO_OPER_MPL_ORBPRE_0201.XSD">

  <Earth_Explorer_Header>
    <Fixed_Header>
      <File_Name>BIO_TEST_MPL_ORBPRE_20211209T130000_20211209T180000_0001</File_Name>
      <File_Description>FOS Predicted Orbit File</File_Description>
      <Notes></Notes>
      <Mission>BIOMASS</Mission>
      <File_Class>TEST</File_Class>
      <File_Type>MPL_ORBPRE</File_Type>
      <Validity_Period>
        <Validity_Start>UTC=2021-12-09T13:00:00</Validity_Start>
        <Validity_Stop>UTC=2021-12-09T18:00:00</Validity_Stop>
      </Validity_Period>
      <File_Version>0001</File_Version>
      <Source>
        <System>FOS</System>
        <Creator>NAPEOS</Creator>
        <Creator_Version>3.0</Creator_Version>
        <Creation_Date>UTC=2021-12-09T13:00:00.000000</Creation_Date>
      </Source>
    </Fixed_Header>
    <Variable_Header>
      <Ref_Frame>EARTH_FIXED</Ref_Frame>
      <Time_Reference>UTC</Time_Reference>
    </Variable_Header>
  </Earth_Explorer_Header>

  <Data_Block type="xml">
    <List_of_OSVs count="3">
      <OSV>
        <TAI>TAI=2021-12-09T13:00:00.000000</TAI>
        <UTC>UTC=2021-12-09T13:00:00.000000</UTC>
        <UT1>UT1=2021-12-09T13:00:00.000000</UT1>
        <Absolute_Orbit>+00000</Absolute_Orbit>
        <X unit="m">+8000000.000</X>
        <Y unit="m">-0000001.000</Y>
        <Z unit="m">+0000001.000</Z>
        <VX unit="m/s">-0001.000000</VX>
        <VY unit="m/s">-2000.000000</VY>
        <VZ unit="m/s">+7000.000000</VZ>
        <Quality>0000000000000</Quality>
      </OSV>
      <OSV>
        <TAI>TAI=2021-12-09T15:30:00.000000</TAI>
        <UTC>UTC=2021-12-09T15:30:00.000000</UTC>
        <UT1>UT1=2021-12-09T15:30:00.000000</UT1>
        <Absolute_Orbit>+00000</Absolute_Orbit>
        <X unit="m">+8000000.000</X>
        <Y unit="m">-0000001.000</Y>
        <Z unit="m">+0000001.000</Z>
        <VX unit="m/s">-0001.000000</VX>
        <VY unit="m/s">-2000.000000</VY>
        <VZ unit="m/s">+7000.000000</VZ>
        <Quality>0000000000000</Quality>
      </OSV>
      <OSV>
        <TAI>TAI=2021-12-09T18:00:00.000000</TAI>
        <UTC>UTC=2021-12-09T18:00:00.000000</UTC>
        <UT1>UT1=2021-12-09T18:00:00.000000</UT1>
        <Absolute_Orbit>+00000</Absolute_Orbit>
        <X unit="m">+8000000.000</X>
        <Y unit="m">-0000001.000</Y>
        <Z unit="m">+0000001.000</Z>
        <VX unit="m/s">-0001.000000</VX>
        <VY unit="m/s">-2000.000000</VY>
        <VZ unit="m/s">+7000.000000</VZ>
        <Quality>0000000000000</Quality>
      </OSV>
    </List_of_OSVs>
  </Data_Block>

</Earth_Explorer_File>
'''


class ANXTest(unittest.TestCase):

    def assert_orbpre_anx_times(self, anx_list: List[datetime.datetime]) -> None:
        self.assertEqual(len(anx_list), 3)
        self.assertEqual(anx_list[0], datetime.datetime(2021, 12, 9, 13, 0, 0))
        self.assertEqual(anx_list[1], datetime.datetime(2021, 12, 9, 15, 30, 0))
        self.assertEqual(anx_list[2], datetime.datetime(2021, 12, 9, 18, 0, 0))

    def create_no_anx_config(self) -> Dict:
        return {
            'output_path': TEST_DIR,
            'type': 'RAWS025_10',
            'processor_name': 'unittest',
            'processor_version': '01.01',
            'baseline': 10,
            'acquisition_date': '2021-01-01T00:00:00.000Z',
            'acquisition_station': 'unittest',
            'num_isp': 387200,
            'num_isp_erroneous': 0,
            'num_isp_corrupt': 0,
            'num_tf': 387200,
            'num_tf_erroneous': 0,
            'num_tf_corrupt': 0,
            'zip_output': False,
            'slice_overlap_start': 5.0,
            'slice_overlap_end': 7.0,
            'slice_minimum_duration': 15.0
        }

    def test_orbit_prediction_parser(self):
        logger = Logger('', '', '', Logger.LEVELS, [])
        job_order = JobOrderOutput()
        job_order.type = 'test'
        job_order.dir = 'test'
        job_order.baseline = 1
        job_order.file_name_pattern = 'test'
        job_order.toi_start = datetime.datetime.now()
        job_order.toi_stop = datetime.datetime.now()
        config = {
            'type': 'test',
        }
        base = ProductGeneratorBase(logger, job_order, config, config)
        self.assertTrue(len(base._anx_list) == 0)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(ORBPRE_DATA.encode('utf-8'))
            orbpre_path = f.name

        self.assertEqual(base._anx_list, [])

        base._parse_orbit_prediction_file(orbpre_path)

        self.assert_orbpre_anx_times(base._anx_list)

    def test_no_anx(self):
        '''Try to create a generator with no ANX information at all. This should fail once it tries to generate something.'''
        config = self.create_no_anx_config()
        gen = RAWSxxx_10(logger=_Logger(), job_config=None, scenario_config=config, output_config=config)
        gen._enable_slicing = True
        with self.assertRaises(ScenarioError):
            gen.generate_output()

    def test_anx_from_orbpre(self):
        '''Create a generator without ANX information in the scenario, but with a suitable orbit prediction file.'''
        # Create generator with no ANX information in the scenario, but with an orbit prediction file to parse.
        config = self.create_no_anx_config()
        gen = RAWSxxx_10(logger=_Logger(), job_config=None, scenario_config=config, output_config=config)

        # Create orbit prediction file.
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(ORBPRE_DATA.encode('utf-8'))
            orbpre_path = f.name

        job_order_input = JobOrderInput()
        job_order_input.file_names.append(orbpre_path)
        job_order_input.file_type = 'MPL_ORBPRE'
        job_order_input.id = ''
        job_order_input.alternative_input_id = ''
        gen.parse_inputs([job_order_input])

        self.assert_orbpre_anx_times(gen._anx_list)

    def test_anx_from_scenario(self):
        '''Create a generator with ANX information from a scenario only.'''
        config = self.create_no_anx_config()
        config['anx'] = [
            "2017-03-02T06:05:51.514000Z",
            "2017-03-02T07:44:02.496000Z"
        ]
        gen = RAWSxxx_10(logger=_Logger(), job_config=None, scenario_config=config, output_config=config)

        self.assertGreater(len(gen._anx_list), 0)
        self.assertEqual(gen._anx_list[0], datetime.datetime(2017, 3, 2, 6, 5, 51, 514000))
        self.assertEqual(gen._anx_list[1], datetime.datetime(2017, 3, 2, 7, 44, 2, 496000))

    def test_anx_from_scenario_and_orbpre(self):
        '''Create a generator with ANX information from a scenario and an orbit prediction file. The scenario should take precedence.'''
        # Create generator with no ANX information in the scenario, but with an orbit prediction file to parse.
        config = self.create_no_anx_config()
        config['anx'] = [
            "2017-03-02T06:05:51.514000Z",
            "2017-03-02T07:44:02.496000Z"
        ]
        gen = RAWSxxx_10(logger=_Logger(), job_config=None, scenario_config=config, output_config=config)

        # Create orbit prediction file.
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(ORBPRE_DATA.encode('utf-8'))
            orbpre_path = f.name

        job_order_input = JobOrderInput()
        job_order_input.file_names.append(orbpre_path)
        job_order_input.file_type = 'MPL_ORBPRE'
        job_order_input.id = ''
        job_order_input.alternative_input_id = ''
        gen.parse_inputs([job_order_input])

        self.assertGreater(len(gen._anx_list), 0)
        self.assertEqual(gen._anx_list[0], datetime.datetime(2017, 3, 2, 6, 5, 51, 514000))
        self.assertEqual(gen._anx_list[1], datetime.datetime(2017, 3, 2, 7, 44, 2, 496000))


if __name__ == '__main__':
    unittest.main()

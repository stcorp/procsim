'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import os
import tempfile
import unittest

from procsim.biomass.product_generator import ProductGeneratorBase
from procsim.core.job_order import JobOrderOutput
from procsim.core.logger import Logger

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')


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


class ProductGeneratorBaseTest(unittest.TestCase):

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

        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(ORBPRE_DATA.encode('utf-8'))
        path = f.name
        f.close()

        self.assertEqual(base._anx_list, [])

        base._parse_orbit_prediction_file(path)

        self.assertEqual(len(base._anx_list), 3)
        self.assertEqual(base._anx_list[0], datetime.datetime(2021, 12, 9, 13, 0, 0))
        self.assertEqual(base._anx_list[1], datetime.datetime(2021, 12, 9, 15, 30, 0))
        self.assertEqual(base._anx_list[2], datetime.datetime(2021, 12, 9, 18, 0, 0))

        print(base._anx_list)


if __name__ == '__main__':
    unittest.main()

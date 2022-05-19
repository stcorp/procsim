'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import tempfile
import unittest
from procsim.biomass.level1_product_generator import Level1PreProcessor, Level1Stripmap

from procsim.core.exceptions import ScenarioError

TEST_DIR = tempfile.TemporaryDirectory()


class _Logger:
    def __init__(self):
        self.count = 0

    def debug(self, *args, **kwargs):
        # print(*args, **kwargs)
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        print(*args, **kwargs)

    def error(self, *args, **kwargs):
        print(*args, **kwargs)


VFRA_DATA = '''<?xml version="1.0" ?>
<Earth_Explorer_File>
    <Earth_Explorer_Header>
        <Fixed_Header>
            <File_Name>BIO_TEST_CPF_L1VFRA_20220421T143831_20220421T143852_01_BN3ZGI</File_Name>
            <File_Description>L1 Virtual Frame</File_Description>
            <Notes/>
            <Mission>BIOMASS</Mission>
            <File_Class>OPER</File_Class>
            <File_Type>CPF_L1VFRA</File_Type>
            <Validity_Period>
                <Validity_Start>UTC=2022-04-21T14:38:31</Validity_Start>
                <Validity_Stop>UTC=2022-04-21T14:38:52</Validity_Stop>
            </Validity_Period>
            <File_Version>01</File_Version>
            <Source>
                <System>PDGS</System>
                <Creator>L1_F</Creator>
                <Creator_Version>1.0</Creator_Version>
                <Creation_Date>UTC=2022-04-22T12:17:06</Creation_Date>
            </Source>
        </Fixed_Header>
        <Variable_Header/>
    </Earth_Explorer_Header>
    <Data_Block type="xml">
        <source_L0S>L0S_Product_Name</source_L0S>
        <source_L0M>L0M_Product_Name</source_L0M>
        <source_AUX_ORB>AUX_ORB_Product_Name</source_AUX_ORB>
        <frame_id>155</frame_id>
        <frame_start_time>UTC=2022-04-21T14:38:31.123456</frame_start_time>
        <frame_stop_time>UTC=2022-04-21T14:38:52.654321</frame_stop_time>
        <frame_Status>NOMINAL</frame_Status>
        <ops_angle_start unit="deg">178.838710</ops_angle_start>
        <ops_angle_stop unit="deg">180</ops_angle_stop>
    </Data_Block>
</Earth_Explorer_File>'''


class VirtualFrameParsingTest(unittest.TestCase):

    def test_settings_from_file(self) -> None:
        '''Check whether settings are properly read from the test data.'''
        config = {'type': 'test'}
        gen = Level1Stripmap(logger=_Logger(), job_config=None, scenario_config=config, output_config=config)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(VFRA_DATA.encode('utf-8'))
            virtual_frame_path = f.name

        gen._parse_virtual_frame_file(virtual_frame_path)

        self.assertEqual(gen._frame_id, 155)
        self.assertEqual(gen._frame_start_time, datetime.datetime(2022, 4, 21, 14, 38, 31, 123456))
        self.assertEqual(gen._frame_stop_time, datetime.datetime(2022, 4, 21, 14, 38, 52, 654321))
        self.assertEqual(gen._frame_status, 'NOMINAL')

    def test_no_frame_info(self) -> None:
        '''Verify that an exception is thrown if framing is attempted without frame info.'''
        config = {
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
        gen = Level1PreProcessor(logger=_Logger(), job_config=None, scenario_config=config, output_config=config)
        gen._enable_framing = True
        with self.assertRaises(ScenarioError):
            gen.generate_output()


if __name__ == '__main__':
    unittest.main()

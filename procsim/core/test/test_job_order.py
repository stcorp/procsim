'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import errno
import glob
import os
import shutil
import unittest
from xml.etree import ElementTree as et

from procsim.core import exceptions, job_order

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
JOB_ORDER_0083 = 'JobOrder_0083.xml'
TEST_JOB_ORDER = 'job_order.xml'
EXPECTED_INPUTS = [
    (['$PATH/BIO_RAW_022_10_20210201T000000_20210201T013810_D20210201T013810_01_B07CK0.zip'], 'RAW_022_10', '', ''),
    (['$PATH/BIO_RAW_023_10_20210201T000000_20210201T013810_D20210201T013810_01_B07CK0.zip'], 'RAW_023_10', '', ''),
    (['$PATH/BIO_RAW_024_10_20210201T000000_20210201T013810_D20210201T013810_01_B07CK0.zip'], 'RAW_024_10', '', ''),
    (['$PATH/BIO_RAW_025_10_20210201T002432_20210201T002932_D20210201T013810_01_B07CK0.zip'], 'RAW_025_10', '', ''),
    (['$PATH/BIO_RAW_026_10_20210201T002432_20210201T002932_D20210201T013810_01_B07CK0.zip'], 'RAW_026_10', '', '')
]


def equal_ignore_order(a, b):
    """ Use only when elements are neither hashable nor sortable! """
    unmatched = list(b)
    for element in a:
        try:
            unmatched.remove(element)
        except ValueError:
            return False
    return not unmatched


def patch_job_order(src, dest, path):
    file_in = open(src, 'r')
    file_out = open(dest, 'w')
    lines = file_in.read()
    file_out.write(lines.replace('$PATH', path))
    file_out.close()
    file_in.close()


class _Logger:
    def __init__(self):
        self.count = 0

    def debug(self, *args, **kwargs):
        pass

    def progress(self, *args, **kwargs):
        self.count += 1

    def error(self, *args, **kwargs):
        print(*args, **kwargs)


class JobOrderParserTest(unittest.TestCase):

    def testFactory(self):
        logger = _Logger()

        self.assertRaises(exceptions.ProcsimException,
                          job_order.job_order_parser_factory, 'ESA-EOPG-EEGS-ID-0083a', logger)

        sim = job_order.job_order_parser_factory('ESA-EOPG-EEGS-ID-0083', logger)
        self.assertIsNotNone(sim)
        self.assertIsInstance(sim, job_order.JobOrderParser)

    def testParse(self):
        path = os.path.join(THIS_DIR, 'tmp')
        os.makedirs(path, exist_ok=True)
        self.addCleanup(shutil.rmtree, path)

        patch_job_order(os.path.join(THIS_DIR, JOB_ORDER_0083), os.path.join(path, TEST_JOB_ORDER), path)

        expected_inputs = []
        for input in EXPECTED_INPUTS:
            entry = job_order.JobOrderInput()
            for file_name in input[0]:
                file_name = file_name.replace('$PATH', path)
                entry.file_names.append(file_name)
                try:
                    os.mknod(os.path.join(THIS_DIR, file_name))
                except OSError as exc:
                    if exc.errno != errno.EEXIST:
                        raise
            entry.file_type = input[1]
            entry.alternative_input_id = input[2]
            entry.id = input[3]
            expected_inputs.append(entry)
        expected_inputs

        logger = _Logger()
        sim = job_order.job_order_parser_factory('ESA-EOPG-EEGS-ID-0083', logger)
        sim.read(os.path.join(path, TEST_JOB_ORDER))
        self.assertEqual(sim.processor_name, 'l0preproc_sm')
        self.assertEqual(sim.processor_version, '01.01')
        self.assertEqual(sim.stderr_levels, [])
        self.assertEqual(sim.stdout_levels, ['ERROR', 'WARNING', 'PROGRESS', 'INFO'])
        self.assertEqual(sim.node, 'MyNode')

        self.assertEqual(len(sim.tasks), 1)
        self.assertEqual(sim.tasks[0].name, 'Step1')
        self.assertEqual(sim.tasks[0].version, '05.03L01')
        self.assertEqual(sim.tasks[0].amount_of_ram_mb, 1073741824)
        self.assertEqual(sim.tasks[0].disk_space_mb, 1073741824)
        self.assertEqual(sim.tasks[0].nr_cpu_cores, 1)

        params = set(sim.tasks[0].processing_parameters)
        self.assertIn('Product_Counter', params)
        self.assertIn('Processing_Stage_Flag', params)
        self.assertIn('originator_ID', params)
        self.assertIn('Orbit_Number', params)
        self.assertIn('Acquisition_Station', params)

        inputs = sim.tasks[0].inputs
        self.assertEqual(len(inputs), 5)
        self.assertTrue(equal_ignore_order(inputs, expected_inputs))


if __name__ == '__main__':
    unittest.main()

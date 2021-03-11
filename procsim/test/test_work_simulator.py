'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import multiprocessing
import os
import queue
import subprocess
import threading
import time
import unittest

import work_simulator

_KB = 2**10
_MB = 2**20


class _Logger:
    def __init__(self):
        self.count = 0

    def debug(self, *args, **kwargs):
        pass

    def progress(self, *args, **kwargs):
        self.count += 1

    def error(self, *args, **kwargs):
        print(*args, **kwargs)


def _meas_resource_usage(meas_time: float = 0.2):
    # Return used memory in MB and cpu load in %
    # Use top to retrieve cpu load and memory usage
    pid = os.getpid()
    cmd = "top -b -n 2 -d {} -p {} | tail -1 | awk '{{print $5,$9}}'".format(meas_time, pid)

    top = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    mem, cpu = top.stdout.split(sep=b' ')
    cpu = cpu.replace(b',', b'.')
    # print('Memory:{} MB, CPU={} %'.format(int(int(mem) / _KB), float(cpu)))
    return int(mem) / _KB, float(cpu)


class WorkSimulatorTest(unittest.TestCase):

    MIN_CPU_LOAD = 90   # should be 100, but could fluctuate a bit (especially with many cores)

    def testMemory(self):
        TEST_TIME = 0
        NR_PROGRESS_MESSAGES = 0
        MEMORY_MB = 200

        logger = _Logger()
        sim = work_simulator.WorkSimulator(
            logger,
            time=TEST_TIME,
            nr_cpu=1,
            memory=MEMORY_MB * _MB,
            disk_space=0,
            nr_progress_log_messages=NR_PROGRESS_MESSAGES
        )
        mem_before, cpu = _meas_resource_usage()
        sim._allocate_memory()
        mem_after, cpu = _meas_resource_usage()
        self.assertAlmostEqual(mem_after - mem_before, MEMORY_MB, delta=10)

    def testAll(self):
        # Test with all available cores
        TEST_TIME = 10
        NR_PROGRESS_MESSAGES = 5
        MEMORY_MB = 250
        DISK_SPACE_MB = 100

        nr_cpu = multiprocessing.cpu_count()
        self.assertGreaterEqual(nr_cpu, 2)

        logger = _Logger()
        sim = work_simulator.WorkSimulator(
            logger,
            time=TEST_TIME,
            nr_cpu=nr_cpu,
            memory=MEMORY_MB * _MB,
            disk_space=DISK_SPACE_MB * _MB,
            nr_progress_log_messages=NR_PROGRESS_MESSAGES
        )

        def meas_task(process_time, q: queue.Queue):
            mem_before, _ = _meas_resource_usage()
            q.put((0))
            time.sleep(process_time / 2)
            mem, cpu = _meas_resource_usage(process_time / 4)

            tmpfile = sim.temp_file_name
            disk_space = 0
            if tmpfile is not None:
                disk_space = os.path.getsize(tmpfile) // _MB
            q.put((mem - mem_before, cpu, disk_space))

        q = queue.Queue()
        meas = threading.Thread(target=meas_task, args=(TEST_TIME, q))
        meas.start()
        q.get()
        tstart = datetime.datetime.now()
        sim.start()
        ttest = datetime.datetime.now() - tstart
        mem, cpu, disk_space = q.get()

        self.assertAlmostEqual(ttest.total_seconds(), TEST_TIME, delta=5)  # Creating temp file is slow on HDD
        self.assertEqual(logger.count, NR_PROGRESS_MESSAGES)
        self.assertAlmostEqual(mem, MEMORY_MB, delta=10)
        self.assertAlmostEqual(disk_space, DISK_SPACE_MB, delta=1)
        self.assertGreater(cpu, self.MIN_CPU_LOAD)


if __name__ == '__main__':
    unittest.main()

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
from typing import Tuple
import unittest

from procsim.core import work_simulator

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


def _get_memkb_cputime(pid: int) -> Tuple[int, datetime.datetime]:
    cmd = f"ps -o rss,cputime -p {pid} | tail -1 | awk '{{print $1,$2}}'"
    ps = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    mem_kb, cputime = ps.stdout.split(sep=b' ')

    return int(mem_kb), datetime.datetime.strptime(cputime.decode('utf-8'), '%M:%S.%f\n')


def _meas_resource_usage(meas_time: float = 0.2):
    # Return used memory in MB and cpu load in %
    # Run ps twice to determine CPU % from elapsed CPU time.
    pid = os.getpid()

    mem_kb, first_cpu_time = _get_memkb_cputime(pid)
    first_run_time = datetime.datetime.now()

    time.sleep(meas_time)

    _, second_cpu_time = _get_memkb_cputime(pid)
    second_run_time = datetime.datetime.now()

    elapsed_time = second_run_time - first_run_time
    elapsed_cpu_time = second_cpu_time - first_cpu_time
    cpu_pct = elapsed_cpu_time / elapsed_time * 100

    return mem_kb * _KB / _MB, cpu_pct


class WorkSimulatorTest(unittest.TestCase):

    MIN_CPU_LOAD = 70   # should be 100, but could fluctuate a bit (especially with many cores)

    def testMemory(self):
        TEST_TIME = 0
        NR_PROGRESS_MESSAGES = 0
        MEMORY_MB = 200

        logger = _Logger()
        sim = work_simulator.WorkSimulator(
            logger,
            time=TEST_TIME,
            nr_cpu=1,
            memory_mb=MEMORY_MB,
            disk_space_mb=0,
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
        DISK_SPACE_MB = 4

        nr_cpu = multiprocessing.cpu_count()
        self.assertGreaterEqual(nr_cpu, 2)

        logger = _Logger()
        sim = work_simulator.WorkSimulator(
            logger,
            time=TEST_TIME,
            nr_cpu=nr_cpu,
            memory_mb=MEMORY_MB,
            disk_space_mb=DISK_SPACE_MB,
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

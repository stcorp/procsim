'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import multiprocessing
import sys
import time

import logger


class WorkSimulator:
    '''
    This class is responsible for consuming memory, CPU cycles and disk space.

    It allocates memory and launches additional processes for each next CPU to
    stress.
    '''
    def __init__(self, logger: logger.Logger, time, nr_cpu, memory, disk_space,
                 nr_progress_log_messages):
        self.logger = logger
        self.time = time
        self.nr_cpu = int(nr_cpu)
        self.memory = int(memory)
        self.disk_space = disk_space
        self.nr_progress_log_messages = nr_progress_log_messages

    def _allocate_memory(self):
        # TODO: Subtract current memory usage? That might be 20..100 MB!
        self.memory_block = None
        try:
            self.memory_block = bytearray(self.memory)
        except MemoryError:
            self.logger.error('Out of memory allocating {} MB'.format(self.memory // 2**20))
        self.logger.debug('size: {} MB'.format(sys.getsizeof(self.memory_block) // 2**20))

    def start(self):
        '''Blocks until done'''
        self._allocate_memory()

        def do_work(step, nr_log_messages):
            for progress in range(0, 100, step):
                if nr_log_messages > 0:
                    self.logger.progress('Working, progress {}%'.format(progress))
                now = time.time()
                while now + self.time / nr_steps > time.time():
                    x = 2
                    # for n in range(25):
                    #     x = x * x

        nr_steps = max(self.nr_progress_log_messages, 1)
        step = int(100 / nr_steps)
        procs = []
        for n in range(self.nr_cpu - 1):
            proc = multiprocessing.Process(target=do_work, args=(step, 0))
            procs.append(proc)
            proc.start()
        do_work(step, self.nr_progress_log_messages)
        for proc in procs:
            proc.join()


if __name__ == '__main__':
    class LoggerStub():

        def debug(self, *args, **kwargs):
            print(*args, **kwargs)

        def progress(self, *args, **kwargs):
            print(*args, **kwargs)

        def error(self, *args, **kwargs):
            print(*args, **kwargs)

    t = 60
    memory_mb = 512
    nr_cpu = multiprocessing.cpu_count()
    print("Run for {} seconds, use {} MB and {} cpu cores".format(t, memory_mb, nr_cpu))
    logger = LoggerStub()
    sim = WorkSimulator(logger, t, nr_cpu, memory_mb * 2**20, 0, 5)
    sim.start()

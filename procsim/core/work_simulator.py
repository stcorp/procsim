'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import multiprocessing
import os
import sys
import tempfile
import time

_MB = 2**20


def do_work(time_to_waste, nr_steps, logger, nr_log_messages):
    step = int(100 / nr_steps)
    for progress in range(0, 100, step):
        if nr_log_messages > 0:
            logger.progress('Working, progress {}%'.format(progress))
        now = time.time()
        while now + time_to_waste / nr_steps > time.time():
            x = 2
            # for n in range(25):
            #     x = x * x


class WorkSimulator:
    '''
    This class is responsible for consuming memory, CPU cycles and disk space.

    It allocates memory and launches additional processes for each next CPU to
    stress.
    '''
    def __init__(self, logger, time, nr_cpu, memory_mb, disk_space_mb,
                 nr_progress_log_messages, tmp_dir=''):
        self._logger = logger
        self._time = time
        self._nr_cpu = int(nr_cpu)
        self._memory_mb = int(memory_mb)
        self._disk_space_mb = disk_space_mb
        self._nr_progress_log_messages = nr_progress_log_messages
        self._tmp_dir = tmp_dir
        self._temp_file_name = None

    @property
    def temp_file_name(self):
        # For unittest only
        return self._temp_file_name

    def _create_temp_file(self):
        # Create file of defined size on disk, return file name
        size = self._disk_space_mb * _MB
        if size > 0:
            CHUNK_SIZE = 1 * _MB
            with tempfile.NamedTemporaryFile(prefix='tmp_procsim_', dir=self._tmp_dir, delete=False) as temp:
                while size > 0:
                    amount = min(size, CHUNK_SIZE)
                    temp.write(os.urandom(max(amount, 0)))
                    size -= amount
                self._temp_file_name = temp.name
                temp.close()
                self._logger.debug('Created temp file {} of {} MB'.format(temp.name, self._disk_space_mb))

    def _remove_temp_file(self):
        if self._temp_file_name is not None:
            os.remove(self._temp_file_name)
            self._logger.debug('Removed temp file {}'.format(self._temp_file_name))
            self._temp_file_name = None

    def _allocate_memory(self):
        # TODO: Subtract current memory usage? That might be 20..100 MB!
        self.memory_block = None
        if self._memory_mb > 0:
            try:
                self.memory_block = bytearray(self._memory_mb * _MB)
            except MemoryError:
                self._logger.error('Out of memory allocating {} MB'.format(self._memory_mb))
            self._logger.debug('Allocated {} MB of RAM'.format(sys.getsizeof(self.memory_block) // _MB))

    def _free_memory(self):
        self.memory_block = None

    def _eat_cpu_cycles(self):
        if self._time > 0:
            self._logger.debug('Start processing on {} cores'.format(self._nr_cpu))
            nr_steps = max(self._nr_progress_log_messages, 1)
            procs = []
            for n in range(self._nr_cpu - 1):
                proc = multiprocessing.Process(target=do_work, args=(self._time, nr_steps, self._logger, 0))
                procs.append(proc)
                proc.start()
            do_work(self._time, nr_steps, self._logger, self._nr_progress_log_messages)
            for proc in procs:
                proc.join()
            
    def start(self):
        '''Blocks until done'''
        self._create_temp_file()
        self._allocate_memory()
        self._eat_cpu_cycles()
        self._free_memory()
        self._remove_temp_file()


if __name__ == '__main__':
    class LoggerStub():

        def debug(self, *args, **kwargs):
            print(*args, **kwargs)

        def progress(self, *args, **kwargs):
            print(*args, **kwargs)

        def error(self, *args, **kwargs):
            print(*args, **kwargs)

    t = 10
    memory_mb = 512
    nr_cpu = multiprocessing.cpu_count()
    disk_mb = 10
    print("Run for {} seconds, use {} MB RAM, {} MB disk and {} cpu cores".format(t, memory_mb, disk_mb, nr_cpu))
    logger = LoggerStub()
    sim = WorkSimulator(logger, t, nr_cpu, memory_mb, disk_mb, 5)
    sim.start()

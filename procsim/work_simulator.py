'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
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


    def start(self):
        '''Blocks until done (TODO: make non-blocking?)'''
        nr_steps = max(self.nr_progress_log_messages, 1)
        step = int(100 / nr_steps)
        for progress in range(0, 100, step):
            if self.nr_progress_log_messages > 0:
                self.logger.progress('Working, progress {}%'.format(progress))
            now = time.time()
            while now + self.time / nr_steps > time.time():
                pass

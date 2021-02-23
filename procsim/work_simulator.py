'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import time

import logger


class WorkSimulator:
    '''
    This class is responsible for consuming memory, CPU cycles and disk space.
    '''
    def __init__(self, logger: logger.Logger, task_config: dict):
        self.logger = logger
        self.time = task_config.get('processing_time', 0)
        self.nr_cpu = task_config.get('nr_cpu', 1)
        self.memory = task_config.get('memory_usage', 0)
        self.disk_space = task_config.get('disk_usage', 0)
        self.nr_progress_log_messages = task_config.get('nr_progress_log_messages', 0)

    def start(self):
        '''Blocks until done (TODO: make non-blocking?)'''
        nr_steps = max(self.nr_progress_log_messages, 1)
        step = int(100 / nr_steps)
        for progress in range(0, 100, step):
            if self.nr_progress_log_messages > 0:
                self.logger.info('Working, progress {}%'.format(progress))
            now = time.time()
            while now + self.time / nr_steps > time.time():
                pass

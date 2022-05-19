'''
Copyright (C) 2021 S[&]T, The Netherlands.

Logging class, messages formatted according to ESA-EOPG-EEGS-ID-0083.
NB: Note that the space after the colon in the formatting string is not specified,
it is only shown in the examples.
'''

import datetime
import os
import sys


class Logger:
    '''
    This class is responsible for generating Log messages on stdout and stderr
    '''
    LEVELS = ['DEBUG', 'INFO', 'PROGRESS', 'WARNING', 'ERROR']

    @staticmethod
    def _print_stderr(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

    @staticmethod
    def _print_stdout(*args, **kwargs):
        print(*args, file=sys.stdout, **kwargs)

    def __init__(self, node_name, processor_name, processor_version,
                 stdout_levels, stderr_levels, task_name=None):
        self._node_name = node_name
        self._processor_name = processor_name
        self._processor_version = processor_version
        self._task_name: str = task_name or 'Unknown'
        self._pid = os.getpid()
        self._header_separator = ':'
        self._stdout_levels = stdout_levels
        self._stderr_levels = stderr_levels

    def set_task_name(self, task_name):
        self._task_name = task_name

    def debug(self, *args, **kwargs):
        self.log('DEBUG', *args, **kwargs)

    def info(self, *args, **kwargs):
        self.log('INFO', *args, **kwargs)

    def progress(self, *args, **kwargs):
        self.log('PROGRESS', *args, **kwargs)

    def warning(self, *args, **kwargs):
        self.log('WARNING', *args, **kwargs)

    def error(self, *args, **kwargs):
        self.log('ERROR', *args, **kwargs)

    def log(self, level: str, *args, **kwargs):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        log_prefix = '{} {} {} {} {} [{:010}]{} [{}]'.format(
            now.isoformat(),
            self._node_name,
            self._processor_name,
            self._processor_version,
            self._task_name,
            self._pid,
            self._header_separator,
            level[0])
        if level in self._stdout_levels:
            self._print_stdout(log_prefix, end=' ')
            self._print_stdout(*args, **kwargs)
        if level in self._stderr_levels:
            self._print_stderr(log_prefix, end=' ')
            self._print_stderr(*args, **kwargs)

'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''

import datetime
import os
import sys


class Logger:
    '''This class is responsible for generating Log messages on stdout and
    stderr, formatted according to ESA-EOPG-EEGS-ID-0083.'''
    LEVELS = {'debug', 'info', 'progress', 'warning', 'error'}

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

    def log(self, level: str, *args, **kwargs):
        if level == 'debug':
            self.debug(*args, **kwargs)
        elif level == 'info':
            self.info(*args, **kwargs)
        elif level == 'progress':
            self.progress(*args, **kwargs)
        elif level == 'warning':
            self.warning(*args, **kwargs)
        else:
            self.error(*args, **kwargs)

    def debug(self, *args, **kwargs):
        self._log('DEBUG', '[D]', *args, **kwargs)

    def info(self, *args, **kwargs):
        self._log('INFO', '[I]', *args, **kwargs)

    def progress(self, *args, **kwargs):
        self._log('PROGRESS', '[P]', *args, **kwargs)

    def warning(self, *args, **kwargs):
        self._log('WARNING', '[W]', *args, **kwargs)

    def error(self, *args, **kwargs):
        self._log('ERROR', '[E]', *args, **kwargs)

    def _log(self, level, message_type, *args, **kwargs):
        now = datetime.datetime.now()
        log_prefix = '{} {} {} {} {} {:012}{}{}'.format(
            now.isoformat(),
            self._node_name,
            self._processor_name,
            self._processor_version,
            self._task_name,
            self._pid,
            self._header_separator,
            message_type)
        if level in self._stdout_levels:
            self._print_stdout(log_prefix, end=' ')
            self._print_stdout(*args, **kwargs)
        if level in self._stderr_levels:
            self._print_stderr(log_prefix, end=' ')
            self._print_stderr(*args, **kwargs)

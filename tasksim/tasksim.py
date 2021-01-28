#!/usr/bin/env python
'''
Copyright (C) 2021 S[&]T, The Netherlands.

Task simulator for scientific processors.
Usage: tasksim <task_filename> <jobOrder_filename>
'''
import sys
import datetime
import os

VERSION = "3.2"

versiontext = "Tasksim v" + VERSION + \
    ", Copyright (C) 2021 S[&]T, The Netherlands.\n"

helptext = versiontext + """\
Usage:
    tasksim <task_filename> <jobOrder_filename> [options]
        Simulate the task as described in the JobOrder file.
"""


def print_stderr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def print_stdout(*args, **kwargs):
    print(*args, file=sys.stdout, **kwargs)


class Logger:
    def __init__(self, processor_name, processor_version):
        self.node_name = 'mynode'            # Read from Job order!
        self.processor_name = processor_name
        self.processor_version = processor_version
        self.task_name = 'mytask'            # Read from config
        self.pid = os.getpid()
        self.header_separator = ':'

    def debug(self, *args, **kwargs):
        self._log('[D]', *args, **kwargs)

    def info(self, *args, **kwargs):
        self._log('[I]', *args, **kwargs)

    def progress(self, *args, **kwargs):
        self._log('[P]', *args, **kwargs)

    def warning(self, *args, **kwargs):
        self._log('[W]', *args, **kwargs)

    def error(self, *args, **kwargs):
        self._log('[E]', *args, **kwargs)

    def _log(self, message_type, *args, **kwargs):
        now = datetime.datetime.now()
        log_prefix = '{} {} {} {} {} {:012}{}{}'.format(
            now.isoformat(),
            self.node_name,
            self.processor_name,
            self.processor_version,
            self.task_name,
            self.pid,
            self.header_separator,
            message_type)
        # TODO: Filter, according to joborder
        print_stdout(log_prefix, end=' ')
        print_stdout(*args, **kwargs)
        # print_stderr(log_prefix, end=' ')
        # print_stderr(args, kwargs)


def main():
    args = sys.argv[1:]
    config_filename = None
    jobOrder_filename = None
    if len(args) == 0 or len(args) > 2:
        print(helptext)
        sys.exit(1)
    if sys.argv[1] == "-h" or sys.argv[1] == "--help":
        print(helptext)
        sys.exit()
    if sys.argv[1] == "-v" or sys.argv[1] == "--version":
        print(versiontext)
        sys.exit()
    if len(args) == 2:
        config_filename = args[0]
        jobOrder_filename = args[1]
    else:
        print(helptext)
        sys.exit(1)

    # TODO: Derive from config
    processor_name = 'testproc'
    processor_version = '01.01'

    logger = Logger(processor_name, processor_version)
    logger.info('Starting, simulating {} v{}, Job Order {}'.format(
        processor_name,
        processor_version,
        jobOrder_filename))
    logger.info('Inputs: <to be done>')
    for progress in range(0, 100, 20):
        logger.info('Working, progress {}%'.format(progress))
    logger.info('Task complete')
    logger.info('Outputs generated: <to be done>')

    exit_code = 0   # 0=ok, 1-127=warning, 128-255=failure
    logger.info('Stopping, returns {}'.format(exit_code))
    exit(exit_code)


if __name__ == "__main__":
    main()

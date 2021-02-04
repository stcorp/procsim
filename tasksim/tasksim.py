#!/usr/bin/env python
'''
Copyright (C) 2021 S[&]T, The Netherlands.

Task simulator for scientific processors.
Usage: tasksim <task_filename> <jobOrder_filename>
'''
import datetime
import json
import os
import sys
import time
from xml.etree import ElementTree as et

from biomass import level0_processor_stub

VERSION = "3.2"

versiontext = "Tasksim v" + VERSION + \
    ", Copyright (C) 2021 S[&]T, The Netherlands.\n"

helptext = versiontext + """\
Usage:
    tasksim <task_filename> <jobOrder_filename> <config_filename>
        Simulate the task as described in the JobOrder file.
"""


class ConfigReader:
    """This class is responsible for reading and parsing the config file."""
    def __init__(self, filename, logger):
        self.config = None
        self.logger = logger
        self._parse_config_file(filename)

    def _parse_config_file(self, filename):
        with open(filename) as data_file:
            try:
                self.config = json.load(data_file)
            except json.JSONDecodeError as e:
                self.logger.error('Error in configuration file on line {}, column {}'.format(e.lineno, e.colno))


def print_stderr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def print_stdout(*args, **kwargs):
    print(*args, file=sys.stdout, **kwargs)


class Logger:
    def __init__(self, processor_name, processor_version, stdout_levels, stderr_levels):
        self.node_name = 'mynode'            # Read from Job order!
        self.processor_name = processor_name
        self.processor_version = processor_version
        self.task_name = 'mytask'            # Read from config
        self.pid = os.getpid()
        self.header_separator = ':'
        self.stdout_levels = stdout_levels
        self.stderr_levels = stderr_levels

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
            self.node_name,
            self.processor_name,
            self.processor_version,
            self.task_name,
            self.pid,
            self.header_separator,
            message_type)
        # TODO: Filter, according to logging levels in job order
        if level in self.stdout_levels:
            print_stdout(log_prefix, end=' ')
            print_stdout(*args, **kwargs)
        if level in self.stderr_levels:
            print_stderr(log_prefix, end=' ')
            print_stderr(*args, **kwargs)


class JobOrderParser:
    '''This class is responsible for reading and parsing the JobOrder'''
    def __init__(self, filename):
        self.processor_name = ''
        self.processor_version = ''
        self.input_files = []
        self.outputs = []
        self.stdout_levels = ['DEBUG', 'INFO', 'PROGRESS', 'WARNING', 'ERROR']
        self.stderr_levels = ['WARNING', 'ERROR']
        self._parse(filename)

    def _parse(self, filename):
        # TODO: This is all for 'old style' XML! Replace (or keep, and create additional class)
        tree = et.parse(filename)
        root = tree.getroot()
        self.processor_name = tree.find(".//Processor_Name").text
        self.processor_version = tree.find(".//Version").text
        inputs_el = tree.find('.//List_of_Inputs')
        for input_el in inputs_el.findall('Input'):
            for file_el in input_el.find('List_of_File_Names').findall('File_Name'):
                self.input_files.append(file_el.text)
        outputs_el = tree.find('.//List_of_Outputs')
        for output_el in outputs_el.findall('Output'):
            output_type = output_el.find('File_Type').text
            output_dir = output_el.find('File_Name').text
            self.outputs.append({'type': output_type, 'dir': output_dir})


class WorkSimulator:
    '''This class is responsible for simulating the actual processing,
    by consuming resources'''
    def __init__(self, logger, task_config):
        self.logger = logger
        self.time = task_config['processing_time']
        self.nr_cpu = task_config['nr_cpu']
        self.memory = task_config['memory_usage']
        self.disk_space = task_config['disk_usage']

    def start(self):
        '''Blocks until done (TODO: make non-blocking?)'''
        for progress in range(0, 100, 20):
            self.logger.info('Working, progress {}%'.format(progress))
            now = time.time()
            while now + self.time / 5 > time.time():
                pass
        self.logger.info('Task complete')


def get_task_config(cfg, task_file_name):
    file_name = os.path.basename(task_file_name)
    for mission_name, mission in cfg.items():
        for processor_name, proc in mission.items():
            for task_name, task in proc.items():
                if task['task_file_name'] == file_name:
                    return task
    return None


def find_fitting_scenario(task_file_name, cfg, job, logger):
    # Find out: can we do something with this combination?
    # 1. The task should be in our config
    # 2. The input/output as specified in the job should match one of the scenarios
    task_config = get_task_config(cfg, task_file_name)
    if task_config is None:
        logger.error('Task {} is not defined in the configuration'.format(task_file_name))
        return None
    print('todo: check scenarios')
    return task_config


def main():
    args = sys.argv[1:]
    if len(args) == 0 or len(args) > 3:
        print(helptext)
        sys.exit(1)
    if sys.argv[1] == "-h" or sys.argv[1] == "--help":
        print(helptext)
        sys.exit()
    if sys.argv[1] == "-v" or sys.argv[1] == "--version":
        print(versiontext)
        sys.exit()
    if len(args) == 3:
        task_filename = args[0]
        job_filename = args[1]
        config_filename = args[2]
    else:
        print(helptext)
        sys.exit(1)

    # Parse JobOrder
    job = JobOrderParser(job_filename)

    # Create logger
    logger = Logger(job.processor_name,
                    job.processor_version, job.stdout_levels, job.stderr_levels)

    # Parse configuration.
    cfg = ConfigReader(config_filename, logger)
    if cfg.config is None:
        logger.error('Cannot read tasksim configuration file {}, exiting'.format(config_filename))
        exit(1)

    logger.info('Starting, simulating Task {} from {} v{}, Job Order {}'.format(
        os.path.basename(task_filename),
        job.processor_name,
        job.processor_version,
        os.path.basename(job_filename)))

    msg = [os.path.basename(file_name) for file_name in job.input_files]
    logger.info('Inputs: {}'.format(msg))

    # TODO: Check input files existence (optional)

    # TODO: Find fitting scenario.
    task_config = find_fitting_scenario(task_filename, cfg.config, job, logger)
    if task_config is None:
        exit(1)

    # For now, assume Biomass level0 processor
    output_path = job.outputs[0]['dir']
    proc = level0_processor_stub.Step1(output_path)
    proc.parse_inputs(job.input_files)

    # Simulate work, consume resources
    worker = WorkSimulator(logger, task_config)
    worker.start()

    # TODO: Generate output data, according to job order, scenario and configuration
    proc.generate_outputs()
    logger.info('Outputs generated: <to be done>')

    exit_code = 0   # 0=ok, 1-127=warning, 128-255=failure
    # logger.info('Stopping, returns {}'.format(exit_code))
    exit(exit_code)


if __name__ == "__main__":
    main()

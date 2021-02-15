#!/usr/bin/env python
'''
Copyright (C) 2021 S[&]T, The Netherlands.

Task simulator for scientific processors.
'''
import datetime
import importlib
import json
import os
import re
import sys
import time
from xml.etree import ElementTree as et

import common

VERSION = "1.0"

versiontext = "procsim v" + VERSION + \
    ", Copyright (C) 2021 S[&]T, The Netherlands.\n"

helptext = versiontext + """\
Usage:
    procsim <task_filename> <jobOrder_filename> <config_filename>
        Simulate the task as described in the JobOrder file.
"""


def read_config(filename, logger):
    # Load configuration and check for correctness.
    ROOT_KEYS = ['processors', 'mission']
    PROCESSOR_KEYS = ['name', 'version', 'tasks']
    TASK_KEYS = ['name', 'version', 'file_name', 'processing_time', 'nr_cpu',
                 'memory_usage', 'disk_usage', 'output_file_size', 'exit_code']
    with open(filename) as data_file:
        try:
            f = open(filename, 'r')
            commented_json = f.read()
            clean_json = common.remove_comments(commented_json)
            config = json.loads(clean_json)
            is_ok = True
            if set(config.keys()) == set(ROOT_KEYS):
                for proc in config['processors']:
                    if set(proc) < set(PROCESSOR_KEYS):
                        is_ok = False
                        break
                    for task in proc['tasks']:
                        if set(task) < set(TASK_KEYS):
                            is_ok = False
                            break
            else:
                is_ok = False
            if not is_ok:
                logger.error('Configuration file incomplete')
                return None
            return config
        except json.JSONDecodeError as e:
            logger.error('Error in configuration file on line {}, column {}'.format(e.lineno, e.colno))
    return None


def TaskFactory(mission, processor, task, logger):
    '''Return a Task class for the given parameters.'''
    # HACK!
    processor = 'level0'
    try:
        mod = importlib.import_module(mission + '.' + processor)
    except ImportError:
        logger.error('Cannot find plugin for mission {}'.format(mission))
        return None
    try:
        task_class = getattr(mod, task)
    except AttributeError:
        logger.error('Processor {} for plugin {} has no task {}'.format(
            mission, processor, task))
        return None
    return task_class


def print_stderr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def print_stdout(*args, **kwargs):
    print(*args, file=sys.stdout, **kwargs)


class Logger:
    '''This class is responsible for generating Log messages on stdout and
    stderr, formatted according to ESA-EOPG-EEGS-ID-0083.'''
    LEVELS = {'debug', 'info', 'progress', 'warning', 'error'}

    def __init__(self, node_name, processor_name, processor_version, task_name, stdout_levels, stderr_levels):
        self.node_name = node_name
        self.processor_name = processor_name
        self.processor_version = processor_version
        self.task_name = task_name
        self.pid = os.getpid()
        self.header_separator = ':'
        self.stdout_levels = stdout_levels
        self.stderr_levels = stderr_levels

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
    '''This class is responsible for reading and parsing the JobOrder.
       TODO: This is all for 'old style' XML! Replace (or keep, and create additional class)'''

    def __init__(self, filename):
        self.processor_name = ''
        self.processor_version = ''
        self.node = 'TODO'  # Not in this version of the XML
        self.tasks = []
        # TODO: hard coded for now, get from new-style job orders
        self.stdout_levels = ['DEBUG', 'INFO', 'PROGRESS', 'WARNING', 'ERROR']
        self.stderr_levels = []
        self.processing_parameters = {}
        self._parse(filename)

    def _find_matching_files(self, pattern):
        # Return list of all files matching 'pattern'.
        # For now, assume the path is 'fixed' and the regex does not contiain slashes.
        rootdir = os.path.dirname(os.path.abspath(pattern))
        files = []
        for file in os.scandir(rootdir):
            if re.match(pattern, file.path):
                files.append(file.path)
        return files

    def _parse(self, filename):
        tree = et.parse(filename)
        self.processor_name = tree.find('.//Processor_Name').text
        self.processor_version = tree.find('.//Version').text

        # Build list of tasks
        for task_el in tree.find('List_of_Ipf_Procs').findall('Ipf_Proc'):
            task = lambda: 0
            task.name = task_el.find('Task_Name').text
            task.version = task_el.find('Task_Version').text
            task.input_files = []
            task.outputs = []
            for input_el in task_el.find('List_of_Inputs').findall('Input'):
                file_name_type = input_el.find('File_Name_Type')
                for file_el in input_el.find('List_of_File_Names').findall('File_Name'):
                    if file_name_type is not None and file_name_type.text == 'Regexp':
                        task.input_files.extend(self._find_matching_files(file_el.text))
                    else:
                        task.input_files.append(file_el.text)
            for output_el in task_el.find('List_of_Outputs').findall('Output'):
                output_type = output_el.find('File_Type').text
                output_dir = output_el.find('File_Name').text
                task.outputs.append({'type': output_type, 'dir': output_dir})
            self.tasks.append(task)

        # List of processing parameters
        for param in tree.find('Processing_Parameters').findall('Processing_Parameter'):
            self.processing_parameters[param.find('Name').text] = param.find('Value').text


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


def find_task_config(cfg, task_file_name, job: JobOrderParser):
    # Parse configuration, find configuration and job ordersettings for this Task.
    file_name = os.path.basename(task_file_name)
    for cfg_proc in cfg['processors']:
        if cfg_proc['name'] != job.processor_name or cfg_proc['version'] != job.processor_version:
            continue
        for cfg_task in cfg_proc['tasks']:
            for job_task in job.tasks:
                if cfg_task['name'] == job_task.name and cfg_task['version'] == job_task.version:
                    if cfg_task['file_name'] == file_name:
                        return cfg_task, job_task
    return None, None


def find_fitting_scenario(task_file_name, cfg, job, logger):
    # Find out: can we do something with this combination?
    # 1. The task should be in our config
    # 2. The input/output as specified in the job should match one of the scenarios
    task_config, job_task = find_task_config(cfg, task_file_name, job)
    if task_config is None:
        logger.error('Task {} is not defined in the configuration'.format(task_file_name))
        return None, None
    return task_config, job_task


def log_configured_messages(cfg, logger):
    # Send any log messages in the configuration file to the logger
    level = 'info'
    for item in cfg.get('logging', []):
        level = item.get('level', level)
        if level not in logger.LEVELS:
            logger.error('Incorrect log level in configuration file: {}'.format(level))
        else:
            message = item.get('message', '')
            if message:
                logger.log(level, message)


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
    logger = Logger(
        job.node,
        job.processor_name,
        job.processor_version,
        'Unknown',
        job.stdout_levels,
        job.stderr_levels
    )

    # Parse configuration.
    cfg = read_config(config_filename, logger)
    if cfg is None:
        logger.error('Cannot read configuration file {}, exiting'.format(config_filename))
        sys.exit(1)

    # TODO: Find fitting scenario.
    task_config, job_task = find_fitting_scenario(task_filename, cfg, job, logger)
    if task_config is None:
        sys.exit(1)

    logger.task_name = job_task.name    # This info was not available before

    # Log messages in config
    log_configured_messages(task_config, logger)

    # Log processing parameters
    for param, value in job.processing_parameters.items():
        logger.info('Processing parameter {} = {}'.format(param, value))

    msg = [os.path.basename(file_name) for file_name in job_task.input_files]
    logger.info('Inputs: {}'.format(msg))

    # TODO: Check input files existence (optional)

    logger.info('Starting, simulating {} from {} v{}, Order {}'.format(
        os.path.basename(task_filename),
        job.processor_name,
        job.processor_version,
        os.path.basename(job_filename)))

    output_path = job_task.outputs[0]['dir']
    proc_class = TaskFactory(cfg['mission'], job.processor_name, job_task.name, logger)
    if (proc_class is None):
        sys.exit(1)
    proc = proc_class(output_path, logger)
    if not proc.parse_inputs(job_task.input_files):
        sys.exit(1)

    # Simulate work, consume resources
    worker = WorkSimulator(logger, task_config)
    worker.start()

    # TODO: Generate output data, according to job order, scenario and configuration
    proc.generate_outputs()
    logger.info('Outputs generated: <to be done>')

    exit_code = 0   # 0=ok, 1-127=warning, 128-255=failure
    exit(exit_code)


if __name__ == "__main__":
    main()
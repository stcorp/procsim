#!/usr/bin/env python
'''
Copyright (C) 2021 S[&]T, The Netherlands.

Task simulator for scientific processors.
'''
import abc
import getopt
import importlib
import json
import os
import sys
from typing import List, Optional

import utils
from logger import Logger
from work_simulator import WorkSimulator
from job_order import JobOrderParser, JobOrderInput, JobOrderTask

VERSION = "1.0"


class IProductGenerator(abc.ABC):
    '''
    Interface for product generators
    '''
    @abc.abstractmethod
    def parse_inputs(self, inputs: List[JobOrderInput]) -> bool:
        pass

    @abc.abstractmethod
    def list_scenario_metadata_parameters(self) -> List[str]:
        pass

    @abc.abstractmethod
    def read_scenario_metadata_parameters(self):
        pass

    @abc.abstractmethod
    def generate_output(self):
        pass


def _read_config(filename, logger):
    # Load configuration and check for correctness.
    # TODO: Use JSON schema! Yes, that exists...
    ROOT_KEYS = ['scenarios', 'mission']
    SCENARIO_KEYS = ['name', 'file_name', 'processor_name', 'processor_version', 'task_name', 'task_version', 'outputs']
    with open(filename) as data_file:
        try:
            f = open(filename, 'r')
            commented_json = f.read()
            uncommented_json = utils.json_remove_comments(commented_json)
            clean_json = utils.remove_trailing_commas(uncommented_json)
            config = json.loads(clean_json)
            is_ok = True
            if set(config.keys()) == set(ROOT_KEYS):
                for scenario in config['scenarios']:
                    if set(scenario) < set(SCENARIO_KEYS):
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
    logger.error('Cannot read configuration file {}, exiting'.format(filename))
    return None


def _output_factory(mission, logger, job_output_cfg, scenario_cfg, output_cfg) -> Optional[IProductGenerator]:
    '''Return an output generator for the given parameters.'''
    # Import plugin for this mission
    try:
        mod = importlib.import_module(mission)
    except ImportError:
        logger.error('Cannot open plugin for mission {}'.format(mission))
        return None
    try:
        factory = getattr(mod, 'product_generator_factory')
    except AttributeError:
        logger.error('Plugin {} has no factory'.format(mission))
        return None
    # Use plugin factory to create generator
    generator = factory(logger, job_output_cfg, scenario_cfg, output_cfg)
    return generator


def _compare_inputs(scenario, task):
    # Todo! Match types against file names
    return True


def _compare_outputs(scenario, task):
    # Every output type in the scenario should be in the task config
    scenario_output_types = {op['type'] for op in scenario['outputs']}
    task_output_types = {op.type for op in task.outputs}
    return scenario_output_types == task_output_types


def _find_fitting_scenario(logger, task_filename, cfg, job: JobOrderParser, scenario_name):
    # Find scenario from the list of scenarios in the cfg.
    #
    # If an explicit scenario name is given, use that and try to find a matching
    # task in the JobOrder.
    #
    # Else, compare every scenario with:
    # 1. The 'File name' argument procsim was called with
    # 2. The processor and task name/version as specified in the jobOrder
    # 3. The list of inputs as specified in the jobOrder
    # 4. The list of outputs as specified in the jobOrder

    # Parse configuration, find configuration and job ordersettings for this Task.
    exec_found = False
    proc_found = False
    task_found = False
    matching_inputs_found = False
    file_name = os.path.basename(task_filename)
    for scenario in cfg['scenarios']:
        if scenario_name is not None:
            if scenario['name'] != scenario_name:
                continue
            exec_found = True
            proc_found = True
            task_found = True
            if not job.tasks:
                return scenario, JobOrderTask()  # Return empty jobordertask
        else:
            if scenario['file_name'] != file_name:
                continue
            exec_found = True
            if scenario['processor_name'] != job.processor_name or \
               scenario['processor_version'] != job.processor_version:
                continue
            proc_found = True

        # Find matching job
        for job_task in job.tasks:
            if scenario['task_name'] != job_task.name or \
               scenario['task_version'] != job_task.version:
                continue
            task_found = True
            if not _compare_inputs(scenario, job_task):
                continue
            matching_inputs_found = True
            if not _compare_outputs(scenario, job_task):
                continue
            return scenario, job_task

    if not exec_found:
        if task_filename:
            logger.error('No scenario for {} found'.format(os.path.basename(task_filename)))
        else:
            logger.error('No scenario "{}" found'.format(scenario_name))
    elif not proc_found:
        logger.error('No scenario for {} and processor {} {} found'.format(
            os.path.basename(task_filename), job.processor_name, job.processor_version))
    elif not task_found:
        logger.error('No scenario with matching task found for {}.'.format(
            os.path.basename(task_filename)))
    elif not matching_inputs_found:
        logger.error('No scenario with matching inputs found for {}.'.format(
            os.path.basename(task_filename)))
    else:
        logger.error('No scenario with matching outputs found for {}.'.format(
            os.path.basename(task_filename)))

    return None, None


def _log_configured_messages(scenario, logger):
    # Send any log messages in the configuration file to the logger
    level = 'INFO'
    for item in scenario.get('logging', []):
        level = item.get('level', level).upper()
        if level not in logger.LEVELS:
            logger.error('Incorrect log level {} in configuration file'.format(level))
        else:
            message = item.get('message', '')
            if message:
                logger.log(level, message)


def _log_processor_parameters(parameters, logger):
    for param, value in parameters.items():
        logger.info('Processing parameter {} = {}'.format(param, value))


def _do_work(logger, config):
    time = config.get('processing_time', 0)
    nr_cpu = config.get('nr_cpu', 1)
    memory = config.get('memory_usage', 0)
    disk_space = config.get('disk_usage', 0)
    nr_progress_log_messages = config.get('nr_progress_log_messages', 0)
    worker = WorkSimulator(logger, time, nr_cpu, memory, disk_space,
                           nr_progress_log_messages)
    worker.start()


versiontext = "procsim v" + VERSION + \
    ", Copyright (C) 2021 S[&]T, The Netherlands.\n"

helptext = versiontext + """\
Usage: procsim [-t TASK_FILENAME] [-j JOBORDER_FILE] [-s SCENARIO_NAME] CONFIG_FILE
  or:  procsim -h
  or:  procsim -v

    Simulate a scenario from CONFIG_FILE. The scenario is selected using
    TASK_FILENAME (the name of the task as called by the CPF)
    or specified explicitly by SCENARIO_NAME.
"""


def parse_command_line(argv):
    config_filename = None
    task_filename = ''
    job_filename = None
    scenario_name = None
    try:
        opts, args = getopt.getopt(argv, 'hvt:j:s:', ['help', 'version', 'task_filename=', 'joborder=', 'scenario='])
    except getopt.GetoptError:
        print(helptext)
        sys.exit()
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(helptext)
            sys.exit()
        elif opt in ('-v', '--version'):
            print(versiontext)
            sys.exit()
        elif opt in ('-t', '--task_filename'):
            task_filename = arg
        elif opt in ('-j', '--joborder_filename'):
            job_filename = arg
        elif opt in ('-s', '--scenario_name'):
            scenario_name = arg
    if not args:
        print(helptext)
        sys.exit()
    config_filename = args[0]
    return task_filename, job_filename, config_filename, scenario_name


def main(argv):
    task_filename, job_filename, config_filename, scenario_name = parse_command_line(argv)

    job = JobOrderParser(job_filename)

    logger = Logger(
        job.node,
        job.processor_name,
        job.processor_version,
        job.stdout_levels,
        job.stderr_levels
    )

    config = _read_config(config_filename, logger)
    if config is None:
        sys.exit(1)

    scenario, job_task = _find_fitting_scenario(logger, task_filename, config, job, scenario_name)
    if scenario is None:
        sys.exit(1)

    logger.set_task_name(job_task.name)    # This info was not available yet

    _log_configured_messages(scenario, logger)
    _log_processor_parameters(job.processing_parameters, logger)

    for input in job_task.inputs:
        for file_name in input.file_names:
            logger.info('Input type {}: {}'.format(input.file_type, os.path.basename(file_name)))
    logger.info('Simulate scenario {}'.format(scenario['name']))

    # Create product generators, parse inputs
    generators: List[IProductGenerator] = []
    for output_cfg in scenario['outputs']:
        # Find corresponding output parameters in JobOrder task config
        job_output_cfg = None
        for job_output_cfg in job_task.outputs:
            if job_output_cfg.type == output_cfg['type']:
                break

        generator = _output_factory(config['mission'], logger, job_output_cfg, scenario, output_cfg)
        if (generator is None):
            sys.exit(1)
        if job_task.inputs and not generator.parse_inputs(job_task.inputs):
            sys.exit(1)
        generators.append(generator)

    _do_work(logger, scenario)

    for gen in generators:
        gen.read_scenario_metadata_parameters()
        gen.generate_output()

    exit_code = scenario['exit_code']
    logger.info('Task done, exit with code {}'.format(exit_code))
    exit(exit_code)


if __name__ == "__main__":
    main(sys.argv[1:])

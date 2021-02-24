#!/usr/bin/env python
'''
Copyright (C) 2021 S[&]T, The Netherlands.

Task simulator for scientific processors.
'''
import abc
import importlib
import json
import os
import sys
from typing import List, Optional

import utils
from logger import Logger
from work_simulator import WorkSimulator
from job_order import JobOrderParser, JobOrderInput

VERSION = "1.0"

versiontext = "procsim v" + VERSION + \
    ", Copyright (C) 2021 S[&]T, The Netherlands.\n"

helptext = versiontext + """\
Usage:
    procsim <task_filename> <jobOrder_filename> <config_filename>
        Simulate the task as described in the JobOrder file.
"""


class IProductGenerator(abc.ABC):
    '''
    Interface for product generators
    '''
    @abc.abstractmethod
    def parse_inputs(self, inputs: List[JobOrderInput]) -> bool:
        pass

    @abc.abstractmethod
    def generate_output(self):
        pass


def read_config(filename, logger):
    # Load configuration and check for correctness.
    # TODO: Use JSON schema! Yes, that exists...
    ROOT_KEYS = ['scenarios', 'mission']
    SCENARIO_KEYS = ['name', 'file_name', 'processor_name', 'processor_version', 'task_name', 'task_version', 'outputs']
    with open(filename) as data_file:
        try:
            f = open(filename, 'r')
            commented_json = f.read()
            clean_json = utils.json_remove_comments(commented_json)
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
    return None


def OutputFactory(mission, logger, job_output_cfg, scenario_cfg, output_cfg) -> Optional[IProductGenerator]:
    '''Return an output generator for the given parameters.'''
    # Import plugin for this mission
    try:
        mod = importlib.import_module(mission + '.product_generator_factory')
    except ImportError:
        logger.error('Cannot open plugin for mission {}'.format(mission))
        return None
    try:
        factory = getattr(mod, 'OutputGeneratorFactory')
    except AttributeError:
        logger.error('Plugin {} has no factory'.format(mission))
        return None
    # Use plugin factory to create generator
    generator = factory(logger, job_output_cfg, scenario_cfg, output_cfg)
    return generator


def compare_inputs(scenario, task):
    # Todo! Match types against file names
    return True


def compare_outputs(scenario, task):
    # Every output type in the scenario should be in the task config
    scenario_output_types = {op['type'] for op in scenario['outputs']}
    task_output_types = {op.type for op in task.outputs}
    return scenario_output_types == task_output_types


def find_fitting_scenario(logger, task_filename, cfg, job: JobOrderParser):
    # Find out: do we have a scenario for this combination of JobOrder and filename?
    #
    # Compare every scenario with:
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
        if scenario['file_name'] != file_name:
            continue
        exec_found = True
        if scenario['processor_name'] != job.processor_name or \
           scenario['processor_version'] != job.processor_version:
            continue
        proc_found = True
        for job_task in job.tasks:
            if scenario['task_name'] != job_task.name or \
               scenario['task_version'] != job_task.version:
                continue
            task_found = True
            if not compare_inputs(scenario, job_task):
                continue
            matching_inputs_found = True
            if not compare_outputs(scenario, job_task):
                continue
            return scenario, job_task

    if not exec_found:
        logger.error('No scenario for {} found'.format(task_filename))
    elif not proc_found:
        logger.error('No scenario for {} and processor {} {} found'.format(
            task_filename, job.processor_name, job.processor_version))
    elif not task_found:
        logger.error('No scenario with matching task found for {}.'.format(
            task_filename))
    elif not matching_inputs_found:
        logger.error('No scenario with matching inputs found for {}.'.format(
            task_filename))
    else:
        logger.error('No scenario with matching outputs found for {}.'.format(
            task_filename))

    return None, None


def log_configured_messages(scenario, logger):
    # Send any log messages in the configuration file to the logger
    level = 'info'
    for item in scenario.get('logging', []):
        level = item.get('level', level)
        if level not in logger.LEVELS:
            logger.error('Incorrect log level {} in configuration file'.format(level))
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
        job.stdout_levels,
        job.stderr_levels
    )

    cfg = read_config(config_filename, logger)
    if cfg is None:
        logger.error('Cannot read configuration file {}, exiting'.format(config_filename))
        sys.exit(1)

    scenario, job_task = find_fitting_scenario(logger, task_filename, cfg, job)
    if scenario is None:
        sys.exit(1)

    logger.set_task_name(job_task.name)    # This info was not available before

    log_configured_messages(scenario, logger)

    for param, value in job.processing_parameters.items():
        logger.info('Processing parameter {} = {}'.format(param, value))
    for input in job_task.inputs:
        for file_name in input.file_names:
            logger.info('Input type {}: {}'.format(input.file_type, os.path.basename(file_name)))
    logger.info('Starting, simulating scenario {}, Order {}'.format(
        scenario['name'],
        os.path.basename(job_filename)))

    # Create product generators, parse inputs
    generators = []
    for output_cfg in scenario['outputs']:
        # Find corresponding output parameters in JobOrder task config
        job_output_cfg = None
        for job_output_cfg in job_task.outputs:
            if job_output_cfg.type == output_cfg['type']:
                break

        generator = OutputFactory(cfg['mission'], logger, job_output_cfg, scenario, output_cfg)
        if (generator is None):
            sys.exit(1)
        if not generator.parse_inputs(job_task.inputs):
            sys.exit(1)
        generators.append(generator)

    worker = WorkSimulator(logger, scenario)
    worker.start()

    for gen in generators:
        gen.generate_output()

    exit_code = scenario['exit_code']
    logger.info('Task done, exit with code {}'.format(exit_code))
    exit(exit_code)


if __name__ == "__main__":
    main()

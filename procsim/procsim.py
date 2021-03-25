#!/usr/bin/env python3
'''
Copyright (C) 2021 S[&]T, The Netherlands.

Task simulator for scientific processors.
'''
import abc
import getopt
import importlib
import json
import os
import signal
import sys
from typing import List, Optional, Tuple

import utils
from exceptions import ScenarioError, TerminateError
from job_order import (JobOrderInput, JobOrderParser, JobOrderTask,
                       job_order_parser_factory)
from logger import Logger
from version import __version__
from work_simulator import WorkSimulator

# JobOrder/logging format ICD. Hard-coded for now, can be read from plugin or
# configuration file if needed.
PROCESSOR_ICD = 'ESA-EOPG-EEGS-ID-0083'


def signal_term_handler(signal, frame):
    raise TerminateError('Program terminated (SIGTERM)')


def signal_int_handler(signal, frame):
    raise TerminateError('Program interrupted (SIGINT)')


class IProductGenerator(abc.ABC):
    '''
    Interface for product generators
    '''
    @abc.abstractmethod
    def get_params(self) -> Tuple[List[str], List[str], List[str]]:
        '''
        Returns generator, header and acquisition parameters
        '''
        pass

    @abc.abstractmethod
    def parse_inputs(self, inputs: List[JobOrderInput]) -> bool:
        pass

    @abc.abstractmethod
    def list_scenario_parameters(self) -> List[str]:
        pass

    @abc.abstractmethod
    def read_scenario_parameters(self):
        pass

    @abc.abstractmethod
    def generate_output(self):
        pass


def _read_config(logger, filename) -> dict:
    # Load configuration and check for correctness.
    # TODO: Use JSON schema! Yes, that exists...
    ROOT_KEYS = ['scenarios', 'mission']
    SCENARIO_KEYS = ['name', 'file_name', 'processor_name', 'processor_version', 'task_name', 'task_version', 'outputs']
    with open(filename) as f:
        try:
            commented_json = f.read()
            uncommented_json = utils.json_remove_comments(commented_json)
            clean_json = utils.remove_trailing_commas(uncommented_json)
            config = json.loads(clean_json)
            is_ok = True
            if set(config.keys()) >= set(ROOT_KEYS):
                for scenario in config['scenarios']:
                    if set(scenario) < set(SCENARIO_KEYS):
                        is_ok = False
                        break
            else:
                is_ok = False
            if not is_ok:
                raise ScenarioError('Configuration file incomplete')
            return config
        except json.JSONDecodeError as e:
            raise ScenarioError('Error in configuration file on line {}, column {}'.format(e.lineno, e.colno))


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


def _find_fitting_scenario(task_filename, cfg, job: JobOrderParser, scenario_name) -> Tuple[dict, JobOrderTask]:
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
            raise ScenarioError('No scenario for {} found'.format(os.path.basename(task_filename)))
        else:
            raise ScenarioError('No scenario "{}" found'.format(scenario_name))
    elif not proc_found:
        raise ScenarioError('No scenario for {} and processor {} {} found'.format(
            os.path.basename(task_filename), job.processor_name, job.processor_version))
    elif not task_found:
        raise ScenarioError('No scenario with matching task found for {}.'.format(
            os.path.basename(task_filename)))
    elif not matching_inputs_found:
        raise ScenarioError('No scenario with matching inputs found for {}.'.format(
            os.path.basename(task_filename)))
    else:
        raise ScenarioError('No scenario with matching outputs found for {}.'.format(
            os.path.basename(task_filename)))


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


def _log_inputs(inputs, logger):
    for input in inputs:
        for file_name in input.file_names:
            logger.info('Input type {}: {}'.format(input.file_type, os.path.basename(file_name)))


def _create_product_generators(logger: Logger, mission: str, job_task: Optional[JobOrderTask],
                               scenario: dict) -> List[IProductGenerator]:
    '''
    Create product generators for all enabled outputs in the scenario
    '''
    generators: List[IProductGenerator] = []
    for output_cfg in scenario['outputs']:
        product_type = output_cfg['type']
        is_enabled = output_cfg.get('enable')
        if is_enabled is None or is_enabled:
            # Find parameters for this output in JobOrder task config
            job_output_cfg = None
            for job_output_cfg in job_task.outputs:
                if job_output_cfg.type == product_type:
                    break
            generator = _output_factory(mission, logger, job_output_cfg, scenario, output_cfg)
            if (generator is None):
                sys.exit(1)
            generators.append(generator)
        else:
            logger.warning('Output product {} is disabled in scenario'.format(product_type))
    return generators


def _do_work(logger, config, job_task: Optional[JobOrderTask]):
    # Get paremters from scenario
    time = config.get('processing_time', 0)
    nr_cpu = config.get('nr_cpu', 1)
    memory_mb = config.get('memory_usage', 0)
    disk_space_mb = config.get('disk_usage', 0)
    nr_progress_log_messages = config.get('nr_progress_log_messages', 0)

    # The Job order resource parameters are treated as limits over the
    # resource usage as specified in the scenario config.
    if job_task is not None:
        if job_task.nr_cpu_cores != 0.0:
            nr_cpu = min(nr_cpu, int(job_task.nr_cpu_cores))
        memory_mb = min(memory_mb, job_task.amount_of_ram_mb)
        disk_space_mb = min(memory_mb, job_task.disk_space_mb)

    worker = WorkSimulator(
        logger,
        time,
        nr_cpu,
        memory_mb,
        disk_space_mb,
        nr_progress_log_messages)
    worker.start()


def _generate_intermediate_files(logger, job_task: Optional[JobOrderTask]):
    if job_task is None:
        return
    for intermediate_output in job_task.intermediate_outputs:
        logger.info('Create intermediate file {} with id {}'.format(
            os.path.basename(intermediate_output.file_name),
            intermediate_output.id
        ))
        with open(intermediate_output.file_name, 'w') as file:
            file.write('Intermediate file, created by procsim\nID={}\n'.format(
                intermediate_output.id
            ))
            file.close()


versiontext = "procsim v" + __version__ + \
    ", Copyright (C) 2021 S[&]T, The Netherlands.\n"

helptext = versiontext + """\
Usage:
    procsim [OPTIONS] -t TASK_FILENAME -j JOBORDER_FILE [-s SCENARIO_NAME] CONFIG_FILE
    procsim [OPTIONS] -s SCENARIO_NAME CONFIG_FILE
        Simulate a scenario from CONFIG_FILE.
        The scenario is selected using either TASK_FILENAME and JOBORDER_FILE,
        or specified explicitly by SCENARIO_NAME.

    procsim -v
        Shows version number.

    procsim -h
    procsim -h MISSION PRODUCT_TYPE
        Shows generic help, or for a specific product type.

    -t, --task_filename=NAME    The name of the task as called by the CPF
    -j, --joborder=NAME         The file name of the job order
    -s, --scenario=SCENARIO     For use of SCENARIO (normally derived from
                                task-filename and joborder)
    -l, --log-level=LVL         Force log level to LVL. LVL can be
                                debug, info, progress, warning, error
"""


def full_help(args):
    prod = None
    if len(args) == 0:
        print(helptext)
        print('procsim has support for the following missions:')
        this_dir = os.path.dirname(os.path.abspath(__file__))
        plugins = [f.path for f in os.scandir(this_dir) if f.is_dir() and f.name not in ['test', '__pycache__']]
    elif len(args) != 2:
        print(helptext)
        return
    else:
        plugins = [str(args[0])]
        prod = args[1]

    for plugin in plugins:
        plugin = os.path.basename(plugin)
        try:
            mod = importlib.import_module(plugin)
        except ImportError:
            continue  # Not a Python package
        try:
            lister = getattr(mod, 'list_supported_products')
            factory = getattr(mod, 'product_generator_factory')
        except AttributeError:
            continue  # Not a procsim plugin
        product_list = lister()
        flattened_list = [prod for prods in product_list for prod in prods]
        if prod is None or prod not in flattened_list:
            print()
            print('- {}, supporting the following products:'.format(plugin))
            for prod in product_list:
                print('    - {}'.format(prod))
        else:
            config = {'output_path': '.', 'type': prod, 'anx': ''}
            gen = factory(None, None, config, config)
            print()
            print('{} product generator details:'.format(prod))
            print('-------------------------------------')
            print(gen.__doc__)
            print('Supported scenario parameters for product type {} are:'.format(prod))
            for param, ptype in gen.list_scenario_parameters():
                print('   - {} ({})'.format(param, ptype))


def parse_command_line(argv):
    config_filename = None
    task_filename = ''
    job_filename = None
    scenario_name = None
    log_level = None
    try:
        opts, args = getopt.getopt(argv, 'hvt:j:s:l:', ['help', 'version', 'task_filename=', 'joborder=', 'scenario=', 'log-level='])
    except getopt.GetoptError:
        print(helptext)
        sys.exit()
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            full_help(args)
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
        elif opt in ('-l', '--log-level'):
            level = arg.upper()
            if level in Logger.LEVELS:
                log_level = level
            else:
                levels = [lvl.lower() for lvl in Logger.LEVELS]
                print('Log level must be one of {}'.format(Logger.LEVELS))
    if not args:
        print(helptext)
        sys.exit()
    config_filename = args[0]
    return task_filename, job_filename, config_filename, scenario_name, log_level


def main(argv):
    task_filename, job_filename, config_filename, scenario_name, log_level = parse_command_line(argv)
    logger = Logger('', '', '', Logger.LEVELS, [])  # Create temporary logger
    try:
        # Program terminate/interrupt, will raise an exception which in turn will
        # result in a log message.
        signal.signal(signal.SIGTERM, signal_term_handler)
        signal.signal(signal.SIGINT, signal_int_handler)

        config = _read_config(logger, config_filename)
        if config is None:
            sys.exit(1)

        job = job_order_parser_factory(PROCESSOR_ICD, logger)
        job.read(job_filename)

        scenario, job_task = _find_fitting_scenario(task_filename, config, job, scenario_name)

        # Adjust log level
        stdout_levels = job.stdout_levels
        stderr_levels = job.stderr_levels
        log_level = log_level or scenario.get('log_level') or config.get('log_level')
        if log_level is not None:
            stdout_levels = []
            stderr_levels = []
            for level in Logger.LEVELS[::-1]:
                stdout_levels.append(level)
                if level == log_level.upper():
                    break

        logger = Logger(
            job.node,
            job.processor_name,
            job.processor_version,
            stdout_levels,
            stderr_levels
        )

        exit_code = scenario.get('exit_code', 0)

        logger.set_task_name(job_task.name)    # This info was not available yet
        logger.info('Procsim v{} processor stub simulator'.format(__version__))
        logger.info('Simulate scenario {}'.format(scenario['name']))
        if job_filename:
            logger.info('Read JobOrder {}'.format(job_filename))
            if job._is_validated:
                logger.debug('JobOrder validation against schema: OK')
            logger.info('Read task {} from the JobOrder'.format(job_task.name))
        _log_processor_parameters(job_task.processing_parameters, logger)
        _log_inputs(job_task.inputs, logger)
        _log_configured_messages(scenario, logger)

        _do_work(logger, scenario, job_task)

        _generate_intermediate_files(logger, job_task)

        generators = _create_product_generators(logger, config['mission'], job_task, scenario)
        for gen in generators:
            if job_task.inputs and not gen.parse_inputs(job_task.inputs):
                sys.exit(1)
            gen.read_scenario_parameters()
            gen.generate_output()

        logger.info('Task done, exit with code {}'.format(exit_code))

    except TerminateError:
        exit_code = 1
        logger.error(str(sys.exc_info()[1]).strip("\n\r"))
        logger.info('Terminate with code {}'.format(exit_code))
    except ScenarioError:
        exit_code = 1
        logger.error(str(sys.exc_info()[1]).strip("\n\r"))
        logger.info('Terminate with code {}'.format(exit_code))

    exit(exit_code)


if __name__ == "__main__":
    main(sys.argv[1:])

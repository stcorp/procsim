#!/usr/bin/env python3
'''
Copyright (C) 2021 S[&]T, The Netherlands.

Task simulator for scientific processors, entry point.
'''
import argparse
import importlib
import json
import os
import signal
import sys
from typing import List, Optional, Tuple

from . import utils
from .iproduct_generator import IProductGenerator
from .exceptions import GeneratorError, ScenarioError, TerminateError
from .job_order import JobOrderParser, JobOrderTask, job_order_parser_factory
from .logger import Logger
from .version import __version__
from .work_simulator import WorkSimulator

# JobOrder/logging format ICD. Hard-coded for now, can be read from plugin or
# configuration file if needed.
PROCESSOR_ICD = 'ESA-EOPG-EEGS-ID-0083'


def signal_term_handler(signal, frame):
    raise TerminateError('Program terminated (SIGTERM)')


def signal_int_handler(signal, frame):
    raise TerminateError('Program interrupted (SIGINT)')


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


def _output_generator_factory(mission, logger, job_output_cfg, scenario_cfg, output_cfg) -> Optional[IProductGenerator]:
    # Import plugin and get factory for this mission
    try:
        mod = importlib.import_module('procsim.' + mission)
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


def _compare_outputs(scenario, task):
    # Every output type in the scenario should be in the task config, but not the other way around:
    # the job order for each task represents all POSSIBLE outputs of that task.
    scenario_output_types = {op['type'] for op in scenario['outputs']}
    task_output_types = {op.type for op in task.outputs}
    return scenario_output_types.issubset(task_output_types)


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
            matching_inputs_found = True
            if not _compare_outputs(scenario, job_task):
                continue
            return scenario, job_task

    if not exec_found:
        if task_filename:
            raise ScenarioError('No scenario with filename="{}" found.'.format(os.path.basename(task_filename)))
        else:
            raise ScenarioError('No scenario "{}" found'.format(scenario_name))
    elif not proc_found:
        raise ScenarioError('No scenario for {} and processor {} {} found'.format(
            os.path.basename(task_filename), job.processor_name, job.processor_version))
    elif not task_found:
        raise ScenarioError('No scenario with matching job task found for {}.'.format(
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
    if not inputs:
        logger.info('No input files')
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
            if job_task is not None:
                for job_output_cfg in job_task.outputs:
                    if job_output_cfg.type == product_type:
                        break
            generator = _output_generator_factory(mission, logger, job_output_cfg, scenario, output_cfg)
            if generator is None:
                sys.exit(1)
            generators.append(generator)
        else:
            logger.warning('Output product {} is disabled in scenario'.format(product_type))
    return generators


def _do_work(logger, config, job_task: Optional[JobOrderTask]):
    # Get resource usage parameters from scenario
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
    ", Copyright (C) 2022 S[&]T, The Netherlands."
procsim_description = \
    "Simulate a processor task, using a scenario read from config_filename."


def print_product_info(prod):
    if prod == '':
        print(versiontext)
        print('This tool has support for the following products:')
    this_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    plugins = [f.path for f in os.scandir(this_dir) if f.is_dir() and f.name not in ['test', '__pycache__', 'core']]

    for plugin in plugins:
        plugin = os.path.basename(plugin)
        try:
            mod = importlib.import_module('procsim.' + plugin)
        except ImportError:
            continue  # Not a Python package
        try:
            lister = getattr(mod, 'list_supported_products')
            factory = getattr(mod, 'product_generator_factory')
        except AttributeError:
            continue  # Not a procsim plugin
        product_list = lister()
        flattened_list = [prod for prods in product_list for prod in prods]
        if prod == '':
            print()
            print('- {}:'.format(plugin.upper()))
            for prods in product_list:
                n = len(prods)
                for idx in range(n):
                    if idx % 6 == 0:
                        print('\n      ', end='')
                    else:
                        print(', ', end='')
                    print('{}'.format(prods[idx]), end='')
                print()
        elif prod in flattened_list:
            config = {'output_path': '.', 'type': prod, 'anx': ''}
            gen = factory(None, None, config, config)
            print()
            print('{} product generator details:'.format(prod))
            print('-------------------------------------')
            print(gen.__doc__)
            print('Supported scenario parameters for product type {} are:'.format(prod))
            for param, ptype in gen.list_scenario_parameters():
                print('   - {} ({})'.format(param, ptype))


def parse_command_line():
    parser = argparse.ArgumentParser(description=procsim_description)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i', '--info',
                       metavar='product_name',
                       dest='info_product',
                       default=None,
                       const='',
                       nargs='?', action='store',
                       help='list all supported output products, or details for a specific product')
    group.add_argument(dest='config_filename', metavar='config_filename', nargs='?')
    parser.add_argument('-v', '--version', action='version', version=versiontext)
    parser.add_argument('-t', '--task_filename', metavar='name', dest='task_filename', default='',
                        help='the name of the task as called by the CPF')
    parser.add_argument('-j', '--job_order', metavar='filename', dest='job_filename',
                        help='The file name of the job order')
    parser.add_argument('-s', '--scenario', metavar='scenario', dest='scenario_name',
                        help='force use of SCENARIO (normally derived from task-filename and joborder)')
    parser.add_argument('-l', '--log-level', dest='log_level',
                        choices=['debug', 'info', 'progress', 'warning', 'error'],
                        help='force log level')

    args = parser.parse_args()
    if args.info_product is not None:
        print_product_info(args.info_product)
        sys.exit(0)
    return args.task_filename, args.job_filename, args.config_filename, args.scenario_name, args.log_level


def main():
    task_filename, job_filename, config_filename, scenario_name, log_level = parse_command_line()
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
                raise GeneratorError('Parsing inputs failed')
            gen.read_scenario_parameters()
            gen.generate_output()

        logger.info('Task done, exit with code {}'.format(exit_code))

    except (TerminateError, ScenarioError, GeneratorError, IOError):
#        import traceback
#        traceback.print_exc()
        exit_code = 1
        logger.error(str(sys.exc_info()[1]).strip("\n\r"))
        logger.info('Terminate with code {}'.format(exit_code))

    exit(exit_code)


if __name__ == "__main__":
    main()

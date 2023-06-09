'''
Copyright (C) 2021 S[&]T, The Netherlands.

Read JobOrders, according to ESA-EOPG-EEGS-ID-0083 v1.3
'''
import os
import re
import subprocess
import datetime
from typing import List, Optional
from xml.etree import ElementTree as et

from procsim.core.exceptions import ParseError, ProcsimException

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
JOB_ORDER_SCHEMA = os.path.join(THIS_DIR, 'job_order_ESA-EOPG-EEGS-ID-0083.xsd')


class JobOrderInput():
    '''
    Data class describing input product
    '''
    def __init__(self):
        self.id: str
        self.alternative_input_id: str
        self.file_type: str
        self.file_names: List[str] = []

    def __eq__(self, other):
        return self.id == other.id and \
            self.alternative_input_id == other.alternative_input_id and \
            self.file_type == other.file_type and \
            self.file_names == other.file_names


class JobOrderOutput():
    '''
    Data class describing output product
    '''
    def __init__(self):
        self.type: str
        self.dir: str
        self.baseline: int
        self.file_name_pattern: str
        self.toi_start: Optional[datetime.datetime]
        self.toi_stop: Optional[datetime.datetime]


class JobOrderIntermediateOutput():
    '''
    Data class describing an intermediate output file
    '''
    def __init__(self):
        self.id: str    # Identifier of the intermediate output. The Task’s executable shall be able to recognize it.
        self.file_name: str  #


class JobOrderTask():
    '''
    Data class with task parameters
    '''
    def __init__(self):
        self.name: str = ''
        self.version: str = ''
        self.nr_cpu_cores = 0.0     # A value of 0 means no limit
        self.amount_of_ram_mb = 1000000     # limit
        self.disk_space_mb = 1000000        # limit
        self.inputs: List[JobOrderInput] = []
        self.outputs: List[JobOrderOutput] = []
        self.intermediate_outputs: List[JobOrderIntermediateOutput] = []
        self.processing_parameters = {}


class JobOrderParser:
    '''
    This class is responsible for reading (test and parse) the JobOrder.

    Only errors are logged, since the logger is not setup yet (it needs info
    from the JobOrder for that).
    '''
    ISO_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

    @classmethod
    def _time_from_iso(cls, timestr: Optional[str]) -> Optional[datetime.datetime]:
        if timestr is None:
            return None
        if timestr[-1] == 'Z':
            timestr = timestr[:-1]  # strip 'Z', if any
        return datetime.datetime.strptime(timestr, cls.ISO_TIME_FORMAT).replace(tzinfo=datetime.timezone.utc)

    def __init__(self, logger, schema):
        self._logger = logger
        self._is_validated = False
        self._schema = schema
        self.processor_name = ''
        self.processor_version = ''

        # This flag will enable/disable any kind of breakpoint functionality
        # generation implemented by the processor
        self.intermediate_output_enable = True
        self.node = 'N/A'
        self.tasks: List[JobOrderTask] = []
        self.stdout_levels: List[str] = ['INFO', 'PROGRESS', 'WARNING', 'ERROR']
        self.stderr_levels: List[str] = []
        self.toi_start = None
        self.toi_stop = None

    def read(self, filename: str):
        """
        Check against schema, if available, and parse job order.
        """
        if filename is not None:
            self._check_against_schema(filename, self._schema)
            self._parse(filename)

    def _check_against_schema(self, filename, schema):
        cmd = 'xmllint --noout --schema {} {}'.format(
            schema, filename
        )
        xmllint = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = xmllint.stderr.decode('utf-8').strip('\n')
        if 'validates' not in result:
            self._logger.error('Check {} against {}: {}'.format(
                os.path.basename(filename),
                os.path.basename(schema),
                result
            ))
            self._is_validated = False
        else:
            self._is_validated = True

    def _find_matching_files(self, pattern):
        # Return list of all files matching 'pattern'.
        # For now, assume the path is 'fixed' and the regex does not contain slashes.
        rootdir = os.path.dirname(os.path.abspath(pattern))
        files = []
        if os.path.isdir(rootdir):
            for file in os.scandir(rootdir):
                if re.match(pattern, file.path) or os.path.abspath(pattern) == file.path:
                    files.append(file.path)
        else:
            self._logger.warning('Cannot open directory {} (which is used in jobOrder)'.format(rootdir))
        return files

    def _parse(self, filename):
        it = et.iterparse(filename)
        for _, el in it:
            _, _, el.tag = el.tag.rpartition('}')  # strip ns
        root = it.root  # type: ignore
        proc = root.find('Processor_Configuration')
        if proc is None:
            raise ProcsimException('Job order error, Processor_Configuration missing')
        self.processor_name = proc.findtext('Processor_Name')
        self.processor_version = proc.findtext('Processor_Version')
        self.node = proc.findtext('Processing_Node')
        self.stdout_levels = []
        self.stderr_levels = []
        stdout_log_levels = proc.find('List_of_Stdout_Log_Levels')
        if stdout_log_levels is None:
            raise ParseError(stdout_log_levels)
        for level_el in stdout_log_levels.findall('Stdout_Log_Level'):
            self.stdout_levels.append(level_el.text or '')
        stderr_log_levels = proc.find('List_of_Stderr_Log_Levels')
        if stderr_log_levels is None:
            raise ParseError(stderr_log_levels)
        for level_el in stderr_log_levels.findall('Stderr_Log_Level'):
            self.stderr_levels.append(level_el.text or '')
        self.intermediate_output_enable = proc.findtext('Intermediate_Output_Enable') == 'true'
        request = proc.find('Request')
        if request:
            toi = request.find('TOI')
            if toi:
                self.toi_start = self._time_from_iso(toi.findtext('Start'))   # TODO: to datetime
                self.toi_stop = self._time_from_iso(toi.findtext('Stop'))    # to datetime

        # Build list of tasks. Add every input file found to the list of inputs
        tasks = root.find('List_of_Tasks')
        if tasks is None:
            raise ParseError(tasks)
        for task_el in tasks.findall('Task'):
            task = JobOrderTask()
            task.name = task_el.findtext('Task_Name', '')
            task.version = task_el.findtext('Task_Version', '')
            task.nr_cpu_cores = float(task_el.findtext('Number_of_CPU_Cores', '0.0'))
            task.amount_of_ram_mb = int(task_el.findtext('Amount_of_RAM', '1000000'))
            task.disk_space_mb = int(task_el.findtext('Disk_Space', '1000000'))
            task.inputs = []
            task.outputs = []
            task.intermediate_outputs = []

            inputs = task_el.find('List_of_Inputs')
            if inputs is None:
                raise ParseError(inputs)
            for input_el in inputs.findall('Input'):
                input = JobOrderInput()
                input.id = input_el.findtext('Input_ID', '')
                input.alternative_input_id = input_el.findtext('Alternative_ID', '')
                list_of_selected_inputs_el = input_el.find('List_of_Selected_Inputs')
                if list_of_selected_inputs_el:
                    selected_inputs = list_of_selected_inputs_el.findall('Selected_Input')
                    for selected_input in selected_inputs:
                        input.file_type = selected_input.findtext('File_Type', '')
                        list_of_file_names = selected_input.find('List_of_File_Names')
                        if list_of_file_names:
                            for file_name_el in list_of_file_names.findall('File_Name'):
                                # input.file_names.append(file_name_el.text or '')
                                # HACK alert: in ICD2020, there are NO regex filenames, all file names must be fully specified!
                                # This must be patched in the PF (PVML in this case)
                                input.file_names.extend(self._find_matching_files(file_name_el.text))
                task.inputs.append(input)

            outputs = task_el.find('List_of_Outputs')
            if outputs is None:
                raise ParseError(outputs)
            for output_el in outputs.findall('Output'):
                output = JobOrderOutput()
                output.type = output_el.findtext('File_Type', '')
                output.dir = output_el.findtext('File_Dir', '')  # Can be empty or omitted
                output.baseline = int(output_el.findtext('Baseline', '0'))
                output.file_name_pattern = output_el.findtext('File_Name_Pattern', '')
                output.toi_start = self.toi_start  # TOI Start/stop are common for all outputs
                output.toi_stop = self.toi_stop
                task.outputs.append(output)

            if self.intermediate_output_enable:
                intermediate_outputs = task_el.find('List_of_Intermediate_Outputs')
                if intermediate_outputs is None:
                    raise ParseError(intermediate_outputs)
                for int_output_el in intermediate_outputs.findall('Intermediate_Output'):
                    int_output = JobOrderIntermediateOutput()
                    int_output.id = int_output_el.findtext('Intermediate_Output_ID', '')
                    int_output.file_name = int_output_el.findtext('Intermediate_Output_File', '')
                    task.intermediate_outputs.append(int_output)

            # List of processing parameters
            proc_parameters = task_el.find('List_of_Proc_Parameters')
            if proc_parameters is None:
                raise ParseError(proc_parameters)
            for param in proc_parameters.findall('Proc_Parameter'):
                task.processing_parameters[param.findtext('Name')] = param.findtext('Value')

            self.tasks.append(task)


def job_order_parser_factory(icd, logger):
    '''
    Return JobOrderParser. Currently only supports ICD ESA-EOPG-EEGS-ID-0083.
    '''
    if icd == 'ESA-EOPG-EEGS-ID-0083':
        return JobOrderParser(logger, JOB_ORDER_SCHEMA)
    raise ProcsimException('Unknown JobOrder ICD type {}'.format(icd))

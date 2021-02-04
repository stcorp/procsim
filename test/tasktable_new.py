# Copyright (C) 2009-2020 S[&]T, The Netherlands.
#
# Implements abstract classes TaskTable and JobOrder, according to
# ESA-EOPG-EEGS-ID-0083.
#

import datetime
from collections import OrderedDict
try:
    from xml.etree.cElementTree import ElementTree, Element, SubElement, parse
except ImportError:
    from xml.etree.ElementTree import ElementTree, Element, SubElement, parse

# FIXME: duplicated code from PVML
class Struct(object):
    """Generic object in which we can set/get any fields we want"""
    def __repr__(self):
        return self.__dict__.__repr__()


class TaskTableNew(object):
    """
    Object containing all information for a single TaskTable file:
       - variant_config (string)
       - variant_processing_parameter (string)
       - filename: full path to the file
       - processor_name (string)
       - processor_version (string)
       - enable_test (bool)
       - min_disk_space (int, converted to 'bytes' unit)
       - max_time (float, converted to 'seconds' unit)
       - config_files[] (Struct)
         - version (string)
         - filename (string)
       - default_config_file (int, index in config_file[])
       - config_spaces[] (string)
       - enable_sensing_time (bool)
       - processing_parameters (OrderedDict of Struct)
         - name (string)
         - type (string)
         - default (string)
         - valid_list (list of string)
         - mandatory (bool)
       - pools[] (Struct)
         - detached (string)
         - kill_signal (int)
         - tasks (OrderedDict of Struct)
           - name (string)
           - version (string)
           - critical (bool)
           - criticallity_level (int)
           - filename (string)
           - inputs[] (Struct)
             - id (string, None)
             - mode (string)
             - mandatory (bool)
             - alternatives[] (Struct)
               - order (string)
               - origin (string)
               - retrieval_mode (string)
               - t0 (T0) (float, convert units to 'seconds')
               - t1 (T1) (float, convert units to 'seconds')
               - product_type (string)
               - filename_type (string)
               - input_source_data (bool or None)
           - outputs[] (Struct)
             - destination (string)
             - mandatory (string)
             - product_type (string)
             - filename_type (string)
           - breakpoints[] (empty list)
    """

    def __init__(self, tasktable_file):
        self.filename = tasktable_file
        tree = parse(self.filename)
        self.processor_name = tree.find("Processor_Name").text
        self.processor_version = tree.find("Version").text
        self.enable_test = (tree.find("Test").text == "Yes")
        # disk space is always provided in MB
        self.min_disk_space = int(tree.find("Min_Disk_Space").text) * 1024 * 1024
        # time is always provided in seconds
        self.max_time = float(tree.find("Max_Time").text)
        self.default_config_file = 0
        config_element = tree.find("Private_Config")
        if config_element is not None:
            self.variant_config = "Private_Config"
            element = config_element.find("Default")
            if element is not None and element.text:
                self.default_config_file = int(element.text)
        else:
            self.variant_config = "List_of_Cfg_Files"
            config_element = tree
        self.config_files = []
        config_file_elements = config_element.findall("List_of_Cfg_Files/Cfg_File")
        if len(config_file_elements) == 0:
            # Try alternative name (used by Sentinel-1)
            config_file_elements = config_element.findall("List_of_Cfg_Files/Cfg_Files")
        for element in config_file_elements:
            config_file = Struct()
            config_file.version = element.find("Version").text
            config_file.filename = element.find("File_Name").text
            self.config_files.append(config_file)
        self.config_spaces = []
        for element in tree.findall("List_of_Config_Spaces/Config_Space"):
            self.config_spaces.append(element.text)
        self.enable_sensing_time = True
        element = tree.find("Sensing_Time_flag")
        if element is not None:
            if element.text == "false" or element.text == "0":
                self.enable_sensing_time = False
        self.processing_parameters = OrderedDict()
        if tree.find("Processing_Parameters") is not None:
            element_path = "Processing_Parameters/Processing_Parameter"
            self.variant_processing_parameter = "Processing_Parameter"
        else:
            element_path = "List_of_Dyn_ProcParam/Dyn_ProcParam"
            self.variant_processing_parameter = "Dynamic_Processing_Parameter"
        for element in tree.findall(element_path):
            parameter = Struct()
            parameter.name = element.find("Param_Name").text
            parameter.type = element.find("Param_Type").text
            parameter.default = None
            parameter.valid_list = []
            parameter.mandatory = True
            default_element = element.find("Param_Default")
            if default_element is not None:
                parameter.default = element.find("Param_Default").text
            mandatory = element.get("mandatory")
            if mandatory is not None:
                if mandatory == "false":
                    parameter.mandatory = False
            for valid_element in element.findall("Param_Valid"):
                parameter.valid_list.append(valid_element.text)
            self.processing_parameters[parameter.name] = parameter
        self.pools = []
        named_inputs = {}
        for pool_element in tree.findall("List_of_Pools/Pool"):
            pool = Struct()
            pool.detached = pool_element.find("Detached").text
            pool.kill_signal = int(pool_element.find("Killing_Signal").text)
            pool.tasks = OrderedDict()
            for task_element in pool_element.findall("List_of_Tasks/Task"):
                task = Struct()
                task.name = task_element.find("Name").text
                task.version = task_element.find("Version").text
                task.critical = task_element.find("Critical").text in ["true", "1"]
                task.criticality_level = int(task_element.find("Criticality_Level").text)
                task.filename = task_element.find("File_Name").text
                task.inputs = []
                for input_element in task_element.findall("List_of_Inputs/Input"):
                    if input_element.get("ref") is not None:
                        id = input_element.get("ref")
                        if id not in named_inputs:
                            raise Error("task '%s' contains input reference using unknown id '%s'" % (task.name, id))
                        input = named_inputs[id]
                    else:
                        input = Struct()
                        input.id = None
                        if input_element.get("id") is not None:
                            input.id = input_element.get("id")
                        input.mode = input_element.find("Mode").text
                        input.mandatory = (input_element.find("Mandatory").text == "Yes")
                        input.alternatives = []
                        for alternative_element in input_element.findall("List_of_Alternatives/Alternative"):
                            alternative = Struct()
                            order_element = alternative_element.find("Order")
                            alternative.order = 0 if not order_element.text else int(order_element.text)
                            alternative.origin = alternative_element.find("Origin").text
                            alternative.retrieval_mode = alternative_element.find("Retrieval_Mode").text
                            alternative.t0 = datetime.timedelta(seconds=float(alternative_element.find("T0").text))
                            alternative.t1 = datetime.timedelta(seconds=float(alternative_element.find("T1").text))
                            alternative.product_type = alternative_element.find("File_Type").text
                            alternative.filename_type = alternative_element.find("File_Name_Type").text
                            alternative.input_source_data = None
                            source_element = alternative_element.find("Input_Source_Data")
                            if source_element is not None:
                                alternative.input_source_data = source_element.text in ["true", "1"]
                            input.alternatives.append(alternative)
                            if input.id is not None:
                                named_inputs[input.id] = input
                    task.inputs.append(input)
                task.outputs = []
                for output_element in task_element.findall("List_of_Outputs/Output"):
                    output = Struct()
                    output.destination = output_element.find("Destination").text
                    output.mandatory = (output_element.find("Mandatory").text == "Yes")
                    element = output_element.find("Type")
                    if element is None:
                        element = output_element.find("File_Type")
                    output.product_type = element.text
                    output.filename_type = output_element.find("File_Name_Type").text
                    task.outputs.append(output)
                task.breakpoints = []
                pool.tasks[task.name] = task
            self.pools.append(pool)


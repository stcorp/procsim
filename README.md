# Procsim
In the Payload Data Ground Segment (PDGS) of a satellite mission, the data processing functionality is handled by at least one Processing Facility (PF) which integrates one or more processors.
The PF is responsible of the processing orchestration, implementing the logic to: prepare the input data for the processing, trigger the processing (performed by the processors), collect the output data.
The processor is the entity responsible of the data processing and is composed by one or more Tasks.

Tasks (executables) are called by the PF with a single command line argument: the file name of a JobOrder file. The JobOrder contains information for the Task, such as processing parameters, location of input data and which output data is expected.

This tool, Procsim, can be used to simulate a generic Task, in order to test the interface between the Processing Facility and the software implementing the Task.

Procsim does not do any 'real' processing, but reads and interprets the JobOrder, consumes resources (CPU, disk and memory) and generates output data with correct directory/file names and valid Main Product Headers.

# Installation instructions
To use procsim, you will need:

 - A Unix-based operating system (e.g. Linux).

 - Python version 3.6 or higher.

 - The xmllint program, included with most Linux distributions. If missing, you can either install the libxml2 package using the package manager of your Unix distribution or download/install the package from http://xmlsoft.org/. After installation, make sure that the xmllint executable is in your executable path (i.e. the directory location where it is in should be in your PATH environment setting).

Procsim is command-line based. The package consists of directory 'procsim', containing the core application, and one or more subdirectories containing the mission-specific plugins. 

To install, unzip/untar the procsim installation package and to a location of your choice.

# Usage
For every Task to be simulated, you need:

 - a shell script that will be called by the PF, instead of the 'real' processor task. This script should in turn execute procsim.py.

 - a 'scenario', describing the desired behavior of procsim for this specific Task. The scenarios are defined in configuration files.

## Shell script
The PF calls the processor with only one argument, the name of the JobOrder file. The shell script, used to redirect the PF's call, should call procsim with the following arguments: 

  - `-t`, followed by the name of the script, as called by the PF

  - `-j`, followed by the name of the job order file

  - the name of the procsim configuration file.
 
Example:

```
#!/bin/sh
<path_to_procsim>/procsim.py -t $0 -j $1 <path_to_config_file>
```
Optionally, you can specify a specific scenario using `-s` followed by the name of the scenario.

## Scenario configuration
Procsim can act as a stub for all kind of processors. Its behavior is determined by a so-called 'scenario'. A scenario specifies e.g. the amount of resources (CPU/memory/disk) to be used, the time procsim should sleep and the output products to be generated. 

The scenarios are described in JSON configuration files. C-style comments and trailing comma's at the end of lists and objects are allowed. Date/times should be specified as strings in ISO format, such as `"2021-02-01T00:24:32.000Z"`

A configuration file can contain one or multiple scenarios. The scenario is selected by automatically using the combination of task file name (i.e. the name of the executable called by the PF) and the JobOrder contents, or manually using an additonal command line parameter.

The configuration file is structured as following:
```
{
  "mission": "biomass",
  "job_order_schema": "/home/jenkins/procsim/joborder.xsd",

  "scenarios": [
      // Array with scenarios
  ]
}
```
A JSON editor with syntax checking and coloring, such as Visual Studio Code, is recommended to create and edit the configuration files.
The parameters are described below.

- `mission` : string, mandatory. Must match the name of plugin, in this case biomass.

- `job_order_schema` : string, optional. Should point to the XML schema used to validate the JobOrder.

- `scenarios` : array of objects, mandatory. This section contains one or more scenarios.

An example scenario:
```
    {
      // Task #5
      "name": "L0 step 5, Consolidation of External Calibration Standard products",

      "file_name": "level0_task5.sh",
      "processor_name": "l0_ec",
      "processor_version": "01.01",
      "task_name": "Step5",
      "task_version": "05.03L01",

      "logging": [
        {
          "level": "info",
          "message": "Procsim log message"
        }
      ],

      // resources
      "processing_time": 60,   // in seconds
      "nr_progress_log_messages": 4,
      "nr_cpu": 1,
      "memory_usage": 100,     // in MB
      "disk_usage": 100,       // in MB

      "outputs": [
        {
          "type": "EC_RAW__0S",
          "size": 0,   // in MB
          "enable": true,
          "metadata_source": ".*EC_RAWP_0S.*"
        }
      ],
      "exit_code": 0
    },
```
The parameters are described below.

- `name` : string, mandatory. Used for logging, and can be specified on the command line to select a specific scenario.

- `file_name` : string, mandatory. Must match the `-t` command line parameter.

- `processor_name`, `processor_version`, `task_name` and `task_version` : string, mandatory. Used to find the matching task in the JobOrder and must match the corresponding fields in the JobOrder.

- `logging` : array of objects, optional. Procsim produces many log messages, formatted and filtered according to the settings in the JobOrder. An optional list with additional log messages can be specified and will be logged.

  - `level` : string, optional. Specifies the log level and can be `"debug", "info", "progress", "warning" or "error"`.

  - `message` : string, mandatory. The message to be logged.

- `processing_time`, `nr_progress_log_messages`, `nr_cpu`, `memory_usage`, `disk_usage` : number, optional. After reading the configuration and the job order, procsim will 'work' for a while, consuming memory, disk space and CPU cycles, and producing progress log messages. The defaults are zero (no cpu-time spent, no memory/disk used, no progress log messages produced). Note that resouce usage is limited by the values in the JobOrder, if present.

- `outputs` : array, mandatory. The section 'outputs' contains one or more output products to be generated.

  - `type` : string, mandatory. Specifies the product type. Procsim contains 'product generators' for many product types. Use the command `procsim.py -h` to get a list with supported product types.

  - `size` : number, optional. Specifies the size of the product's 'data' file(s) in MB. In case of products with multiple binary files, `size` specifies the total size, divided over the separate files. If not set, minimal sized files are produced (a few bytes).

 - `enable` : boolean, optional. When set to false, a warning is logged and this output product is not generated. Default is true.

  - `metadata_source` : string, optional. Regular expression, used to specify the input product which is used as a first source for the metadata in the output product. Think of parameters such as validity start/stop times, mission phase, etc., these are copied from the metadata source product.

  - `exit_code` : number, optional. Default is 0.

### Metadata parameters
Most metadata will be copied from an input source. Some metadata is set by the output product generator, such as the product type, the processor name and the processor version (all read from the scenario) and the baseline version (read from the JobOrder). Some output product generators set additional fields as well, such as the 'slice number'.

Metadata parameter values can be specified in the scenario. If already read from the `metadata_source`, they will be overwritten. Parameter values can be placed in the scenario 'root' (common for all output products) or in a specific output section. 

Example:
```
      "mission_phase": "Tomographic",
      "outputs": [
        {
          "type": "AC_RAW__0A",
          "metadata_source": ".*EC_RAW__0M.*",
          "swath": "AC",
          "operational_mode": "AC",
        },
```
This scenario sets the mission_phase to "Tomographic" for all output products, and the swath and operational mode of the AC_RAW__0A product to "AC".
A list with all supported metadata parameters can be retrieved using 'procsim -h <mission> <product_type>'. This command also shows other product-specific details and scenario options. Example:
```
procsim.py -h biomass S1_RAW__0S
```

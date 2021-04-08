# Procsim
In the Payload Data Ground Segment (PDGS) of a satellite mission, the data processing functionality is handled by at least one Processing Facility (PF) which integrates one or more processors.
The PF is responsible of the processing orchestration, implementing the logic to: prepare the input data for the processing, trigger the processing (performed by the processors), collect the output data.
The processor is the entity responsible of the data processing and is composed by one or more Tasks.

Tasks (executables) are called by the PF with a single command line argument: the file name of a JobOrder file. The JobOrder contains information for the Task, such as processing parameters, location of input data and which output data is expected.

This tool, Procsim, can be used to simulate a generic Task, in order to test the interface between the Processing Facility and the software implementing the Task.

Procsim does not do any 'real' processing, but reads and interprets the JobOrder, consumes resources (CPU, disk and memory) and generates output data with correct directory/file names and valid Main Product Headers.

During execution, logging is produced, with log levels according to those specified in the JobOrder. However, log levels can be overruled on the command line or in the configuration file. The program exits with an exit code which can be specified.

# Installation instructions
To use procsim, you will need:

 - A Unix-based operating system (e.g. Linux).

 - Python version 3.6 or higher.

 - The xmllint program, included with most Linux distributions. If missing, you can either install the libxml2 package using the package manager of your Unix distribution or download/install the package from http://xmlsoft.org/. After installation, make sure that the xmllint executable is in your executable path (i.e. the directory location where it is in should be in your PATH environment setting).

Procsim is distributed as a source distribution created using `setuptools`. It can be installed in several ways, for example using pip or by invoking setup.py manually. Note: installation using setup.py requires super user privileges in most cases.

Using setup.py:
```
$ tar xvfz <procsim_package_name>.tar.gz
$ cd <procsim_package_name>
$ python3 setup.py install
```

Using pip:
```
$ pip install <procsim_pacakge>.tar.gz
```

Procsim is a command-line based tool. To test the installation, enter:
 ```
$ procsim --version
 ```

# Usage
For every Task to be simulated, you need:

 - a shell script that will be called by the PF, instead of the 'real' processor task. This script should in turn call `procsim`.

 - a 'scenario', describing the desired behavior of procsim for this specific Task. The scenarios are defined in configuration files.

## Shell script
The PF calls the processor with only one argument, the name of the JobOrder file. The shell script, used to redirect the PF's call, should call procsim with the following arguments: 

  - `-t`, followed by the name of the script, as called by the PF

  - `-j`, followed by the name of the job order file

  - the name of the procsim configuration file.
 
The script will look like this:
```
#!/bin/sh
procsim -t $0 -j $1 <path_to_config/configfile>
```
Optionally, you can specify a specific scenario using `-s`, followed by the name of the scenario.

## Scenario configuration
Procsim can act as a stub for all kind of processors. Its behavior is determined by a 'scenario'. A scenario specifies e.g. the amount of resources (CPU/memory/disk) to be used, the time procsim should sleep and the output products to be generated. 

The scenarios are described in JSON configuration files. C-style comments and trailing comma's at the end of lists and objects are allowed. Date/times should be specified as strings in ISO format, such as `"2021-02-01T00:24:32.000Z"`

A configuration file can contain one or multiple scenarios. The scenario is selected by automatically using the combination of task file name (i.e. the name of the executable called by the PF) and the JobOrder contents, or manually using an additonal command line parameter.

The configuration file is structured as following:
```
{
  "mission": "biomass",
  "log_level": "debug",
  "scenarios": [
      // Array with scenarios
  ]
}
```
A JSON editor with syntax checking and coloring, such as Visual Studio Code, is recommended to create and edit the configuration files.
The parameters are described below.

- `mission` : string, mandatory. Must match the name of plugin, in this case biomass.

- `log_level` : string, optional. Log level, can be debug, info, progress, warning, error. Overrules the level in the jobOrder, if any. Default is 'info'.

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

      "log_level": "debug",
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

- `log_level` : string, optional. Log level, can be debug, info, progress, warning, error. Overrules the `log_level` in the root of the configuration, if any, or the level in the jobOrder, if any. Default is 'info'.

- `logging` : array of objects, optional. Procsim produces many log messages, formatted and filtered according to the settings in the JobOrder. An optional list with additional log messages can be specified and will be logged.

  - `level` : string, optional. Specifies the log level and can be `"debug", "info", "progress", "warning" or "error"`.

  - `message` : string, mandatory. The message to be logged.

- `processing_time`, `nr_progress_log_messages`, `nr_cpu`, `memory_usage`, `disk_usage` : number, optional. After reading the configuration and the job order, procsim will 'work' for a while, consuming memory, disk space and CPU cycles, and producing progress log messages. The defaults are zero (no cpu-time spent, no memory/disk used, no progress log messages produced). Note that resouce usage is limited by the values in the JobOrder, if present.

- `outputs` : array, mandatory. The section 'outputs' contains one or more output products to be generated. Per product, you can specify:

  - `type` : string, mandatory. Specifies the product type. Procsim contains 'product generators' for many product types. Use the command `procsim -i` to get a list with supported product types.

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

A list with all supported parameters for a specific output type can be retrieved using `procsim -i [product_type]`.

Example:
```
$ procsim -i AC_RAW__0A

AC_RAW__0A product generator details:
-------------------------------------

    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 ancillary products.

    Inputs are a Sx_RAW__0M product and all RAWS022_10 belonging to the same
    data take.
    The output reads the begin/end times of the monitoring product and adds the
    leading/trailing margins as specified in the job order or the scenario.
    (defaults is 16/0 seconds).
    
Supported scenario parameters for product type AC_RAW__0A are:
   - baseline (int)
   - begin_position (date)
   - end_position (date)
   - num_l0_lines (str)
   - num_l0_lines_corrupt (str)
   - num_l0_lines_missing (str)
   - swath (str)
   - operational_mode (str)
   - mission_phase (str)
   - data_take_id (int)
   - global_coverage_id (str)
   - major_cycle_id (str)
   - repeat_cycle_id (str)
   - track_nr (str)
   - slice_frame_nr (int)
   - output_path (str)
   - leading_margin (float)
   - trailing_margin (float)
```

# Sample code
Directory `examples` contains examples of scenario configurations, job orders and scripts to demonstrate them.

# Program flow
The next section describes the program flow during normal execution of procsim.

### Init phase
- Parse command line arguments.
- Install signal handler. On 'SIGTERM' or 'SIGINT', a log message is produced and the program terminates.
- Parse scenario configuration file.
- Parse Job Order file.
- Try to find a matching scenario and job order task.
- Produce logging:
  - name of the scenario
  - job order file
  - inputs
  - processor parameters
  - user log messages, as defined in the scenario.

### Processing
- 'Processing' starts: procsim eats resources for the specified amount of time. Note that limits in the job order (i.e. regarding cpu/memory usage) prevail over the scenario resource parameters.

### Output generation
- Generate intermediate files, if specified in the job order.
- For every output product specified in the job order:
  - Walk over input products. For every input:
    - Unzip, if needed.
    - Check if product is a directory.
    - If a pattern is specified for the 'metadata source' in the scenario, this product's metadata is set as metadata for the output.
    - For some output products, additional information is parsed from the input products.
  - Apply the scenario parameters to this output. E.g., specified metadata is set/overwritten.
  - Generate output products.

### Program termination
- The program exits with the exit code as defined in the scenario (default 0).

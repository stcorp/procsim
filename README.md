# Procsim

## Introduction
In the PDGS, the data processing functionality is handled by at least one Processing Facility (PF) which integrates one or more processors.
The PF is responsible of the processing orchestration, implementing the logic to: prepare the input data for the processing, trigger the processing (performed by the processors), collect the output data.
The processor is the entity responsible of the data processing and is composed by one or more Tasks.

Tasks (executables) are called by the PF with a single command line argument: the file name of a JobOrder file. The JobOrder contains information for the Task, such as processing parameters, location of input data and which output data is expected.

Procsim can be used to simulate a generic Task, in order to test the  nterface between the Processing Facility and the software implementing the Task.
Procsim does not process the input data. However, it reads and interprets the JobOrder, uses resources (CPU, disk and memory) and generates dummy output data.

## Installation instructions
To be able to use procsim, you will need:
- A Unix-based operating system (e.g. Linux).
- Python version 3.6 or higher.

The tool consists of a core application and mission-specific plugin files.

Instructions:
- Copy the directory tree containing the software to your file system.

## Usage
For every Task to be simulated, you should create a bash script with the desired name on the desired location. The path of the script should be in the TaskTable and will be called by the management layer of the PF.

This script should execute procsim.py with the first two parameters the script was called ($0 and $1), followed by the name of the procsim configuration file. Example:

```
#!/bin/sh
python /home/user/procsim/procsim.py $0 $1 /home/user/procsim_config.json
```

## Procsim Configuration
The simulation settings are stored in a JSON file. The configuration can hold settings for one or multiple tasks.

# Procsim

## Introduction
In the PDGS, the data processing functionality is handled by at least one Processing Facility (PF) which integrates one or more processors.
The PF is responsible of the processing orchestration, implementing the logic to: prepare the input data for the processing, trigger the processing (performed by the processors), collect the output data.
The processor is the entity responsible of the data processing and is composed by one or more Tasks.

Tasks (executables) are called by the PF with a single command line argument: the file name of a JobOrder file. The JobOrder contains information for the Task, such as processing parameters, location of input data and which output data is expected.

Procsim can be used to simulate a generic Task, in order to test the  nterface between the Processing Facility and the software implementing the Task.

## Installation instructions
To be able to use procsim, you will need:
- A Unix-based operating system (e.g. Linux).
- Python version 3.6 or higher.

Copy the directory tree to somewhere in the file system.

## Usage
For every Task to be simulated, you should create a bash script with the desired name on the desired location. 
This script should execute procsim.py with the first two parameters the script was called ($0 and $1), followed by the name of the procsim configuration file.

## Procsim Configuration
The simulation settings are stored in a JSON file. The configuration can hold settings for one or multiple tasks. 

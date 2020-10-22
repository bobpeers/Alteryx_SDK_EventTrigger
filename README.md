# Alteryx SDK Event Trigger
Alteryx SDK Tool to wait for a file system event before allowing records to flow

Custom Alteryx SDK tool that will wait for file system events before allowing records to flow through. Events can be either folder or file events:
- Change event (editing, renaming etc.)
- Delete event (file/folder is deleted, note that renaming also triggers this event)
- Add event (file/folder is created, note that renaming also triggers this event)

## Installation
Download the yxi file and double click to install in Alteyrx. 

<img src="https://github.com/bobpeers/Alteryx_SDK_Event_Trigger/blob/main/images/EventTrigger_Install.png" width="600" alt="Event Trigger Install Dialog">

The tool will be installed in the __Filesystem__ category.

<img src="https://github.com/bobpeers/Alteryx_SDK_Event_Trigger/blob/main/images/EventTrigger_toolbar.png" width="400" alt="Event Trigger Install Toolbar">

## Requirements

None, uses standard Python libraries.

## Usage
Configure the tool to either monitor file or folder events.
For folders just select the folder to monitor and the type of event to monitor. The folder does not need to exist beforehand so you can wait for a given folder to be created.
For files select the folder and a file specification as well as the events types to monitor. As with folders the file does not need to exist beforehand so you can wait for a given file to be created.

The timout is how many secods the workflow will wait before continuing. If an event is triggered before the timeout data will pass out of the top (O) output, otherwise the timeout will trigger and data will pass out of the lower (E) output.

## Outputs
The output will be a copy of the input data.

## Usage
This workflow demonstrates the tool in use and the output data. The workflow shown here:

<img src="https://github.com/bobpeers/Alteryx_SDK_Event_Trigger/blob/main/images/EventTrigger_workflow.png" width="1000" alt="Event Trigger Workflow">

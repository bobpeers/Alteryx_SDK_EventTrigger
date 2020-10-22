import AlteryxPythonSDK as Sdk
import xml.etree.ElementTree as Et
import os, time
from fnmatch import fnmatch

class AyxPlugin:
    def __init__(self, n_tool_id: int, alteryx_engine: object, output_anchor_mgr: object):
        # Default properties
        self.n_tool_id: int = n_tool_id
        self.alteryx_engine: Sdk.AlteryxEngine = alteryx_engine
        self.output_anchor_mgr: Sdk.OutputAnchorManager = output_anchor_mgr

        # Custom properties
        self.event_type: str = None
        self.event_folder: str = None
        self.event_filespec: str = None
        self.event_file: str = None
        self.event_timeout: int = None
        self.event_additions: bool = False
        self.event_deletions: bool = False
        self.event_changes: bool = False

        # control which record is being pushed
        self.first_record: bool = True

        self.is_initialized = True
        
        self.input: IncomingInterface = None
        self.output: Sdk.OutputAnchor = None
        self.error_output : sdk.OutputAnchor = None


    def pi_init(self, str_xml: str):

        # Getting the output anchor from Config.xml by the output connection name
        self.output = self.output_anchor_mgr.get_output_anchor('Output')
        self.error_output = self.output_anchor_mgr.get_output_anchor("Error")
        
        # Getting the dataName data property from the Gui.html
        root = Et.fromstring(str_xml)
        # get radio value
        self.event_type = root.find('event_type').text if 'event_type' in str_xml else None
        # folder
        self.event_folder = root.find('monitor_dir').text if 'monitor_dir' in str_xml else None
        # filespec
        self.event_filespec= root.find('filespec').text if 'filespec' in str_xml else None
        # file
        self.event_file = root.find('monitor_file').text if 'monitor_file' in str_xml else None

        # event triggers
        self.event_additions = root.find('additions').text == 'True' if 'additions' in str_xml else None
        self.event_deletions = root.find('deletions').text == 'True' if 'deletions' in str_xml else None
        self.event_changes = root.find('changes').text == 'True' if 'changes' in str_xml else None

        # timeout
        self.event_timeout = int(root.find('timeout').text) if 'timeout' in str_xml else None


        # Validity checks.
        if self.event_type == 'event_folder':
            if self.event_folder is None:
                self.display_error_msg('Select a folder to monitor.')
            elif not os.path.exists(self.event_folder):
                self.display_error_msg(f'Folder {self.event_folder} doesn\'t exist')
            elif self.event_filespec is None:
                self.display_error_msg('Select a file specification to monitor.')
        else:
            if self.event_file is None:
                self.display_error_msg('Select a file to monitor.')
            elif not os.path.exists(os.path.dirname(self.event_file)):
                self.display_error_msg(f'Folder {os.path.dirname(self.event_file)} doesn\'t exist')

        if not self.event_additions and not self.event_deletions and not self.event_changes:
            self.display_error_msg('Select at least one event type to monitor (additions, deletions or changes).')


    def pi_add_incoming_connection(self, str_type: str, str_name: str) -> object:
        self.input = IncomingInterface(self)
        return self.input

    def pi_add_outgoing_connection(self, str_name: str) -> bool:
        return True

    def pi_push_all_records(self, n_record_limit: int) -> bool:
        self.alteryx_engine.output_message(self.n_tool_id, Sdk.EngineMessageType.error, 'Missing Incoming Connection.')
        return False

    def pi_close(self, b_has_errors: bool):
        self.output.assert_close()
        self.error_output.assert_close()

    def display_error_msg(self, msg_string: str):
        self.alteryx_engine.output_message(self.n_tool_id, Sdk.EngineMessageType.error, msg_string)
        self.is_initialized = False

    def display_info(self, msg_string: str):
        self.alteryx_engine.output_message(self.n_tool_id, Sdk.EngineMessageType.info, msg_string)

class IncomingInterface:
    def __init__(self, parent: AyxPlugin):
        # Default properties
        self.parent: AyxPlugin = parent

        # Custom properties
        self.record_copier: Sdk.RecordCopier = None
        self.record_creator: Sdk.RecordCreator = None

        self.timedout = True

    def ii_init(self, record_info_in: Sdk.RecordInfo) -> bool:
        # Make sure the user provided a field to parse

        # Returns a new, empty RecordCreator object that is identical to record_info_in.
        record_info_out = record_info_in.clone()

        # Lets the downstream tools know what the outgoing record metadata will look like
        self.parent.output.init(record_info_out)
        self.parent.error_output.init(record_info_out)
        
        # Creating a new, empty record creator based on record_info_out's record layout.
        self.record_creator = record_info_out.construct_record_creator()

        # Instantiate a new instance of the RecordCopier class.
        self.record_copier = Sdk.RecordCopier(record_info_out, record_info_in)
        
        # Map each column of the input to where we want in the output.
        for index in range(record_info_in.num_fields):
            # Adding a field index mapping.
            self.record_copier.add(index, index)

        # Let record copier know that all field mappings have been added.
        self.record_copier.done_adding()
        
        return True

    def ii_push_record(self, in_record: Sdk.RecordRef) -> bool:
        # Copy the data from the incoming record into the outgoing record.
        self.record_creator.reset()
        self.record_copier.copy(self.record_creator, in_record)

        if self.parent.alteryx_engine.get_init_var(self.parent.n_tool_id, 'UpdateOnly') == 'True' or not self.parent.is_initialized:
            return False

        if self.parent.first_record:
            polling = 5
            progress = 0

            self.parent.display_info(f'Monitoring events for :{self.parent.event_timeout} seconds')

            if self.parent.event_type == 'event_folder':
                path_to_watch = self.parent.event_folder
                self.parent.display_info(f'Monitoring path:{self.parent.event_folder} for files matching {self.parent.event_filespec}')
            else:
                path_to_watch = os.path.dirname(self.parent.event_file)
                self.parent.event_filespec = os.path.split(self.parent.event_file)[1]
                self.parent.display_info(f'Monitoring file {self.parent.event_file}')

            self.parent.display_info(f'Monitoring events: Additions {"✅" if self.parent.event_additions else "❌"} Deletions {"✅" if self.parent.event_deletions else "❌"} Changes {"✅" if self.parent.event_changes else "❌"}')

            before = dict([(f, os.path.getmtime(os.path.join(path_to_watch, f))) for f in os.listdir(path_to_watch) if fnmatch(f, self.parent.event_filespec)])
            
            while progress < self.parent.event_timeout:
                time.sleep (polling)
                after = dict([(f, os.path.getmtime(os.path.join(path_to_watch, f))) for f in os.listdir(path_to_watch) if fnmatch(f, self.parent.event_filespec)])

                added = [f for f in after if not f in before]
                removed = [f for f in before if not f in after]
                changed = [f for f in before if f in after and before[f] != after[f]]

                if self.parent.event_additions and  added :
                    self.parent.display_info(f'Added:{", ".join(added)}')
                    self.timedout = False
                    break
                if self.parent.event_deletions and removed:
                    self.parent.display_info(f'Removed:{", ".join(removed)}')
                    self.timedout = False
                    break
                if self.parent.event_changes and  changed:
                    self.parent.display_info(f'Changed:{", ".join(changed)}')
                    self.timedout = False
                    break

                before = after
                progress += polling

            if self.timedout:
                self.parent.display_info('Timeout occured without capturing any events.')

        self.parent.first_record = False

        out_record = self.record_creator.finalize_record()
        if self.timedout:
            self.parent.error_output.push_record(out_record)
        else:
            self.parent.output.push_record(out_record)

        return True

    def ii_update_progress(self, d_percent: float):
        # Inform the Alteryx engine of the tool's progress.
        self.parent.alteryx_engine.output_tool_progress(self.parent.n_tool_id, d_percent)

        # Inform the outgoing connections of the tool's progress.
        self.parent.output.update_progress(d_percent)

    def ii_close(self):
        # Close outgoing connections.
        self.parent.output.close()
        self.parent.error_output.close()

# file_protocol.py

import json
import logging
import shlex
from file_interface import FileHandler

"""
* ProtocolHandler class processes incoming data 
* and validates it against the defined protocol rules
* 
* Client data arrives as bytes which gets converted
* to string for processing
"""
class ProtocolHandler:
    def __init__(self):
        self.file_handler = FileHandler()
        
    def process_request(self, request_string=''):
        logging.warning(f"Processing request of length: {len(request_string)}")
        try:
            if not request_string.strip():
                return json.dumps({'status': 'FAILED', 'error': 'Empty request'})

            parts = request_string.split(maxsplit=1)
            command = parts[0].strip().lower()
            params = []
            
            if len(parts) > 1:
                if command == "upload":
                    # Special handling for file uploads
                    param_parts = parts[1].split(maxsplit=1)
                    params = param_parts
                else:
                    try:
                        params = shlex.split(parts[1])
                    except ValueError as e:
                        logging.warning(f"Parameter parsing error: {e}")
                        params = parts[1].split()
            
            logging.warning(f"Executing: {command} with {len(params)} params")
            
            if hasattr(self.file_handler, self._map_command(command)):
                method = getattr(self.file_handler, self._map_command(command))
                response = method(params)
                return json.dumps(response)
            return json.dumps({'status': 'FAILED', 'error': 'Invalid command'})
        except Exception as e:
            logging.warning(f"Processing error: {e}")
            return json.dumps({'status': 'FAILED', 'error': f'Processing error: {e}'})
    
    def _map_command(self, cmd):
        command_map = {
            'list': 'list_files',
            'get': 'retrieve_file',
            'upload': 'save_file',
            'delete': 'remove_file'
        }
        return command_map.get(cmd, cmd)


if __name__ == '__main__':
    # Example usage
    protocol = ProtocolHandler()
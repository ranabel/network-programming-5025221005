# file_interface.py

import os
import json
import base64
from pathlib import Path

class FileHandler:
    def __init__(self):
        current_dir = Path(__file__).parent.absolute()
        files_dir = current_dir / 'files'
        os.chdir(files_dir)

    def list_files(self, args=None):
        if args is None:
            args = []
        try:
            files = [f for f in os.listdir() if os.path.isfile(f)]
            return {'status': 'SUCCESS', 'files': files}
        except Exception as err:
            return {'status': 'FAILED', 'error': str(err)}

    def retrieve_file(self, args=None):
        if args is None:
            args = []
        try:
            if not args or not args[0]:
                return {'status': 'FAILED', 'error': 'Filename required'}
            
            target_file = args[0]
            with open(target_file, 'rb') as file:
                content = base64.b64encode(file.read()).decode()
            
            return {
                'status': 'SUCCESS',
                'filename': target_file,
                'content': content
            }
        except Exception as err:
            return {'status': 'FAILED', 'error': str(err)}
    
    def save_file(self, args=None):
        if args is None:
            args = []
        try:
            if len(args) < 2:
                return {'status': 'FAILED', 'error': 'Missing parameters'}
            
            filename, file_data = args[0], base64.b64decode(args[1])
            with open(filename, 'wb') as file:
                file.write(file_data)
            
            return {'status': 'SUCCESS', 'message': 'File saved'}
        except Exception as err:
            return {'status': 'FAILED', 'error': str(err)}
    
    def remove_file(self, args=None):
        if args is None:
            args = []
        try:
            if not args:
                return {'status': 'FAILED', 'error': 'Filename required'}
            
            filename = args[0]
            if os.path.exists(filename):
                os.unlink(filename)
                return {'status': 'SUCCESS', 'message': 'File deleted'}
            return {'status': 'FAILED', 'error': 'File not found'}
        except Exception as err:
            return {'status': 'FAILED', 'error': str(err)}


if __name__ == '__main__':
    handler = FileHandler()
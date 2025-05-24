import os
import json
import base64
from glob import glob

class FileInterface:
    def __init__(self):
        os.chdir('files/')

    def list(self, params=[]):
        try:
            filelist = glob('*.*')
            return dict(status='OK', data=filelist)
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def get(self, params=[]):
        try:
            filename = params[0]
            if not filename:
                return None
            with open(filename, 'rb') as fp:
                isifile = base64.b64encode(fp.read()).decode()
            return dict(status='OK', data_namafile=filename, data_file=isifile)
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def upload(self, params=[]):  
        try:
            filename = params[0]
            file_content = base64.b64decode(params[1])
            with open(filename, 'wb') as fp:
                fp.write(file_content)
            return dict(status='OK', data=f"UPLOAD {filename} Success")
        except Exception as e:
            return dict(status='ERROR', data=str(e))
            
    def delete(self, params=[]):
        try:
            filename = params[0]
            if not filename:
                return dict(status='ERROR', data='Filename empty')
            os.remove(filename)
            return dict(status='OK', data=f"DELETE {filename} Success")
        except Exception as e:
            return dict(status='ERROR', data=str(e))
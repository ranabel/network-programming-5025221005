import os
import socket
from glob import glob
from datetime import datetime
import logging

class HttpServer:
    """
    HTTP Server yang mendukung operasi file: list, upload, delete
    Dengan logging yang enhanced
    """
    
    def __init__(self):
        self.sessions = {}
        self.types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.zip': 'application/zip',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.bin': 'application/octet-stream'
        }
        # Setup logger untuk HTTP server
        self.logger = logging.getLogger('HttpServer')
    
    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers={}):
        """
        Membuat HTTP response dengan format yang benar
        """
        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append(f"HTTP/1.1 {kode} {message}\r\n")
        resp.append(f"Date: {tanggal}\r\n")
        resp.append("Connection: close\r\n")
        resp.append("Server: FileServer/2.0\r\n")
        resp.append(f"Content-Length: {len(messagebody)}\r\n")
        
        # Tambahkan headers custom
        for key, value in headers.items():
            resp.append(f"{key}: {value}\r\n")
        
        resp.append("\r\n")
        
        # Gabungkan headers
        response_headers = ''.join(resp)
        
        # Pastikan messagebody dalam bytes
        if type(messagebody) is not bytes:
            messagebody = messagebody.encode('utf-8')
        
        response = response_headers.encode('utf-8') + messagebody
        
        # Log response yang dibuat
        self.logger.info(f"📤 Generated response: {kode} {message} ({len(messagebody)} bytes)")
        
        return response
    
    def proses(self, headers, body):
        """
        Memproses HTTP request berdasarkan method dan path
        """
        try:
            requests = headers.split("\r\n")
            baris = requests[0]
            all_headers = [n for n in requests[1:] if n != '']
            
            j = baris.split(" ")
            method = j[0].upper().strip()
            object_address = j[1].strip()
            
            # Enhanced logging - TAMPILKAN DI CONSOLE JUGA
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"🔄 [{timestamp}] HTTP Server processing: {method} {object_address}")
            
            # Log headers jika verbose
            if len(all_headers) > 0:
                print(f"📋 Request headers: {len(all_headers)} lines")
            
            # Log body size jika ada
            if body and len(body) > 0:
                print(f"📦 Request body: {len(body)} bytes")
            
            # Route berdasarkan method
            if method == 'GET':
                print(f"📥 Processing GET request untuk {object_address}")
                result = self.http_get(object_address, all_headers)
                print(f"✅ GET {object_address} - completed")
                return result
            elif method == 'POST':
                print(f"📤 Processing POST (upload) ke {object_address}")
                result = self.http_post(object_address, all_headers, body)
                print(f"✅ POST {object_address} - completed")
                return result
            elif method == 'DELETE':
                print(f"🗑️  Processing DELETE untuk {object_address}")
                result = self.http_delete(object_address, all_headers)
                print(f"✅ DELETE {object_address} - completed")
                return result
            else:
                print(f"⚠️  Unsupported method: {method}")
                return self.response(405, 'Method Not Allowed', 'Method tidak didukung', {})
                
        except (IndexError, ValueError) as e:
            print(f"❌ Bad request: {str(e)}")
            return self.response(400, 'Bad Request', f'Request tidak valid: {str(e)}', {})
        except Exception as e:
            print(f"❌ Server error dalam proses: {str(e)}")
            return self.response(500, 'Internal Server Error', f'Server error: {str(e)}', {})
    
    def http_get(self, object_address, headers):
        """
        Menangani GET request untuk download file atau list direktori
        """
        print(f"📥 GET handler: {object_address}")
        
        # Jika path berakhir dengan '/', tampilkan list file
        if object_address == '/' or object_address.endswith('/'):
            print(f"📁 Listing directory: {object_address}")
            return self.list_directory(object_address)
        
        # Handle special endpoints
        if object_address == '/files' or object_address == '/list':
            print(f"📁 Special endpoint for file listing")
            return self.list_directory('/')
        
        # Endpoint khusus lainnya
        if object_address == '/info':
            print(f"ℹ️  Info endpoint accessed")
            return self.response(200, 'OK', 'HTTP File Server - Support GET, POST, DELETE', {})
        if object_address == '/status':
            file_count = len([f for f in os.listdir('.') if os.path.isfile(f)])
            status_msg = f'Server aktif. Total file: {file_count}'
            print(f"📊 Status endpoint: {file_count} files")
            return self.response(200, 'OK', status_msg, {})
        
        # Download file
        print(f"⬇️  Download request untuk: {object_address}")
        return self.download_file(object_address)
    
    def list_directory(self, path):
        """
        Menampilkan daftar file dalam direktori
        """
        try:
            # Tentukan direktori yang akan di-list
            if path == '/' or path == '':
                target_dir = '.'
            else:
                target_dir = '.' + path
            
            print(f"📂 Scanning directory: {target_dir}")
            
            if not os.path.isdir(target_dir):
                print(f"❌ Directory not found: {target_dir}")
                return self.response(404, 'Not Found', 'Direktori tidak ditemukan', {})
            
            # Ambil daftar file
            files = []
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    modified = datetime.fromtimestamp(os.path.getmtime(item_path))
                    files.append({
                        'name': item,
                        'size': size,
                        'modified': modified.strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            # Urutkan berdasarkan nama
            files.sort(key=lambda x: x['name'])
            
            print(f"📋 Found {len(files)} files in directory")
            
            # Buat response HTML yang lebih menarik
            html_content = self.generate_file_list_html(files, path)
            
            return self.response(200, 'OK', html_content, {'Content-Type': 'text/html; charset=utf-8'})
            
        except Exception as e:
            print(f"❌ Error reading directory: {str(e)}")
            return self.response(500, 'Internal Server Error', f'Gagal membaca direktori: {str(e)}', {})
    
    def generate_file_list_html(self, files, path):
        """
        Generate HTML untuk daftar file
        """
        print(f"🎨 Generating HTML for {len(files)} files")
        
        html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daftar File - HTTP Server</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.2em;
            font-weight: 300;
        }}
        .stats {{
            background: #f8f9fa;
            padding: 15px 30px;
            border-bottom: 1px solid #e9ecef;
            color: #6c757d;
        }}
        .file-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .file-table th {{
            background: #343a40;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 500;
        }}
        .file-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
            vertical-align: middle;
        }}
        .file-table tr:hover {{
            background: #f8f9fa;
        }}
        .file-name {{
            font-weight: 500;
            color: #2c3e50;
        }}
        .file-size {{
            color: #6c757d;
            text-align: right;
        }}
        .file-date {{
            color: #6c757d;
            font-size: 0.9em;
        }}
        .actions {{
            text-align: center;
        }}
        .btn {{
            display: inline-block;
            padding: 6px 12px;
            margin: 2px;
            border: none;
            border-radius: 4px;
            text-decoration: none;
            font-size: 0.85em;
            cursor: pointer;
            transition: all 0.3s;
        }}
        .btn-download {{
            background: #28a745;
            color: white;
        }}
        .btn-download:hover {{
            background: #218838;
        }}
        .btn-delete {{
            background: #dc3545;
            color: white;
        }}
        .btn-delete:hover {{
            background: #c82333;
        }}
        .empty-state {{
            text-align: center;
            padding: 60px 30px;
            color: #6c757d;
        }}
        .upload-info {{
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px 20px;
            margin: 20px 30px;
            border-radius: 4px;
        }}
        .server-info {{
            background: #f1f8e9;
            border-left: 4px solid #4caf50;
            padding: 10px 20px;
            margin: 10px 30px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 HTTP File Server</h1>
            <p>📁 Direktori: {path if path != '/' else 'Root'}</p>
        </div>
        
        <div class="stats">
            <strong>📊 Total file:</strong> {len(files)} | 
            <strong>🖥️  Server:</strong> FileServer/2.0 | 
            <strong>⏰ Waktu:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <div class="server-info">
            <strong>🎯 Server Status:</strong> Online dan berfungsi normal. 
            Log aktivitas tersimpan di directory logs/.
        </div>
        
        <div class="upload-info">
            <strong>💡 Info:</strong> Untuk upload file, gunakan POST request ke server ini. 
            Untuk hapus file, gunakan DELETE method dengan nama file.
            Semua aktivitas akan tercatat di log server.
        </div>
"""
        
        if len(files) == 0:
            html += """
        <div class="empty-state">
            <h3>📂 Direktori Kosong</h3>
            <p>Belum ada file dalam direktori ini.</p>
            <p>Upload file menggunakan client atau POST request.</p>
        </div>
"""
        else:
            html += """
        <table class="file-table">
            <thead>
                <tr>
                    <th>📄 Nama File</th>
                    <th>📏 Ukuran</th>
                    <th>📅 Terakhir Dimodifikasi</th>
                    <th>⚡ Aksi</th>
                </tr>
            </thead>
            <tbody>
"""
            
            for file_info in files:
                size_formatted = self.format_file_size(file_info['size'])
                html += f"""
                <tr>
                    <td class="file-name">{file_info['name']}</td>
                    <td class="file-size">{size_formatted}</td>
                    <td class="file-date">{file_info['modified']}</td>
                    <td class="actions">
                        <a href="/{file_info['name']}" class="btn btn-download">⬇️ Download</a>
                        <button onclick="deleteFile('{file_info['name']}')" class="btn btn-delete">🗑️ Hapus</button>
                    </td>
                </tr>
"""
            
            html += """
            </tbody>
        </table>
"""
        
        html += """
    </div>
    
    <script>
        function deleteFile(filename) {
            if (confirm('🗑️ Yakin ingin menghapus file "' + filename + '"?')) {
                console.log('🔄 Deleting file:', filename);
                fetch('/' + filename, {
                    method: 'DELETE'
                })
                .then(response => response.text())
                .then(data => {
                    console.log('✅ Delete response:', data);
                    alert('✅ ' + data);
                    location.reload();
                })
                .catch(error => {
                    console.error('❌ Delete error:', error);
                    alert('❌ Error: ' + error);
                });
            }
        }
        
        // Auto refresh setiap 30 detik
        setTimeout(() => {
            console.log('🔄 Auto-refreshing page...');
            location.reload();
        }, 30000);
        
        // Log page load
        console.log('📄 File listing page loaded with """ + str(len(files)) + """ files');
    </script>
</body>
</html>
"""
        return html
    
    def format_file_size(self, size_bytes):
        """Format ukuran file menjadi human readable"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def download_file(self, object_address):
        """
        Download file dari server
        """
        try:
            # Hapus leading slash
            object_address = object_address[1:] if object_address.startswith('/') else object_address
            
            print(f"⬇️  Download request: {object_address}")
            
            # Security check - cegah directory traversal
            if '..' in object_address or object_address.startswith('/'):
                print(f"🛡️  Security: Invalid file path blocked: {object_address}")
                return self.response(400, 'Bad Request', 'Invalid file path', {})
            
            file_path = './' + object_address
            
            # Cek apakah file ada
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                return self.response(404, 'Not Found', f'File "{object_address}" tidak ditemukan', {})
            
            if not os.path.isfile(file_path):
                print(f"❌ Path is not a file: {file_path}")
                return self.response(400, 'Bad Request', 'Path bukan file', {})
            
            # Baca file
            with open(file_path, 'rb') as fp:
                file_content = fp.read()
            
            file_size = len(file_content)
            print(f"✅ File read successfully: {object_address} ({self.format_file_size(file_size)})")
            
            # Tentukan content type berdasarkan ekstensi
            file_ext = os.path.splitext(file_path)[1].lower()
            content_type = self.types.get(file_ext, 'application/octet-stream')
            
            headers = {
                'Content-Type': content_type,
                'Content-Disposition': f'attachment; filename="{object_address}"'
            }
            
            return self.response(200, 'OK', file_content, headers)
            
        except Exception as e:
            print(f"❌ Error reading file {object_address}: {str(e)}")
            return self.response(500, 'Internal Server Error', f'Error reading file: {str(e)}', {})
    
    def http_post(self, object_address, headers, body):
        """
        Menangani POST request untuk upload file
        """
        try:
            # Hapus leading slash untuk nama file
            file_name = object_address[1:] if object_address.startswith('/') else object_address
            
            print(f"📤 Upload request: {file_name}")
            
            # Security check
            if '..' in file_name or '/' in file_name:
                print(f"🛡️  Security: Invalid filename blocked: {file_name}")
                return self.response(400, 'Bad Request', 'Invalid filename', {})
            
            if not file_name:
                # Generate nama file jika kosong
                file_name = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
                print(f"📝 Generated filename: {file_name}")
            
            file_path = './' + file_name
            
            # Tulis file
            with open(file_path, 'wb') as f:
                f.write(body)
            
            file_size = len(body)
            size_formatted = self.format_file_size(file_size)
            
            success_msg = f'File "{file_name}" berhasil diupload ({size_formatted})'
            print(f"✅ Upload successful: {file_name} - {size_formatted}")
            print(f"📤 [UPLOAD SUCCESS] {file_name} - {size_formatted}")
            
            return self.response(201, 'Created', success_msg, {})
            
        except Exception as e:
            error_msg = f'Upload gagal: {str(e)}'
            print(f"❌ Upload failed: {error_msg}")
            print(f"❌ [UPLOAD ERROR] {error_msg}")
            return self.response(500, 'Internal Server Error', error_msg, {})
    
    def http_delete(self, object_address, headers):
        """
        Menangani DELETE request untuk hapus file
        """
        try:
            # Hapus leading slash
            file_name = object_address[1:] if object_address.startswith('/') else object_address
            
            print(f"🗑️  Delete request: {file_name}")
            
            # Security check
            if '..' in file_name or '/' in file_name:
                print(f"🛡️  Security: Invalid filename blocked: {file_name}")
                return self.response(400, 'Bad Request', 'Invalid filename', {})
            
            if not file_name:
                print(f"❌ Empty filename for delete")
                return self.response(400, 'Bad Request', 'Filename tidak boleh kosong', {})
            
            file_path = './' + file_name
            
            # Cek apakah file ada
            if not os.path.exists(file_path):
                print(f"❌ File not found for delete: {file_name}")
                return self.response(404, 'Not Found', f'File "{file_name}" tidak ditemukan', {})
            
            # Cek apakah itu file (bukan direktori)
            if not os.path.isfile(file_path):
                print(f"❌ Cannot delete directory: {file_name}")
                return self.response(400, 'Bad Request', 'Tidak bisa menghapus direktori', {})
            
            # Hapus file
            os.remove(file_path)
            
            success_msg = f'File "{file_name}" berhasil dihapus'
            print(f"✅ Delete successful: {file_name}")
            print(f"🗑️  [DELETE SUCCESS] {file_name}")
            
            return self.response(200, 'OK', success_msg, {})
            
        except OSError as e:
            error_msg = f'Gagal menghapus file: {str(e)}'
            print(f"❌ Delete failed (OS): {error_msg}")
            print(f"❌ [DELETE ERROR] {error_msg}")
            return self.response(500, 'Internal Server Error', error_msg, {})
        except Exception as e:
            error_msg = f'Error: {str(e)}'
            print(f"❌ Delete failed: {error_msg}")
            print(f"❌ [DELETE ERROR] {error_msg}")
            return self.response(500, 'Internal Server Error', error_msg, {})

# Test jika dijalankan langsung
if __name__ == "__main__":
    # Setup logging untuk testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    httpserver = HttpServer()
    
    print("🧪 Testing HTTP Server...")
    
    # Test GET
    print("\n=== Test GET ===")
    result = httpserver.proses('GET / HTTP/1.1\r\nHost: localhost\r\n', b'')
    print(f"Response size: {len(result)} bytes")
    print("First 200 chars:", result.decode('utf-8', errors='replace')[:200] + "...")
    
    # Test POST (upload)
    print("\n=== Test POST ===")
    test_content = b"Hello, this is test file content for HTTP server testing!"
    headers = f'POST /test_file.txt HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(test_content)}\r\n'
    result = httpserver.proses(headers, test_content)
    print("Response:", result.decode('utf-8', errors='replace'))
    
    # Test GET untuk file yang baru diupload
    print("\n=== Test GET for uploaded file ===")
    result = httpserver.proses('GET /test_file.txt HTTP/1.1\r\nHost: localhost\r\n', b'')
    print(f"Response size: {len(result)} bytes")
    if b"200 OK" in result:
        print("✅ File download successful")
    
    # Test DELETE
    print("\n=== Test DELETE ===")
    result = httpserver.proses('DELETE /test_file.txt HTTP/1.1\r\nHost: localhost\r\n', b'')
    print("Response:", result.decode('utf-8', errors='replace'))
    
    print("\n✅ HTTP Server testing completed!")
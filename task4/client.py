import socket
import logging
import os
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default server address - ubah sesuai kebutuhan
server_address = ('127.0.0.1', 8880)

def make_socket(destination_address='127.0.0.1', port=8880):
    """
    Membuat koneksi socket ke server
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_addr = (destination_address, port)
        logging.info(f"Connecting to {server_addr}")
        sock.connect(server_addr)
        return sock
    except Exception as e:
        logging.error(f"Connection error: {str(e)}")
        return None

def send_command(command_data, timeout=10):
    """
    Mengirim command ke server dan menerima response
    """
    alamat_server = server_address[0]
    port_server = server_address[1]
    sock = make_socket(alamat_server, port_server)
    
    if not sock:
        return "Error: Could not connect to server"
    
    try:
        # Set timeout yang lebih pendek
        sock.settimeout(timeout)
        
        logging.info(f"Sending request...")
        
        # Kirim data
        if isinstance(command_data, str):
            command_data = command_data.encode('utf-8')
        
        sock.sendall(command_data)
        logging.debug(f"Request sent: {str(command_data[:100])}")
        
        # Terima response dengan method yang lebih simple
        data_received = b""
        
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data_received += chunk
                
                # Cek jika sudah dapat response lengkap
                if b"\r\n\r\n" in data_received:
                    # Parse headers untuk content length
                    header_end = data_received.find(b"\r\n\r\n")
                    headers = data_received[:header_end].decode('utf-8', errors='replace')
                    
                    content_length = 0
                    for line in headers.split('\r\n'):
                        if line.lower().startswith('content-length:'):
                            try:
                                content_length = int(line.split(':', 1)[1].strip())
                                break
                            except:
                                pass
                    
                    if content_length > 0:
                        body_start = header_end + 4
                        current_body = data_received[body_start:]
                        
                        # Baca sisa body jika perlu
                        while len(current_body) < content_length:
                            remaining = content_length - len(current_body)
                            chunk = sock.recv(min(4096, remaining))
                            if not chunk:
                                break
                            data_received += chunk
                            current_body = data_received[body_start:]
                    break
                    
            except socket.timeout:
                if len(data_received) > 0:
                    break  # Ada data partial, return saja
                else:
                    raise
        
        logging.info(f"Received {len(data_received)} bytes from server")
        return data_received.decode('utf-8', errors='replace')
        
    except socket.timeout:
        return "Error: Request timeout"
    except Exception as e:
        logging.error(f"Error during communication: {str(e)}")
        return f"Error: {str(e)}"
    finally:
        try:
            sock.close()
        except:
            pass

def send_binary_data(command_headers, binary_data, timeout=30):
    """
    Mengirim data binary (untuk upload file)
    """
    alamat_server = server_address[0]
    port_server = server_address[1]
    sock = make_socket(alamat_server, port_server)
    
    if not sock:
        return "Error: Could not connect to server"
    
    try:
        sock.settimeout(timeout)
        
        # Gabungkan headers dan binary data
        if isinstance(command_headers, str):
            command_headers = command_headers.encode('utf-8')
        
        request_data = command_headers + binary_data
        
        logging.info(f"Sending {len(request_data)} bytes...")
        
        # Kirim data sekaligus untuk file kecil
        if len(request_data) < 64*1024:  # < 64KB
            sock.sendall(request_data)
        else:
            # Kirim dalam chunks untuk file besar
            bytes_sent = 0
            chunk_size = 8192  # 8KB chunks
            
            while bytes_sent < len(request_data):
                chunk = request_data[bytes_sent:bytes_sent + chunk_size]
                sent = sock.send(chunk)
                if sent == 0:
                    break
                bytes_sent += sent
        
        logging.info(f"Sent {len(request_data)} bytes total")
        
        # Terima response
        response = b""
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                # Break jika sudah dapat response lengkap
                if b"\r\n\r\n" in response:
                    break
            except socket.timeout:
                break
        
        return response.decode('utf-8', errors='replace')
        
    except Exception as e:
        logging.error(f"Error sending binary data: {str(e)}")
        return f"Error: {str(e)}"
    finally:
        try:
            sock.close()
        except:
            pass

def list_files(directory='/'):
    """
    Mengambil daftar file dari server
    """
    print(f"\n{'='*50}")
    print(f"LISTING FILES")
    print(f"{'='*50}")
    
    command = f"GET {directory} HTTP/1.1\r\nHost: localhost\r\n\r\n"
    hasil = send_command(command)
    
    if "200 OK" in hasil:
        print("SUCCESS: File listing received")
        
        # Parse HTML untuk extract nama file
        file_list = extract_filenames_from_html(hasil)
        
        if file_list:
            print(f"\nFound {len(file_list)} files:")
            print("-" * 40)
            for i, filename in enumerate(file_list, 1):
                print(f"{i:2d}. {filename}")
            print("-" * 40)
        else:
            print("No files found or failed to parse response")
    else:
        print("FAILED: Could not get file listing")
        print("--- Server Response (first 500 chars) ---")
        print(hasil[:500] + "..." if len(hasil) > 500 else hasil)
        print("-" * 50)
    
    return hasil

def extract_filenames_from_html(html_response):
    """
    Extract filenames dari HTML response
    """
    import re
    
    try:
        # Cari semua pattern yang mengandung nama file dalam HTML table
        # Pattern: <td class="file-name">filename</td>
        pattern = r'<td class="file-name">([^<]+)</td>'
        matches = re.findall(pattern, html_response)
        
        # Clean up filenames (remove any extra whitespace)
        filenames = [filename.strip() for filename in matches if filename.strip()]
        
        return filenames
        
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return []

def upload_file(local_path, remote_path=None):
    """
    Upload file ke server
    """
    if not os.path.exists(local_path):
        print(f"ERROR: File '{local_path}' not found")
        return False
    
    if not remote_path:
        remote_path = '/' + os.path.basename(local_path)
    
    if not remote_path.startswith('/'):
        remote_path = '/' + remote_path
    
    print(f"\n{'='*50}")
    print(f"UPLOADING FILE")
    print(f"{'='*50}")
    print(f"Local:  {local_path}")
    print(f"Remote: {remote_path}")
    
    try:
        # Baca file
        with open(local_path, 'rb') as f:
            file_content = f.read()
        
        file_size = len(file_content)
        print(f"Size:   {format_file_size(file_size)}")
        
        # Buat HTTP request
        headers = (
            f"POST {remote_path} HTTP/1.1\r\n"
            f"Host: localhost\r\n"
            f"Content-Length: {file_size}\r\n"
            f"\r\n"
        )
        
        start_time = time.time()
        hasil = send_binary_data(headers, file_content, timeout=60)
        upload_time = time.time() - start_time
        
        print(f"Upload time: {upload_time:.2f}s")
        
        if upload_time > 0:
            speed = file_size / upload_time
            print(f"Upload speed: {format_file_size(speed)}/s")
        
        if "201 Created" in hasil or "200 OK" in hasil:
            print("SUCCESS: File uploaded successfully!")
            # Extract just the success message
            lines = hasil.split('\n')
            for line in lines:
                if 'berhasil' in line.lower() or 'success' in line.lower():
                    print(f"Server message: {line.strip()}")
                    break
            return True
        else:
            print("FAILED: Upload failed")
            print("--- Upload Response ---")
            print(hasil[:300] + "..." if len(hasil) > 300 else hasil)
            return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        print("-" * 50)

def download_file(remote_filename, local_path=None):
    """
    Download file dari server
    """
    if not local_path:
        local_path = remote_filename
    
    print(f"\n{'='*50}")
    print(f"📥 DOWNLOADING FILE")
    print(f"{'='*50}")
    print(f"Remote: {remote_filename}")
    print(f"Local:  {local_path}")
    
    command = f"GET /{remote_filename} HTTP/1.1\r\nHost: localhost\r\n\r\n"
    
    try:
        start_time = time.time()
        response = send_command(command, timeout=120)
        download_time = time.time() - start_time
        
        # Parse response untuk mendapatkan file content
        if "\r\n\r\n" in response:
            headers, body = response.split("\r\n\r\n", 1)
            
            if "200 OK" in headers:
                # Simpan file
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(body)
                
                file_size = len(body.encode('utf-8'))
                print(f"✅ Download successful!")
                print(f"Size: {format_file_size(file_size)}")
                print(f"Time: {download_time:.2f}s")
                
                if download_time > 0:
                    speed = file_size / download_time
                    print(f"Speed: {format_file_size(speed)}/s")
                
                return True
            else:
                print("--- Download Response ---")
                print(response)
                return False
        else:
            print("--- Download Response ---")
            print(response)
            return False
            
    except Exception as e:
        print(f"❌ Error during download: {e}")
        return False
    finally:
        print("-" * 50)

def delete_file(filepath):
    """
    Hapus file dari server
    """
    if not filepath.startswith('/'):
        filepath = '/' + filepath
    
    print(f"\n{'='*50}")
    print(f"DELETING FILE")
    print(f"{'='*50}")
    print(f"File: {filepath}")
    
    command = f"DELETE {filepath} HTTP/1.1\r\nHost: localhost\r\n\r\n"
    hasil = send_command(command)
    
    if "200 OK" in hasil:
        print("SUCCESS: File deleted successfully!")
        # Extract success message
        lines = hasil.split('\n')
        for line in lines:
            if 'berhasil' in line.lower() or 'success' in line.lower():
                print(f"Server message: {line.strip()}")
                break
        print("-" * 50)
        return True
    else:
        print("FAILED: Delete failed")
        print("--- Delete Response ---")
        print(hasil[:300] + "..." if len(hasil) > 300 else hasil)
        print("-" * 50)
        return False

def format_file_size(size_bytes):
    """Format ukuran file"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def interactive_mode():
    """
    Mode interaktif untuk testing
    """
    print(f"\n{'-'*60}")
    print(f"HTTP FILE CLIENT - INTERACTIVE MODE")
    print(f"{'-'*60}")
    print(f"Server: {server_address[0]}:{server_address[1]}")
    print(f"{'-'*60}")
    
    while True:
        print(f"\nAvailable operations:")
        print(f"  1. List files")
        print(f"  2. Upload file") 
        print(f"  3. Download file")
        print(f"  4. Delete file")
        print(f"  5. Exit")
        
        try:
            choice = input(f"\nSelect operation (1-5): ").strip()
            
            if choice == '1':
                list_files('/')
                
            elif choice == '2':
                local_file = input("Enter local file path: ").strip()
                if local_file:
                    remote_name = input("Remote filename (Enter for same): ").strip()
                    upload_file(local_file, remote_name if remote_name else None)
                    
            elif choice == '3':
                remote_file = input("Enter remote filename: ").strip()
                if remote_file:
                    local_name = input("Save as (Enter for same): ").strip()
                    download_file(remote_file, local_name if local_name else None)
                    
            elif choice == '4':
                filename = input("Enter filename to delete: ").strip()
                if filename:
                    confirm = input(f"Delete '{filename}'? (y/N): ").strip().lower()
                    if confirm == 'y':
                        delete_file(filename)
                    else:
                        print("Delete cancelled")
                        
            elif choice == '5':
                print("Goodbye!")
                break
                
            else:
                print("Invalid choice. Please select 1-5.")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

def demo_operations():
    """
    Demo otomatis semua operasi
    """
    print(f"\n{'='*60}")
    print(f"🎬 RUNNING DEMO - ALL OPERATIONS")
    print(f"{'='*60}")
    
    # 1. List files awal
    print("\n1️⃣ Initial file listing...")
    list_files('/')
    
    # 2. Upload test file
    print("\n2️⃣ Creating and uploading test file...")
    test_content = f"Test file created at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    test_content += "This is a test file for HTTP server demo.\n"
    test_content += "Server supports GET, POST, and DELETE operations.\n"
    
    with open('demo_test.txt', 'w') as f:
        f.write(test_content)
    
    upload_file('demo_test.txt', '/demo_test.txt')
    
    # 3. Upload file lain jika ada
    if os.path.exists('README.md'):
        print("\n3️⃣ Uploading README.md...")
        upload_file('README.md', '/readme_copy.md')
    
    # 4. List files setelah upload
    print("\n4️⃣ File listing after upload...")
    list_files('/')
    
    # 5. Download file
    print("\n5️⃣ Downloading uploaded file...")
    download_file('demo_test.txt', 'downloaded_demo.txt')
    
    # 6. Delete file
    print("\n6️⃣ Deleting uploaded file...")
    delete_file('/demo_test.txt')
    
    # 7. Final file listing
    print("\n7️⃣ Final file listing...")
    list_files('/')
    
    # Cleanup
    try:
        os.remove('demo_test.txt')
        if os.path.exists('downloaded_demo.txt'):
            os.remove('downloaded_demo.txt')
    except:
        pass
    
    print(f"\n{'='*60}")
    print(f"✅ DEMO COMPLETED")
    print(f"{'='*60}")

def main():
    """
    Main function
    """
    import argparse
    global server_address
    
    parser = argparse.ArgumentParser(description='HTTP File Client')
    parser.add_argument('--host', default='127.0.0.1', help='Server host')
    parser.add_argument('--port', type=int, default=8880, help='Server port')
    parser.add_argument('--demo', action='store_true', help='Run demo of all operations')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    
    # Command line operations
    parser.add_argument('--list', action='store_true', help='List files')
    parser.add_argument('--upload', help='Upload file (local_path)')
    parser.add_argument('--remote-name', help='Remote filename for upload')
    parser.add_argument('--download', help='Download file')
    parser.add_argument('--save-as', help='Local filename for download')
    parser.add_argument('--delete', help='Delete file')
    
    args = parser.parse_args()
    
    # Set server address
    server_address = (args.host, args.port)
    
    if args.demo:
        demo_operations()
    elif args.interactive:
        interactive_mode()
    elif args.list:
        list_files('/')
    elif args.upload:
        upload_file(args.upload, args.remote_name)
    elif args.download:
        download_file(args.download, args.save_as)
    elif args.delete:
        delete_file(args.delete)
    else:
        # Default ke interactive mode
        interactive_mode()

if __name__ == '__main__':
    main()
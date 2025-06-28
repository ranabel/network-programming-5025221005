from socket import *
import socket
import logging
import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor
from http import HttpServer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global HTTP server instance
httpserver = HttpServer()

def ProcessTheClient(connection, address):
    """
    Fungsi untuk memproses client dalam thread terpisah
    """
    thread_id = threading.current_thread().ident
    start_time = time.time()
    
    try:
        logging.info(f"[Thread-{thread_id}] Processing connection from {address}")
        
        # Set timeout untuk connection
        connection.settimeout(120.0)  # 2 menit timeout
        
        # Terima headers dulu sampai ketemu double CRLF
        headers_data = b""
        while b"\r\n\r\n" not in headers_data:
            data = connection.recv(1024)
            if not data:
                break
            headers_data += data
            
            # Batasi ukuran header maksimal (security)
            if len(headers_data) > 32768:  # 32KB max headers
                logging.warning(f"[Thread-{thread_id}] Header terlalu besar dari {address}")
                break
        
        if not headers_data:
            logging.warning(f"[Thread-{thread_id}] Tidak ada data dari {address}")
            return
        
        # Pisahkan header dan body yang mungkin sudah terbaca
        if b"\r\n\r\n" in headers_data:
            header_part, _, body_part = headers_data.partition(b'\r\n\r\n')
        else:
            header_part = headers_data
            body_part = b""
        
        header_str = header_part.decode('utf-8', errors='ignore')
        
        # Cari Content-Length dari header
        content_length = 0
        for line in header_str.split('\r\n'):
            if "Content-Length:" in line or "content-length:" in line:
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                    break
                except ValueError:
                    logging.warning(f"[Thread-{thread_id}] Invalid Content-Length dari {address}")
        
        # Baca sisa body jika diperlukan
        body_data = body_part
        bytes_read = len(body_part)
        
        while bytes_read < content_length:
            bytes_to_read = min(8192, content_length - bytes_read)  # Read in 8KB chunks
            data = connection.recv(bytes_to_read)
            if not data:
                break
            body_data += data
            bytes_read += len(data)
        
        logging.info(f"[Thread-{thread_id}] Received {len(header_str)} bytes headers + {len(body_data)} bytes body from {address}")
        
        # Proses request menggunakan HTTP server
        hasil = httpserver.proses(header_str, body_data)
        
        # Kirim response
        connection.sendall(hasil)
        
        # Log completion time
        processing_time = time.time() - start_time
        logging.info(f"[Thread-{thread_id}] Completed {address} in {processing_time:.3f}s")
        
    except socket.timeout:
        logging.warning(f"[Thread-{thread_id}] Timeout dari {address}")
    except ConnectionResetError:
        logging.warning(f"[Thread-{thread_id}] Connection reset oleh {address}")
    except Exception as e:
        logging.error(f"[Thread-{thread_id}] Error processing {address}: {str(e)}")
    finally:
        try:
            connection.close()
        except:
            pass
        
        total_time = time.time() - start_time
        logging.info(f"[Thread-{thread_id}] Connection {address} closed (total: {total_time:.3f}s)")

def Server(host='127.0.0.1', port=8880, max_workers=20):
    """
    Main server function dengan Thread Pool
    """
    the_clients = []
    
    # Buat socket server
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Optimasi socket buffer
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)  # 64KB receive buffer
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)  # 64KB send buffer
    
    try:
        my_socket.bind((host, port))
        logging.info(f"Thread Pool Server started on {host}:{port}")
        logging.info(f"Max workers: {max_workers}")
        logging.info(f"Server ready to accept connections...")
        print(f"\n{'='*60}")
        print(f"🚀 HTTP FILE SERVER - THREAD POOL MODE")
        print(f"{'='*60}")
        print(f"📡 Address: http://{host}:{port}")
        print(f"🔧 Max Workers: {max_workers}")
        print(f"📁 Working Directory: {os.getcwd()}")
        print(f"{'='*60}")
        print(f"Available endpoints:")
        print(f"  📋 GET  /           - Server info") 
        print(f"  📋 GET  /files      - List files")
        print(f"  📤 POST /filename   - Upload file")
        print(f"  🗑️  DELETE /filename - Delete file")
        print(f"  📥 GET  /filename   - Download file")
        print(f"{'='*60}")
        print(f"Press Ctrl+C to stop server")
        print()
        
        my_socket.listen(100)  # Backlog queue
        
        # Gunakan ThreadPoolExecutor untuk mengelola threads
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="HTTPServer") as executor:
            while True:
                try:
                    # Accept connection
                    connection, client_address = my_socket.accept()
                    
                    logging.info(f"New connection from {client_address}")
                    
                    # Submit task ke thread pool
                    future = executor.submit(ProcessTheClient, connection, client_address)
                    the_clients.append(future)
                    
                    # Cleanup completed futures (optional)
                    the_clients = [f for f in the_clients if not f.done()]
                    
                    # Log active connections count
                    active_count = len([f for f in the_clients if f.running()])
                    if active_count > 0:
                        logging.info(f"Active connections: {active_count}")
                
                except KeyboardInterrupt:
                    print("\n🛑 Shutdown signal received...")
                    break
                except Exception as e:
                    logging.error(f"Error accepting connection: {str(e)}")
                    
    except Exception as e:
        logging.error(f"Server error: {str(e)}")
    finally:
        logging.info("Closing server socket...")
        my_socket.close()
        logging.info("Thread Pool Server stopped")

def main():
    """
    Main function dengan argument parsing
    """
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='HTTP File Server with Thread Pool')
    parser.add_argument('--host', default='127.0.0.1', help='Server host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8880, help='Server port (default: 8880)')
    parser.add_argument('--workers', type=int, default=20, help='Max worker threads (default: 20)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        Server(host=args.host, port=args.port, max_workers=args.workers)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
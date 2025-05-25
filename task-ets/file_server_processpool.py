from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import logging
from file_protocol import ProtocolHandler
import multiprocessing
import concurrent.futures

handler = ProtocolHandler()

def client_handler(conn, addr):
    """Handles client connections"""
    logging.warning(f"New connection from {addr}")
    data_buffer = ""
    try:
        while True:
            chunk = conn.recv(1024*1024)
            if not chunk:
                break
            data_buffer += chunk.decode()
            
            while "\r\n\r\n" in data_buffer:
                request, data_buffer = data_buffer.split("\r\n\r\n", 1)
                response = handler.process_request(request) + "\r\n\r\n"
                conn.sendall(response.encode())
    except Exception as e:
        logging.warning(f"Connection error: {e}")
    finally:
        logging.warning(f"Closing connection from {addr}")
        conn.close()

class ProcessPoolServer:
    def __init__(self, host='0.0.0.0', port=8889, workers=5):
        self.address = (host, port)
        self.worker_count = workers
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    def start(self):
        logging.warning(f"Starting server on {self.address} with {self.worker_count} workers")
        self.sock.bind(self.address)
        self.sock.listen(1)
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.worker_count) as pool:
            try:
                while True:
                    client_conn, client_addr = self.sock.accept()
                    logging.warning(f"Accepted connection from {client_addr}")
                    pool.submit(client_handler, client_conn, client_addr)
            except KeyboardInterrupt:
                logging.warning("Server shutting down")
            except Exception as e:
                logging.warning(f"Server error: {e}")
            finally:
                self.sock.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Process Pool File Server')
    parser.add_argument('--port', type=int, default=6667, help='Server port')
    parser.add_argument('--pool-size', type=int, default=5, help='Process pool size')
    args = parser.parse_args()
    
    server = ProcessPoolServer(port=args.port, workers=args.pool_size)
    server.start()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    logging.basicConfig(level=logging.WARNING)
    main()
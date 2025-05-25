from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import logging
from file_protocol import ProtocolHandler
import concurrent.futures

handler = ProtocolHandler()

def handle_client(conn, addr):
    """Process client requests"""
    logging.warning(f"Handling client: {addr}")
    buffer = ""
    try:
        conn.settimeout(1800)
        
        while True:
            data = conn.recv(1024*1024)
            if not data:
                break
            buffer += data.decode()
            
            while "\r\n\r\n" in buffer:
                cmd, buffer = buffer.split("\r\n\r\n", 1)
                result = handler.process_request(cmd) + "\r\n\r\n"
                conn.sendall(result.encode())
    except Exception as e:
        logging.warning(f"Client error: {e}")
    finally:
        logging.warning(f"Disconnecting client: {addr}")
        conn.close()

class ThreadedServer:
    def __init__(self, host='0.0.0.0', port=8889, max_threads=5):
        self.server_addr = (host, port)
        self.thread_count = max_threads
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.settimeout(1800)

    def run(self):
        logging.warning(f"Server running on {self.server_addr} with {self.thread_count} threads")
        self.socket.bind(self.server_addr)
        self.socket.listen(5)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_count) as executor:
            try:
                while True:
                    client_conn, client_addr = self.socket.accept()
                    logging.warning(f"New client: {client_addr}")
                    executor.submit(handle_client, client_conn, client_addr)
            except KeyboardInterrupt:
                logging.warning("Server stopping")
            finally:
                self.socket.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Threaded File Server')
    parser.add_argument('--port', type=int, default=6667, help='Server port')
    parser.add_argument('--pool-size', type=int, default=5, help='Thread pool size')
    args = parser.parse_args()
    
    server = ThreadedServer(port=args.port, max_threads=args.pool_size)
    server.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
from socket import *
import socket
import threading
import logging
import pytz
from datetime import datetime

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        try:
            while True:
                data = self.connection.recv(256)
                if data:
                    logging.warning(f"[SERVER] received {data} from {self.address}")
                    
                    if data == b'TIME\r\n':
                        tz = pytz.timezone('Asia/Jakarta')
                        current_time = datetime.now(tz).strftime("%H:%M:%S")
                        response = f"JAM {current_time}\r\n"
                        logging.warning(f"[SERVER] sending {response} to {self.address}")
                        self.connection.sendall(response.encode('UTF-8'))
                    elif data == b'QUIT\r\n':
                        logging.warning(f"[SERVER] closing connection with {self.address}")
                        self.connection.close()
                        break
                    else:
                        logging.warning(f"[SERVER] invalid request from {self.address}")
                        self.connection.close()
                        break
                else:
                    break
        finally:
            self.connection.close()

class Server(threading.Thread):
    def __init__(self):
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        threading.Thread.__init__(self)

    def run(self):
        self.my_socket.bind(('0.0.0.0', 45000))
        self.my_socket.listen(1)
        while True:
            self.connection, self.client_address = self.my_socket.accept()
            logging.warning(f"connection from {self.client_address}")
            
            clt = ProcessTheClient(self.connection, self.client_address)
            clt.start()
            self.the_clients.append(clt)

def main():
    svr = Server()
    svr.start()

if __name__=="__main__":
    main()
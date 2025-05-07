import socket
import logging
import time

def send():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logging.warning("Opening Socket")

    server_address = ('172.16.16.101', 45000) 
    logging.warning(f"opening socket {server_address}")
    sock.connect(server_address)

    try:
        message = "TIME\r\n"
        logging.warning(f"[CLIENT] sending {message}")
        sock.sendall(message.encode("UTF-8"))
        
        data = sock.recv(256)
        logging.warning(f"[RECEIVE FROM SERVER] {data}")
        
        message = "QUIT\r\n"
        logging.warning(f"[CLIENT] sending {message}")
        sock.sendall(message.encode("UTF-8"))
        
    except Exception as e:
        logging.error(f"Error Occured: {e}")
    finally:
        logging.warning("Closing")
        sock.close()
    return

if __name__=='__main__':
    while True:
        send()
        time.sleep(1)
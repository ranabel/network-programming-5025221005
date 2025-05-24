import socket
import json
import base64
import logging

server_address = ('172.16.16.101', 7777)

def send_command(command_str=""):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    logging.warning(f"connecting to {server_address}")
    try:
        logging.warning(f"sending message")
        sock.sendall(command_str.encode())
        data_received = ""
        while True:
            data = sock.recv(1024)
            if data:
                data_received += data.decode()
                if "\r\n\r\n" in data_received:
                    break
            else:
                break
        hasil = json.loads(data_received)
        logging.warning("data received from server:")
        return hasil
    except:
        logging.warning("error during data receiving")
        return False

def remote_list():
    command_str = "LIST"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        print("Daftar file:")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        print("Gagal")
        return False

def remote_get(filename=""):
    command_str = f"GET {filename}"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        namafile = hasil['data_namafile']
        isifile = base64.b64decode(hasil['data_file'])
        with open(namafile, 'wb+') as fp:
            fp.write(isifile)
        return True
    else:
        print("Gagal")
        return False

def remote_upload(filename=""):
    try:
        with open(filename, 'rb') as fp:
            isifile = base64.b64encode(fp.read()).decode()
        command_str = f"UPLOAD {filename} {isifile}"
        hasil = send_command(command_str)
        if hasil['status'] == 'OK':
            print(hasil['data'])
            return True
        else:
            print("Gagal")
            return False
    except FileNotFoundError:
        print(f"File {filename} tidak ditemukan")
        return False

def remote_delete(filename=""):
    command_str = f"DELETE {filename}"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        print(hasil['data'])
        return True
    else:
        print("Gagal")
        return False

if __name__ == '__main__':
    server_address = ('172.16.16.101', 7777)
    print("=== Tes LIST ===")
    remote_list()
    
    print("\n=== Tes GET ===")
    remote_get('donalbebek.jpg')
    
    print("\n=== Tes LIST setelah GET ===")
    remote_list()
    
    print("\n=== Tes UPLOAD ===")
    remote_upload('tugas3.txt')
    
    print("\n=== Tes LIST setelah UPLOAD ===")
    remote_list()
    
    print("\n=== Tes DELETE ===")
    remote_delete('tugas3.txt')
    
    print("\n=== Tes LIST setelah DELETE ===")
    remote_list()
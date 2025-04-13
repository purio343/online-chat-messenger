import socket
import threading
import sys
import datetime

def main():
    server_address = input('Type in the server address: ')
    server_port = 9001

    client_address = ''
    client_port = 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((client_address, client_port))

    rate = 4096
    
    try:
        name = input('Type in your name: ').encode('utf-8')
        threading.Thread(target=listen, args=(sock, rate, name), daemon=True).start()
        while True:
            body = input('Type in your message: ').encode('utf-8')
            header = protocol_header(len(name))
            message = header + name + body
            sock.sendto(message, (server_address, server_port))

    finally:
        print('Closing socket')
        sock.close()

def listen(sock, rate, name):            
        try:
            while True:
                data, server = sock.recvfrom(rate)
                
                username_length = int.from_bytes(data[:1], 'big')
                username = data[1:username_length + 1].decode('utf-8')
                message = data[username_length + 1:].decode('utf-8')
                disp_name = username + '(yourself)' if username == name.decode('utf-8') else username
                sys.stdout.write('\r')
                now = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
                print(f'{now} {disp_name}: {message}')
                sys.stdout.write('Type in your message: ')
                sys.stdout.flush()
        except KeyboardInterrupt:
            print("\nClosing socket")
        except Exception as e:
            print(f'Error receiving data: {e}')

def protocol_header(username_length):
    return username_length.to_bytes(1, 'big')

if __name__ == "__main__":
    main()
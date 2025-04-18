import socket
import threading
import sys
import datetime
import uuid

server_port = 9001
client_address = ''
client_port = 0
token_size = 17

def main():
    tcp_connection()

# def listen(sock, rate, name):            
#         try:
#             while True:
#                 data, server = sock.recvfrom(rate)
                
#                 username_length = int.from_bytes(data[:1], 'big')
#                 username = data[1:username_length + 1].decode('utf-8')
#                 message = data[username_length + 1:].decode('utf-8')
#                 disp_name = username + '(yourself)' if username == name.decode('utf-8') else username
#                 sys.stdout.write('\r')
#                 now = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
#                 print(f'{now} {disp_name}: {message}')
#                 sys.stdout.write('Type in your message: ')
#                 sys.stdout.flush()
#         except KeyboardInterrupt:
#             print("\nClosing socket")
#         except Exception as e:
#             print(f'Error receiving data: {e}')

# def protocol_header(username_length):
#     return username_length.to_bytes(1, 'big')

def chatroom_protocol_header(roomname_length, operation, state, operation_payload_length):
    header = roomname_length.to_bytes(1, 'big')
    header += operation.to_bytes(1, 'big')
    header += state.to_bytes(1, 'big')
    header += operation_payload_length.to_bytes(29, 'big')
    return header

def tcp_connection():
    
    server_address = input('Type in the server address:')
    name = input('Type in your name:').encode('utf-8')
    roomname = input('Type in the room name:').encode('utf-8')
    operation = input('Type in the operation:').encode('utf-8')
    # 部屋作成のリクエストを送信する時、ペイロードにはユーザー名が含まれる。
    header = chatroom_protocol_header(len(roomname), int(operation), 200, len(name))
    body = roomname + name
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((client_address, client_port))

    try:
        sock.connect((server_address, server_port))
    except Exception as e:
        print(f'Error connecting to the server: {e}')

    try:
        sock.sendall(header)
        sock.sendall(body)
    except Exception as e:
        print(f'Error sending data: {e}')
    
    try:
        data = sock.recv(token_size)
        status_code = int.from_bytes(data[:1], 'big')
        if status_code == 1:
            print('Room created successfully')
        elif status_code == 2:
            print('Joined room successfully')
        else:
            print('Failed to create room')
        
        token = uuid.UUID(bytes=data[1:])
        print(f'Your token is {token}')
    except Exception as e:
        print(f'Error receiving data: {e}')
    finally:
        sock.close()

if __name__ == "__main__":
    main()
import socket
import threading
import sys
import datetime
import uuid
import json

with open('config.json', 'r') as f:
    config = json.load(f)

server_address = config["server_address"]
client_address = config["client_address"]
tcp_port = config["tcp_port"]
udp_port = config["udp_port"]
token_size = config["token_size"]
rate = config["rate"]

def main():
    client_token, roomname, actual_port = tcp_connection()
    udp_connection(client_token, roomname, actual_port)

def chatroom_protocol_header(roomname_length, operation, state, operation_payload_length):
    header = roomname_length.to_bytes(1, 'big')
    header += operation.to_bytes(1, 'big')
    header += state.to_bytes(1, 'big')
    header += operation_payload_length.to_bytes(29, 'big')
    return header

def chat_protocol_header(roomname_length, token_length):
    header = roomname_length.to_bytes(1, 'big')
    header += token_length.to_bytes(1, 'big')
    return header

def tcp_connection():
    
    name = input('Type in your name:').encode('utf-8')
    roomname = input('Type in the room name:').encode('utf-8')
    operation = input('Type in the operation:').encode('utf-8')
    # 部屋作成のリクエストを送信する時、ペイロードにはユーザー名が含まれる。
    header = chatroom_protocol_header(len(roomname), int(operation), 200, len(name))
    body = roomname + name
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((client_address, 0))
    # TCPで使用されたポート番号を取得
    actual_port = sock.getsockname()[1]

    try:
        sock.connect((server_address, tcp_port))
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
            print('Failed to create/join room.')
            sys.exit(1)
        
        token = uuid.UUID(bytes=data[1:])
        print(f'Your token is {token}')
        return [token, roomname, actual_port]
    except Exception as e:
        print(f'Error receiving data: {e}')
    finally:
        sock.close()

def udp_connection(token, roomname, actual_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # TCPのソケットと同じポートを使用
    sock.bind((client_address, actual_port))
    try:
        listen_thread = threading.Thread(target=recieve_message, args=(sock, rate), daemon=True)
        send_thread = threading.Thread(target=send_message, args=(sock, token, roomname), daemon=True)
        listen_thread.start()
        send_thread.start()
        listen_thread.join()
        send_thread.join()
    except Exception as e:
        print(f'An error occured: {str(e)}')
    finally:
        sock.close()

def send_message_header_protocol(roomname_length, token_length):
    header = roomname_length.to_bytes(1, 'big')
    header += token_length.to_bytes(1, 'big')
    return header

# メッセージ受信スレッド
def recieve_message(sock, rate):
    try:
        while True:
            # dataにヘッダーは含まれていない
            data, server = sock.recvfrom(rate)
            message = data.decode('utf-8')
            now = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            print(f'{now} {message}')
            print(">", end="", flush=True)
    except KeyboardInterrupt:
        print('\nChat closed')
    except Exception as e:
        print(f'\nAn error occured: {str(e)}')

def send_message(sock, token, roomname):
    while True:
        print(">", end="", flush=True)
        message = input().encode('utf-8')
        # UUIDのバイト列は16バイト
        token_bytes = token.bytes
        header = send_message_header_protocol(len(roomname), len(token_bytes))
        body = roomname + token_bytes + message
        data = header + body
        try:
            sock.sendto(data, (server_address, udp_port))
        except Exception as e:
            print(f'Error sending data: {str(e)}')



if __name__ == "__main__":
    main()
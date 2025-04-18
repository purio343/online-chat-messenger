import socket
import datetime
import time
import threading
import uuid

server_address = '0.0.0.0'
port = 9001
rate = 4096
max_fails = 3
clients = {}
rooms = {}
timeout = 60
lock = threading.Lock()

def main():
    tcp_handler()

# 各クライアントの最終更新日時を取得して、一定時間送信していない場合は管理用の連想配列から削除
# def cleanup_clients(clients, timeout=60):
#     while True:
#         now = datetime.datetime.now()
#         remove_list = []
#         with lock:
#             for address, information in list(clients.items()):
#                 if (now - information["last_seen"]).total_seconds() > timeout:
#                     remove_list.append(address)
#             for addr in remove_list:
#                 print(f'Removing {addr} due to inactivity')
#                 del clients[addr]
#         time.sleep(10)

def tcp_handler():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((server_address, port))
    sock.listen(5)
    print(f'Server is runnning on {server_address}:{port}')

    while True:
        connection, address = sock.accept()
        print(f'Connection from {address}')
        try:
            header = connection.recv(32)
            roomname_length = int.from_bytes(header[:1], 'big')
            operation = int.from_bytes(header[1:2], 'big')
            state = int.from_bytes(header[2:3], 'big')
            operation_payload_length = int.from_bytes(header[3:32], 'big')
            
            roomname = connection.recv(roomname_length).decode('utf-8')
            operation_payload = connection.recv(operation_payload_length)

            # operationに応じた処理を行う。
            # 1: Create Room
            # 2: Join Room
            if operation == 1:
                print(f'Creating room {roomname}')
                username = operation_payload.decode('utf-8')
                print(f'Username: {username}')
                print(f'Roomname: {roomname}')
                create_room(connection, address, username, roomname)
            elif operation == 2:
                if roomname not in rooms:
                    connection.close()
                    return
                print(f'Joining room {roomname}')
                username = operation_payload.decode('utf-8')
                join_room(connection, address, username, roomname)

        except Exception as e:
            print(f'An error occurred: {e}')
        finally:
            connection.close()
            print('Connection closed')

def create_room(connection, address, username, roomname):
    try:
        client_token = uuid.uuid4()
        # 部屋が存在しない場合、部屋を新規に作成。
        if roomname not in rooms:
            rooms[roomname] = {
                "host": {},
                "guest": {}
            }
        # 作成した部屋にホストとして追加。
        rooms[roomname]["host"][address] = {
            "user_name": username,
            "client_token": client_token
        }
        print(f'client_token: {client_token}')
        send_token(connection, client_token, 1)
    except Exception as e:
        print(f'Error creating: {e.__traceback__}')

def join_room(connection, address, username, roomname):
    try:
        client_token = uuid.uuid4()
        # ゲスト（ホスト以外のユーザー）として部屋に追加
        rooms[roomname]["guest"][address] ={
            "user_name": username,
            "client_token": client_token,
        }
        send_token(connection, client_token, 2)
    except Exception as e:
        print(f'Error joinging room: {e.__traceback__}')

def send_token(connection, token_row, status_code):
    try:
        status = status_code.to_bytes(1, 'big')
        # token は16バイト
        token = token_row.bytes
        # data は17バイト
        data = status + token
        connection.send(data)
    except Exception as e:
        print(f'Error sending token: {e.__class__.__name__}: {str(e)}')

if __name__ == "__main__":
    main()
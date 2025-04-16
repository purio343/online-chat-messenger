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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    threading.Thread(target=cleanup_clients, args=(clients, timeout), daemon=True).start()
    sock.bind((server_address, port))
    # クライアントの情報を連想配列で保持。
    
    print(f'Server started on {server_address}:{port}')

    while True:
        # sock.recvfrom() はバイト列を返す。
        try:
            data, address = sock.recvfrom(rate)

            print(f"Received {len(data)} bytes from {address}")

            username_length = int.from_bytes(data[:1], 'big') 
            username = data[1:username_length + 1].decode('utf-8')
            message = data[username_length + 1:].decode('utf-8')

            # クライアント情報を更新、または追加。
            with lock:
                clients[address] = {
                    "user_name": username,
                    "message": message,
                    # datetime.datetime.now() は、現在日時を取得する。
                    "last_seen": datetime.datetime.now(),
                    "failed_count": 0
                }

            # 全クライアントに送信。
            for client in list(clients.keys()):
                try:
                    if client != address:
                        sock.sendto(data, client)
                except Exception as e:
                    print(f'Error sending to {client}: {e}')
                    clients[client]["failed_count"] += 1
                    if clients[client]["failed_count"] >= max_fails:
                        print(f'Removing {client} due to too many failures')
                        del clients[client]

        except KeyboardInterrupt:
            print('Server shutting down')
            break

        except Exception as e:
            print(f'Server error: {e}')

# 各クライアントの最終更新日時を取得して、一定時間送信していない場合は管理用の連想配列から削除
def cleanup_clients(clients, timeout=60):
    while True:
        now = datetime.datetime.now()
        remove_list = []
        with lock:
            for address, information in list(clients.items()):
                if (now - information["last_seen"]).total_seconds() > timeout:
                    remove_list.append(address)
            for addr in remove_list:
                print(f'Removing {addr} due to inactivity')
                del clients[addr]
        time.sleep(10)

def tcp_handler():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((server_address, port))
    sock.listen(5)

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
    client_token = uuid.uuid4()
    rooms[roomname]["host"][address] = {
        "user_name": username,
        "client_token": client_token
    }
    send_token(connection, address, client_token)

def join_room(connection, address, username, roomname):
    client_token = uuid.uuid4()
    # ゲスト（ホスト以外のユーザー）として部屋に追加
    rooms[roomname]["guest"][address] ={
        "user_name": username,
        "client_token": client_token,
    }
    send_token(connection, address, client_token)

def send_token(connection, address, token):
    status_code = str(200).to_bytes(1, 'big')
    token = token.bytes()
    # 17バイト
    data = status_code + token
    connection.send(data, address)

if __name__ == "__main__":
    main()
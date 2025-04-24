import socket
import datetime
import time
import threading
import uuid

server_address = '0.0.0.0'
port = 9001
udp_port = 9002
rate = 4096
max_fails = 3
clients = {}
rooms = {}
timeout = 60
lock = threading.Lock()

def main():
    tcp_thread = threading.Thread(target=tcp_handler, daemon=True)
    udp_thread = threading.Thread(target=udp_handler, daemon=True)
    cleanup_thread = threading.Thread(target=cleanup_clients, daemon=True, args=(rooms, timeout))
    tcp_thread.start()
    udp_thread.start()
    # cleanup_thread.start()
    # tcp_threadが終了するまで待機
    tcp_thread.join()
    udp_thread.join()
    # cleanup_thread.join()

def udp_handler():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((server_address, udp_port))
    print(f'UDP server is runnning on {server_address}:{udp_port}')
    while True:
        try:
            data, address = sock.recvfrom(rate)
            print(f'UDP message received from {address}')
            # ヘッダーは2バイト。
            # 1バイト目は部屋名の長さ。
            # 2バイト目はトークンの長さ。
            header = data[:2]
            body = data[2:]
            roomname_length = int.from_bytes(header[:1], 'big')
            token_length = int.from_bytes(header[1:2], 'big')
            print(f'roomname_length: {roomname_length}')
            print(f'token_length: {token_length}')
            roomname = body[:roomname_length].decode('utf-8')
            print(f'roomname: {roomname}')
            token = body[roomname_length:roomname_length + token_length]
            print(f'token: {uuid.UUID(bytes=token)}')
            message = body[roomname_length + token_length:].decode('utf-8')
            print(f'message: {message}')
            if authentication_token(roomname, address, token):
                send_message(roomname, message, sock)
        except Exception as e:
            print(f'UDP error: {str(e)}')


def tcp_handler():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((server_address, port))
    sock.listen(5)
    print(f'TCP server is runnning on {server_address}:{port}')

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
                username = operation_payload.decode('utf-8')
                print(f'Creating room {roomname} by {username}')
                create_room(connection, address, username, roomname)
            elif operation == 2:
                username = operation_payload.decode('utf-8')
                if roomname not in rooms:
                    connection.close()
                    return
                print(f'Joining {roomname} by {username}')
                join_room(connection, address, username, roomname)

        except Exception as e:
            print(f'An error occurred: {e}')
        finally:
            connection.close()
            print('TCP connection closed')

def create_room(connection, address, username, roomname):
    try:
        client_token = uuid.uuid4()
        # 部屋が存在しない場合、部屋を新規に作成。
        with lock:
            if roomname not in rooms:
                rooms[roomname] = {
                    "host": {},
                    "guest": {}
                }
        # 作成した部屋にホストとして追加。
            rooms[roomname]["host"][address] = {
                "user_name": username,
                "client_token": client_token,
                "last_seen": datetime.datetime.now()
            }
        print(f'client_token: {client_token}')
        print(f'rooms: {rooms}')
        send_token(connection, client_token, 1)
    except Exception as e:
        print(f'Error creating: {e.__traceback__}')

def join_room(connection, address, username, roomname):
    try:
        client_token = uuid.uuid4()
        # ゲスト（ホスト以外のユーザー）として部屋に追加
        with lock:
            rooms[roomname]["guest"][address] ={
                "user_name": username,
                "client_token": client_token,
                "last_seen": datetime.datetime.now()
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

# udp接続時の認証
def authentication_token(roomname, address, token):
    if roomname not in rooms:
        print(f'Room {roomname} is not found')
        return False
    
    #　クライアント（ゲスト）から送信されたトークンが一致した場合Trueを返す。
    if address in rooms[roomname]["guest"]:
        return rooms[roomname]["guest"][address]["client_token"] == uuid.UUID(bytes=token)
    
    # クライアント（ホスト）から送信されたトークンが一致した場合Trueを返す。
    if address in rooms[roomname]["host"]:
        return rooms[roomname]["host"][address]["client_token"] == uuid.UUID(bytes=token)
    
    print(f'Address {address} is not found in {roomname}')
    return False

# その部屋に属するユーザーにメッセージを送信する処理
def send_message(roomname, message, sock):
    try:
        # 部屋が存在しない場合はエラー
        if roomname not in rooms:
            raise Exception(f'room {roomname} is not found')
        
         # メッセージ送信前に部屋情報を表示（デバッグ用）
        print(f'Before sending - rooms content: {rooms}')

        print(f'Sending message to {roomname}')
        # その部屋のホストにメッセージを送信
        for address in rooms[roomname]["host"]:
            try:
                sock.sendto(message.encode('utf-8'), address)
            except Exception as e:
                print(f'Error sending message to {address}')
        # その部屋のゲストにメッセージを送信
        for address in rooms[roomname]["guest"]:
            try:
                sock.sendto(message.encode('utf-8'), address)
            except Exception as e:
                print(f'Error sending message to {address}')
         # メッセージ送信前に部屋情報を表示（デバッグ用）
        print(f'After sending - rooms content: {rooms}')
    except Exception as e:
        print(f'An error occurred sending message: {str(e)}')

# 部屋に属するユーザーの最終更新日時を取得して、一定時間動きがない場合は部屋から削除
def cleanup_clients(rooms, timeout=60):
    while True:
        now = datetime.datetime.now()
        with lock:
            for roomname, information in list(rooms.items()):
                for address, user in list(information["host"].items()):
                    if (now - user["last_seen"]).total_seconds() > timeout:
                        del information["host"][address]
                        # ホストが削除された場合、部屋ごと削除？
                        # del rooms[roomname]
                for address, user in list(information["guest"].items()):
                    if (now - user["last_seen"]).total_seconds() > timeout:
                        del information["guest"][address]            
        time.sleep(30)

if __name__ == "__main__":
    main()
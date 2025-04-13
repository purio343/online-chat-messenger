import socket
import datetime
import time
import threading

server_address = '0.0.0.0'
port = 9001
rate = 4096
max_fails = 3
clients = {}
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

if __name__ == "__main__":
    main()
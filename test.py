import socket
import subprocess
import threading

def handle_client(client_socket):
    greeting = b"\x4a\x00\x00\x00\x0a\x35\x2e\x30\x2e\x31\x32\x00\x0e\x3c\x12\x00\x52\x49\x3a\x24\x05\x73\x63\x75\x72\x65\x40\x6d\x79\x73\x71\x6c\x5f\x6e\x61\x74\x69\x76\x65\x5f\x70\x61\x73\x73\x77\x6f\x72\x64\x00"
    client_socket.sendall(greeting)

    mysql_cli = subprocess.Popen(["mysql", "-u", "username", "-ppassword", "databasename"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def read_from_mysql():
        while True:
            output = mysql_cli.stdout.readline()
            if not output:
                break
            client_socket.send(output)

    def read_from_client():
        while True:
            client_data = client_socket.recv(4096)
            if not client_data:
                break
            mysql_cli.stdin.write(client_data)
            mysql_cli.stdin.flush()

    mysql_reader_thread = threading.Thread(target=read_from_mysql)
    mysql_reader_thread.start()

    client_reader_thread = threading.Thread(target=read_from_client)
    client_reader_thread.start()

    try:
        while mysql_reader_thread.is_alive() and client_reader_thread.is_alive():
            continue
    except KeyboardInterrupt:
        pass

    mysql_reader_thread.join()
    client_reader_thread.join()
    mysql_cli.stdin.close()
    mysql_cli.stdout.close()
    mysql_cli.stderr.close()
    client_socket.close()

def main():
    proxy_host = '127.0.0.1'
    proxy_port = 3307  # Choose a port that's not already in use

    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind((proxy_host, proxy_port))
    proxy_socket.listen(5)

    print(f"Proxy listening on {proxy_host}:{proxy_port}")

    try:
        while True:
            client_socket, addr = proxy_socket.accept()
            print(f"Accepted connection from {addr[0]}:{addr[1]}")
            client_handler = threading.Thread(target=handle_client, args=(client_socket,))
            client_handler.start()
    except KeyboardInterrupt:
        print("Proxy stopped.")

if __name__ == "__main__":
    main()

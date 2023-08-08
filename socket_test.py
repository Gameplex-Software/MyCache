import socket

def main():
    host = "localhost"
    port = 3308

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    while True:
        response = client_socket.recv(1024).decode()
        if not response:
            break
        print(response)

        if "Goodbye!" in response:
            break

        command = input()
        client_socket.send(command.encode())

    client_socket.close()

if __name__ == "__main__":
    main()

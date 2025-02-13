import socket
import select
import sys


def main():
    if len(sys.argv) != 2:
        print("Usage: python chat.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])

    # Initialize server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", port))
    server_socket.listen(5)

    print(f"Chat server started on port {port}")

    # List to keep track of sockets
    sockets_list = [server_socket]
    clients = {}

    while True:
        read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

        for notified_socket in read_sockets:
            if notified_socket == server_socket:
                client_socket, client_address = server_socket.accept()
                sockets_list.append(client_socket)
                clients[client_socket] = client_address
                print(f"New connection from {client_address}")
            else:
                try:
                    message = notified_socket.recv(1024).decode('utf-8')
                    if message:
                        print(f"Received: {message}")
                    else:
                        sockets_list.remove(notified_socket)
                        del clients[notified_socket]
                        notified_socket.close()
                except:
                    sockets_list.remove(notified_socket)
                    del clients[notified_socket]
                    notified_socket.close()

        for notified_socket in exception_sockets:
            sockets_list.remove(notified_socket)
            del clients[notified_socket]
            notified_socket.close()


if __name__ == "__main__":
    main()

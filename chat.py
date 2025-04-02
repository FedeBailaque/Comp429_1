import socket
import select
import sys
import threading
import ipaddress

running = True
active_connections = {}  # {id: (socket, (ip, port))}
lock = threading.Lock()


# Get the local IP address of machine
def get_my_ip():
    try:
        host_name = socket.gethostname()
        ip_list = socket.gethostbyname_ex(host_name)[2]
        for ip in ip_list:
            if not ip.startswith("127."):
                return ip
        return "Unable to determine external IP"
    except Exception as e:
        print(f"Error retrieving IP: {e}")
        return None

# get port server is listening on
def get_my_port(server_socket):
    return server_socket.getsockname()[1]


# menu commands
def display_help():
    print("""
Commands:
  help - list of commands
  myip - display IP address
  myport - display port that is listening
  connect <IP> <PORT> - establish connection with IP and port
  list - display all active connections
  terminate <connection id> - close a specific connection
  send <connection id> <message> - send a message to a connection
  exit - terminate all processes and connections
""")


# listens for incoming messages on a socket
def handle_peer_messages(sock, addr):
    global active_connections
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                print(f"\nConnection closed by {addr}")
                break
            message = data.decode()
            print(f"\nMessage received from {addr[0]}\nSender’s Port: {addr[1]}\nMessage: “{message}”\n>>> ", end='')
    except Exception as e:
        print(f"\nError receiving message from {addr}: {e}")
    finally:
        # when connection ends, close socket and remove from list
        sock.close()
        with lock:
            conn_to_remove = None
            for conn_id, (_, a) in active_connections.items():
                if a == addr:
                    conn_to_remove = conn_id
                    break
            if conn_to_remove:
                del active_connections[conn_to_remove]
                print(f"\nConnection with {addr[0]}:{addr[1]} removed (ID: {conn_to_remove})\n>>> ", end='')


# connects peers and sends peers IP:PORT
def connect_to_peer(ip, port, server_socket):
    try:
        ipaddress.ip_address(ip)
        port = int(port)

        if get_my_ip() == ip and get_my_port(server_socket) == port:
            print("Error: Cannot connect to yourself.")
            return None

        for _, (_, addr) in active_connections.items():
            if addr == (ip, port):
                print(f"Error: Already connected to {ip}:{port}.")
                return None

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))

        my_info = f"{get_my_ip()}:{get_my_port(server_socket)}"
        s.sendall(my_info.encode())

        print(f"Connected to {ip}:{port}")
        threading.Thread(target=handle_peer_messages, args=(s, (ip, port)), daemon=True).start()
        return s
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

# This function handles user input for commands and manages connections
def handle_user_input(server_socket):
    global running
    while running:
        try:
            command = input(">>> ").strip()
            if not running:
                break

            if command == "help":
                display_help()
            elif command == "myip":
                print(f"My IP: {get_my_ip()}")
            elif command == "myport":
                print(f"My Port: {get_my_port(server_socket)}")
            elif command.startswith("connect "):
                parts = command.split()
                if len(parts) == 3:
                    ip, port = parts[1], parts[2]
                    new_sock = connect_to_peer(ip, port, server_socket)
                    if new_sock:
                        with lock:
                            conn_id = len(active_connections) + 1
                            active_connections[conn_id] = (new_sock, (ip, int(port)))
                        print(f"Connected to {ip}:{port} (ID: {conn_id})")
                else:
                    print("Usage: connect <IP> <PORT>")
            elif command == "list":
                print("Active Connections:")
                with lock:
                    for conn_id, (_, addr) in active_connections.items():
                        print(f"  {conn_id}: {addr[0]}:{addr[1]}")
            elif command.startswith("terminate "):
                parts = command.split()
                if len(parts) == 2:
                    try:
                        conn_id = int(parts[1])
                        with lock:
                            if conn_id in active_connections:
                                active_connections[conn_id][0].close()
                                del active_connections[conn_id]
                                print(f"Connection {conn_id} terminated.")
                            else:
                                print("Invalid connection ID.")
                    except ValueError:
                        print("Usage: terminate <connection id>")
                else:
                    print("Usage: terminate <connection id>")
            elif command.startswith("send "):
                parts = command.split(maxsplit=2)
                if len(parts) == 3:
                    try:
                        conn_id = int(parts[1])
                        message = parts[2]
                        with lock:
                            if conn_id in active_connections:
                                active_connections[conn_id][0].sendall(message.encode())
                                print(f"Sent: {message}")
                            else:
                                print("Invalid connection ID.")
                    except ValueError:
                        print("Usage: send <connection id> <message>")
                else:
                    print("Usage: send <connection id> <message>")
            elif command == "exit":
                print("Shutting down...")
                running = False
                break
            else:
                print("Unknown command. Type 'help' for a list of commands.")
        except (EOFError, KeyboardInterrupt):
            running = False


# Main function to start the server and handle incoming connections
def main():
    global running

    if len(sys.argv) != 2:
        print("Usage: python3 chat.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", port))
    server_socket.listen(5)

    print(f"Server started on port {port}")
    display_help()

    input_thread = threading.Thread(target=handle_user_input, args=(server_socket,), daemon=True)
    input_thread.start()

    try:
        while running:
            read_sockets, _, _ = select.select([server_socket], [], [], 1)
            if not running:
                break
            for notified_socket in read_sockets:
                client_socket, client_addr = server_socket.accept()
                peer_info = client_socket.recv(1024).decode()
                if ":" not in peer_info:
                    print(f"Invalid peer info received: '{peer_info}'")
                    client_socket.close()
                    continue
                peer_ip, peer_port = peer_info.split(":")
                peer_port = int(peer_port)

                with lock:
                    for _, (_, addr) in active_connections.items():
                        if addr == (peer_ip, peer_port):
                            print(f"Duplicate connection from {peer_ip}:{peer_port} ignored.")
                            client_socket.close()
                            break
                    else:
                        conn_id = len(active_connections) + 1
                        active_connections[conn_id] = (client_socket, (peer_ip, peer_port))
                        print(f"New connection from {peer_ip}:{peer_port} (ID: {conn_id})")
                        threading.Thread(target=handle_peer_messages, args=(client_socket, (peer_ip, peer_port)), daemon=True).start()

    except KeyboardInterrupt:
        print("\nCaught Ctrl+C in main thread.")
        running = False

    print("Closing all sockets...")
    for _, (sock, _) in active_connections.items():
        sock.close()
    server_socket.close()
    print("Goodbye!")
    sys.exit(0)

if __name__ == "__main__":
    main()

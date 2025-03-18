import socket
import select
import sys
import threading
import ipaddress

# Global vars
running = True
active_connections = {}  # Dictionary to track active connections {id: (socket, (ip, port))}

def get_my_ip():
    """Retrieve the external IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        print(f"Error retrieving IP: {e}")
        return None

def get_my_port(server_socket):
    """Retrieve the port the server is listening on."""
    return server_socket.getsockname()[1]

def display_help():
    """Display the list of available commands."""
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

def connect_to_peer(ip, port):
    """Establish a TCP connection to a peer, ensuring the IP is valid."""
    global connections
    try:
        # Validate the IP address format
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            print(f"Error: Invalid IP address '{ip}'.")
            return None

        port = int(port)
        if get_my_ip() == ip:
            print("Error: Cannot connect to yourself.")
            return None

        # Check if the connection already exists
        for conn in connections:
            if conn.getpeername() == (ip, port):
                print(f"Error: Already connected to {ip}:{port}.")
                return None

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        connections.append(s)  # Store the new connection
        print(f"Connected to {ip}:{port}")
        return s
    except Exception as e:
        print(f"Connection failed: {e}")
        return None


def handle_user_input(server_socket):
    """Handles user commands."""
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
                    new_sock = connect_to_peer(ip, port)
                    if new_sock:
                        conn_id = len(active_connections) + 1
                        active_connections[conn_id] = (new_sock, (ip, int(port)))
                        print(f"Connected to {ip}:{port} (ID: {conn_id})")
                else:
                    print("Usage: connect <IP> <PORT>")
            elif command == "list":
                print("Active Connections:")
                for conn_id, (_, addr) in active_connections.items():
                    print(f"  {conn_id}: {addr[0]}:{addr[1]}")
            elif command.startswith("terminate "):
                parts = command.split()
                if len(parts) == 2:
                    try:
                        conn_id = int(parts[1])
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

def main():
    global running

    if len(sys.argv) != 2:
        print("Usage: python3 main.py <port>")
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
                conn_id = len(active_connections) + 1
                active_connections[conn_id] = (client_socket, client_addr)
                print(f"New connection from {client_addr} (ID: {conn_id})")

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

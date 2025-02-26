import socket
import select
import sys
import threading

# Global vars
running = True
active_connection = None  # Global reference for the "active" peer socket

def get_my_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)) # google dns
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        print(f"Error retrieving IP: {e}")
        return None

def get_my_port(server_socket):
    return server_socket.getsockname()[1]

def display_help():
    print("""
Commands:
  help - list of commands
  myip - display IP address
  myport - display port that is listening
  connect <IP> <PORT> - establish connection with IP and port
  exit - terminate all processes and connections
""")

def connect_to_peer(ip, port, sockets_list, clients):
    try:
        port = int(port)
        # handles connecting to self error
        if get_my_ip() == ip:
            print("Error: Cannot connect to yourself.")
            return None
        # handles duplicate peer error
        for s in clients:
            if clients[s] == (ip, port):
                print("Error: Already connected to this peer.")
                return None
        # Create and connect
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        sockets_list.append(s)
        clients[s] = (ip, port)
        print(f"Connected to {ip}:{port}")
        return s
    except (ValueError, socket.error) as e:
        print(f"Connection failed: {e}")
        return None

def handle_user_input(server_socket, sockets_list, clients):
    global running
    global active_connection

    try:
        while running:
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
                    new_sock = connect_to_peer(parts[1], parts[2], sockets_list, clients)
                    if new_sock:
                        active_connection = new_sock
                else:
                    print("Usage: connect <IP> <port>")

            elif command == "exit":
                print("Shutting down...")
                # Instead of closing sockets here, set running=False
                running = False
                break

            else:
                # if user input not a command, then treated as normal input
                if active_connection:
                    try:
                        active_connection.send(command.encode('utf-8'))
                        print(f"Sent: {command}")
                    except:
                        print("Error: Failed to send message.")
                else:
                    print("Error: No active connection. Use 'connect <IP> <port>' first.")

# shutdown program using ctrl + c solution
    except (EOFError, KeyboardInterrupt):
        running = False  

def main():
    global running
    global active_connection

    if len(sys.argv) != 2:
        print("Usage: python chat.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", port))
    server_socket.listen(5)

    sockets_list = [server_socket]
    clients = {}

    print(f"Server started on port {port}")
    display_help()

    # user-input thread 
    input_thread = threading.Thread(
        target=handle_user_input,
        args=(server_socket, sockets_list, clients),
        daemon=True
    )
    input_thread.start()

    try:
        while running:
            # Use a small timeout in select so we can check 'running' regularly
            read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list, 1)

            # If 'running' was set to False while we were in select, bail out
            if not running:
                break

            for notified_socket in read_sockets:
                if notified_socket == server_socket:
                    client_socket, client_addr = server_socket.accept()
                    sockets_list.append(client_socket)
                    clients[client_socket] = client_addr
                    print(f"New connection from {client_addr}")
                else:
                    try:
                        data = notified_socket.recv(1024)
                        if data:
                            msg = data.decode('utf-8')
                            print(f"\nMessage from {clients[notified_socket]}: {msg}")
                            # Make this the new active connection if you wish
                            active_connection = notified_socket
                            print(">>> ", end="", flush=True)  # re-print prompt
                        else:
                            # Connection closed
                            print(f"Peer {clients[notified_socket]} disconnected.")
                            sockets_list.remove(notified_socket)
                            del clients[notified_socket]
                            notified_socket.close()
                    except:
                        print(f"Error with {clients[notified_socket]}. Disconnecting.")
                        sockets_list.remove(notified_socket)
                        del clients[notified_socket]
                        notified_socket.close()

            # Handle exception sockets
            for err_socket in exception_sockets:
                sockets_list.remove(err_socket)
                del clients[err_socket]
                err_socket.close()

    # this is solution in fixing ctrl + c issue of not fully shutting down socket, causing it to be in an infinite loop halt
    except KeyboardInterrupt:
        print("\nCaught Ctrl+C in main thread.")
        running = False

    # ctrl + c or typing exit closes all sockets and throws a message
    print("Closing all sockets...")
    for s in sockets_list:
        try:
            s.shutdown(socket.SHUT_RDWR)
        except:
            pass
        s.close()

    print("Goodbye!")
    sys.exit(0)

if __name__ == "__main__":
    main()

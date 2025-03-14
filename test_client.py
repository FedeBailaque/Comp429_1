import socket
import time

def test_single_client(server_ip, port):
    """Test connecting a single client to the server."""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_ip, port))
        print("Successfully connected to the server.")
        time.sleep(1)
        client_socket.close()
        print("Connection closed properly.")
    except Exception as e:
        print(f"Failed to connect: {e}")

def test_multiple_clients(server_ip, port, num_clients=3):
    """Test connecting multiple clients to the server."""
    clients = []
    try:
        for i in range(num_clients):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((server_ip, port))
            clients.append(s)
            print(f"Client {i + 1} connected.")
        time.sleep(2)
        for s in clients:
            s.close()
        print("All clients disconnected successfully.")
    except Exception as e:
        print(f"Error in multiple client connection: {e}")

if __name__ == "__main__":
    SERVER_IP = "127.0.0.1"  # Replace with actual server IP if needed
    PORT = 4322
    print("\nRunning Tests...\n")
    test_single_client(SERVER_IP, PORT)
    test_multiple_clients(SERVER_IP, PORT, num_clients=3)

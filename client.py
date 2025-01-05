import socket
import struct
import threading
import time

def listen_for_offers():
    """Listen for UDP broadcast offers from servers."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(("", 13117))
        print("\033[96mClient started, listening for offer requests...\033[0m")
        
        while True:
            data, addr = udp_socket.recvfrom(1024)
            try:
                magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!IBHH', data)
                if magic_cookie == 0xabcddcba and message_type == 0x2:
                    print(f"\033[92mReceived offer from {addr[0]} (UDP Port: {udp_port}, TCP Port: {tcp_port})\033[0m")
                    handle_server_offer(addr[0], udp_port, tcp_port)
            except Exception as e:
                print(f"\033[91mError parsing offer: {e}\033[0m")

def handle_server_offer(server_ip, udp_port, tcp_port):
    """Handle the server's offer by initiating TCP and UDP connections."""
    # Get user input for file size and number of connections
    file_size = int(input("Enter the file size to download (bytes): "))
    tcp_connections = int(input("Enter the number of TCP connections: "))
    udp_connections = int(input("Enter the number of UDP connections: "))

    # Start threads for TCP and UDP transfers
    threads = []
    for i in range(tcp_connections):
        t = threading.Thread(target=tcp_transfer, args=(server_ip, tcp_port, file_size, i + 1))
        threads.append(t)
        t.start()

    for i in range(udp_connections):
        t = threading.Thread(target=udp_transfer, args=(server_ip, udp_port, file_size, i + 1))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("\033[96mAll transfers complete, listening to offer requests\033[0m")

def tcp_transfer(server_ip, tcp_port, file_size, connection_id):
    """Perform a file transfer over TCP."""
    start_time = time.time()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_ip, tcp_port))
            tcp_socket.sendall(f"{file_size}\n".encode())
            
            received_data = 0
            while received_data < file_size:
                chunk = tcp_socket.recv(1024)
                if not chunk:
                    break
                received_data += len(chunk)

        total_time = time.time() - start_time
        speed = file_size / total_time
        print(f"\033[92mTCP transfer #{connection_id} finished, total time: {total_time:.2f} seconds, total speed: {speed:.2f} bytes/second\033[0m")
    except Exception as e:
        print(f"\033[91mTCP transfer #{connection_id} failed: {e}\033[0m")

def udp_transfer(server_ip, udp_port, file_size, connection_id):
    """Perform a file transfer over UDP."""
    start_time = time.time()
    total_segments = file_size // 1024
    received_segments = set()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.sendto(struct.pack('!IBQ', 0xabcddcba, 0x3, file_size), (server_ip, udp_port))
            
            udp_socket.settimeout(1.0)
            while True:
                try:
                    data, _ = udp_socket.recvfrom(2048)
                    magic_cookie, message_type, total, current = struct.unpack('!IBQQ', data[:21])
                    if magic_cookie == 0xabcddcba and message_type == 0x4:
                        received_segments.add(current)
                except socket.timeout:
                    break

        total_time = time.time() - start_time
        speed = (len(received_segments) * 1024) / total_time
        received_percentage = (len(received_segments) / total_segments) * 100
        print(f"\033[93mUDP transfer #{connection_id} finished, total time: {total_time:.2f} seconds, total speed: {speed:.2f} bytes/second, percentage of packets received successfully: {received_percentage:.2f}%\033[0m")
    except Exception as e:
        print(f"\033[91mUDP transfer #{connection_id} failed: {e}\033[0m")

def start_client():
    """Start the client application."""
    try:
        listen_for_offers()
    except KeyboardInterrupt:
        print("\n\033[91mClient shutting down...\033[0m")

if __name__ == "__main__":
    start_client()

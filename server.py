import socket
import struct
import threading
import time
import sys

def udp_broadcast(server_port, tcp_port, stop_event):
    """Broadcast offer messages via UDP."""
    magic_cookie = 0xabcddcba
    message_type = 0x2
    message = struct.pack('!IBHH', magic_cookie, message_type, server_port, tcp_port)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while not stop_event.is_set():
            udp_socket.sendto(message, ('<broadcast>', 13117))
            print(f"\033[94m[UDP]\033[0m Broadcasted offer on UDP port {server_port}, TCP port {tcp_port}")
            time.sleep(1)

def handle_tcp_client(client_socket, file_size):
    """Handle TCP client connection by sending the requested data size."""
    try:
        data = b'0' * int(file_size)
        client_socket.sendall(data)
        print(f"\033[92m[TCP]\033[0m Sent {file_size} bytes to client")
    finally:
        client_socket.close()

def handle_udp_request(server_socket, client_address, file_size):
    """Send data to the client over UDP."""
    try:
        total_segments = int(file_size) // 1024 + 1
        for i in range(total_segments):
            payload = struct.pack('!IBQQ', 0xabcddcba, 0x4, total_segments, i) + b'X' * 1024
            server_socket.sendto(payload, client_address)
        print(f"\033[93m[UDP]\033[0m Sent {total_segments} segments to {client_address}")
    except Exception as e:
        print(f"\033[91m[UDP]\033[0m Error handling request from {client_address}: {e}")

def tcp_server(server_port, stop_event):
    """TCP server to handle incoming connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind(("", server_port))
        tcp_socket.listen()
        print(f"\033[94m[TCP]\033[0m Server listening on port {server_port}")

        while not stop_event.is_set():
            tcp_socket.settimeout(1.0)
            try:
                client_socket, addr = tcp_socket.accept()
                file_size = client_socket.recv(1024).decode().strip()
                print(f"\033[92m[TCP]\033[0m Received request from {addr}, file size: {file_size} bytes")
                threading.Thread(target=handle_tcp_client, args=(client_socket, file_size), daemon=True).start()
            except socket.timeout:
                pass # Exception is expected, continue looping

def udp_server(server_port, stop_event):
    """UDP server to handle incoming requests."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind(("", server_port))
        print(f"\033[94m[UDP]\033[0m Server listening on port {server_port}")

        while not stop_event.is_set():
            udp_socket.settimeout(1.0) 
            try:
                data, addr = udp_socket.recvfrom(2048)
                try:
                    magic_cookie, message_type, file_size = struct.unpack('!IBQ', data)
                    if magic_cookie != 0xabcddcba or message_type != 0x3:
                        print(f"\033[91m[UDP]\033[0m Invalid request from {addr}")
                        continue

                    print(f"\033[92m[UDP]\033[0m Received valid request from {addr}, file size: {file_size} bytes")
                    threading.Thread(target=handle_udp_request, args=(udp_socket, addr, file_size), daemon=True).start()
                except Exception as e:
                    print(f"\033[91m[UDP]\033[0m Error processing request: {e}")
            except socket.timeout:
                pass  # Exception is expected, continue looping

def start_server():
    """Start the server and its components."""
    server_port = 20001
    tcp_port = 20002

    print(f"\033[96mServer started, listening on IP address {socket.gethostbyname(socket.gethostname())}\033[0m")

    stop_event = threading.Event()

    udp_broadcast_thread = threading.Thread(target=udp_broadcast, args=(server_port, tcp_port, stop_event), daemon=True)
    tcp_server_thread = threading.Thread(target=tcp_server, args=(tcp_port, stop_event), daemon=True)
    udp_server_thread = threading.Thread(target=udp_server, args=(server_port, stop_event), daemon=True)

    udp_broadcast_thread.start()
    tcp_server_thread.start()
    udp_server_thread.start()

    return stop_event, [udp_broadcast_thread, tcp_server_thread, udp_server_thread]

if __name__ == "__main__":
    try:
        stop_event, threads = start_server()
        while True:
            time.sleep(1)  # Main thread just waits, the server continues to run
    except KeyboardInterrupt:
        print("\n\033[91m[Server] Shutting down...\033[0m")
        stop_event.set()  # Signal threads to stop
        # Wait for threads to finish their work
        for thread in threads:
            thread.join()
        print("\033[91m[Server] Server shutdown complete.\033[0m")
        sys.exit(0)

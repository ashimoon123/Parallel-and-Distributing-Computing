"""
worker.py - Laptop 2 (Worker Node)
Role:
1. Listens on TCP port 5001 for Laptop 1 (Master).
2. Receives Part 2 of the video.
3. Processes Part 2 (applying the chosen filter with FFmpeg).
4. Transmits the processed Part 2 back to Laptop 1.
"""

import os
import sys
import time
import socket
from common import (
    DEFAULT_PORT,
    SOCKET_TIMEOUT,
    check_ffmpeg_installed,
    receive_file,
    send_file,
    send_msg,
    recv_msg,
    process_video
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

PART2_INPUT = os.path.join(INPUT_DIR, "worker_part2.mp4")
PART2_OUTPUT = os.path.join(OUTPUT_DIR, "worker_processed_part2.mp4")

def run_worker(host="0.0.0.0", port=DEFAULT_PORT):
    if not check_ffmpeg_installed():
        return

    print("=" * 60)
    print("      DISTRIBUTED VIDEO PROCESSING - WORKER (LAPTOP 2)      ")
    print("=" * 60)
    print(f"[*] Worker Node active.")
    print(f"[*] Binding to {host}:{port} and awaiting Master connection...")

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Enable address reuse so restarting the script works immediately without waiting
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_sock.bind((host, port))
        server_sock.listen(1)
        print("[*] Ready. Waiting for Master (Laptop 1) to connect...\n")

        while True:
            try:
                conn, client_addr = server_sock.accept()
                conn.settimeout(SOCKET_TIMEOUT)
                print(f"[+] Master connected from {client_addr[0]}:{client_addr[1]}")

                # Step 1: Handshake
                handshake = recv_msg(conn)
                if handshake != "HELLO_WORKER":
                    print(f"[!] Unknown handshake message: {handshake}")
                    conn.close()
                    continue
                
                send_msg(conn, "WORKER_READY")
                print("[*] Handshake complete. Waiting to receive Part 2...")

                # Step 2: Receive Part 2 from Master
                receive_file(conn, PART2_INPUT, label="Receiving Part 2 from Master")
                send_msg(conn, "PART2_RECEIVED")

                # Step 3: Process Part 2 using FFmpeg
                print("\n" + "-" * 50)
                print("[*] Starting local FFmpeg processing on Part 2...")
                proc_start = time.time()
                process_video(PART2_INPUT, PART2_OUTPUT, filter_type="grayscale")
                proc_elapsed = time.time() - proc_start
                print(f"[+] Worker processing completed in {proc_elapsed:.2f} seconds.")
                print("-" * 50)

                # Step 4: Notify Master that processing is complete
                send_msg(conn, f"DONE:{proc_elapsed:.2f}")

                # Step 5: Wait for Master to request download
                request = recv_msg(conn)
                if request == "GET_PROCESSED_PART2":
                    send_file(conn, PART2_OUTPUT, label="Sending Processed Part 2 to Master")
                    print("[+] Part 2 successfully delivered to Master.")
                
                print("\n[+] Task complete! Worker waiting for next job...\n")
                conn.close()

            except (ConnectionResetError, socket.timeout) as net_err:
                print(f"[!] Network connection issue: {net_err}")
                print("[*] Resetting listener for next connection...")
            except Exception as e:
                print(f"[!] Unexpected error occurred: {e}")
                import traceback
                traceback.print_exc()

    except KeyboardInterrupt:
        print("\n[*] Worker stopping per user request.")
    finally:
        server_sock.close()
        print("[*] Worker socket closed.")

if __name__ == "__main__":
    run_worker()

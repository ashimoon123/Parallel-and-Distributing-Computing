"""
master.py - Laptop 1 (Master Node)
Role:
1. Validates input video and checks FFmpeg.
2. Splits the video into two equal halves (Part 1 and Part 2).
3. Connects to Laptop 2 (Worker) with retry logic.
4. Sends Part 2 to Worker over TCP.
5. Processes Part 1 locally on Laptop 1 WHILE Worker processes Part 2 (Simultaneous Execution).
6. Receives the processed Part 2 back from Worker.
7. Merges both processed segments into final_video.mp4.
8. Prints a complete latency and execution time breakdown.
"""

import os
import sys
import time
import socket
from common import (
    DEFAULT_PORT,
    SOCKET_TIMEOUT,
    check_ffmpeg_installed,
    get_video_duration,
    split_video,
    process_video,
    merge_videos,
    send_file,
    receive_file,
    send_msg,
    recv_msg
)

WORKER_IP = "192.168.1.2"   # Static IP of Laptop 2
WORKER_PORT = DEFAULT_PORT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

INPUT_VIDEO = os.path.join(INPUT_DIR, "sample.mp4")
PART1_VIDEO = os.path.join(INPUT_DIR, "part1.mp4")
PART2_VIDEO = os.path.join(INPUT_DIR, "part2.mp4")
PROCESSED_PART1 = os.path.join(OUTPUT_DIR, "processed_part1.mp4")
PROCESSED_PART2 = os.path.join(OUTPUT_DIR, "processed_part2.mp4")
FINAL_OUTPUT = os.path.join(OUTPUT_DIR, "final_video.mp4")

def connect_to_worker(ip: str, port: int, max_retries: int = 5, retry_delay: int = 2) -> socket.socket:
    """Attempt connection to Worker with automated retries."""
    print(f"[*] Connecting to Worker ({ip}:{port})...")
    for attempt in range(1, max_retries + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect((ip, port))
            print(f"[+] Successfully connected to Worker on attempt {attempt}.")
            return sock
        except (socket.error, ConnectionRefusedError) as e:
            print(f"    [Attempt {attempt}/{max_retries}] Worker not reachable yet ({e}). Waiting {retry_delay}s...")
            time.sleep(retry_delay)
    raise ConnectionError(f"Could not connect to Worker at {ip}:{port} after {max_retries} attempts.")

def run_distributed_pipeline(worker_ip=WORKER_IP, worker_port=WORKER_PORT):
    if not check_ffmpeg_installed():
        return None

    if not os.path.exists(INPUT_VIDEO):
        print("\n" + "=" * 65)
        print(f" [!] Input video not found at: {INPUT_VIDEO}")
        print(" Please place your test video inside the 'input' folder named 'sample.mp4'")
        print(" Or run 'python generate_sample_video.py' to create a test video.")
        print("=" * 65 + "\n")
        return None

    print("\n" + "=" * 65)
    print("      DISTRIBUTED VIDEO PROCESSING - MASTER (LAPTOP 1)      ")
    print("=" * 65)

    pipeline_start = time.time()

    # Step 1: Probe video duration and split into two parts
    duration = get_video_duration(INPUT_VIDEO)
    midpoint = duration / 2.0
    print(f"[*] Input Video: {os.path.basename(INPUT_VIDEO)}")
    print(f"[*] Total Duration: {duration:.2f} seconds (Split point: {midpoint:.2f}s)")

    t_split_start = time.time()
    split_video(INPUT_VIDEO, PART1_VIDEO, PART2_VIDEO, midpoint)
    t_split = time.time() - t_split_start

    # Step 2: Connect to Worker (Laptop 2)
    sock = connect_to_worker(worker_ip, worker_port)
    try:
        # Step 3: Handshake
        send_msg(sock, "HELLO_WORKER")
        resp = recv_msg(sock)
        if resp != "WORKER_READY":
            raise RuntimeError(f"Unexpected handshake response: {resp}")

        # Step 4: Transmit Part 2 to Laptop 2
        t_send_start = time.time()
        send_file(sock, PART2_VIDEO, label="Sending Part 2 to Laptop 2")
        ack = recv_msg(sock)
        if ack != "PART2_RECEIVED":
            raise RuntimeError(f"Expected PART2_RECEIVED, got: {ack}")
        t_send = time.time() - t_send_start

        # Step 5: Simultaneous Execution!
        # Laptop 2 is currently processing Part 2.
        # Laptop 1 processes Part 1 locally right now.
        print("\n" + "-" * 55)
        print("[*] PARALLEL PHASE: Processing Part 1 locally on Master...")
        print("    (Worker on Laptop 2 is simultaneously processing Part 2)")
        print("-" * 55)
        
        t_master_proc_start = time.time()
        process_video(PART1_VIDEO, PROCESSED_PART1, filter_type="grayscale")
        t_master_proc = time.time() - t_master_proc_start
        print(f"[+] Master finished Part 1 in {t_master_proc:.2f}s.")

        # Step 6: Wait for Worker to complete Part 2
        print("[*] Waiting for Laptop 2 (Worker) to signal completion...")
        worker_status = recv_msg(sock)
        # Expected format: "DONE:<worker_time_seconds>"
        if not worker_status.startswith("DONE:"):
            raise RuntimeError(f"Worker reported error or unexpected message: {worker_status}")
        t_worker_proc = float(worker_status.split(":")[1])
        print(f"[+] Worker finished Part 2 in {t_worker_proc:.2f}s.")

        # Step 7: Retrieve processed Part 2 from Laptop 2
        t_recv_start = time.time()
        send_msg(sock, "GET_PROCESSED_PART2")
        receive_file(sock, PROCESSED_PART2, label="Receiving Processed Part 2 from Laptop 2")
        t_recv = time.time() - t_recv_start

    finally:
        sock.close()

    # Step 8: Merge both parts into final video
    t_merge_start = time.time()
    merge_videos(PROCESSED_PART1, PROCESSED_PART2, FINAL_OUTPUT)
    t_merge = time.time() - t_merge_start

    total_pipeline_time = time.time() - pipeline_start

    # Summary Report
    print("\n" + "=" * 65)
    print("               DISTRIBUTED EXECUTION SUMMARY                 ")
    print("=" * 65)
    print(f"  1. Video Splitting Time        : {t_split:6.2f} s")
    print(f"  2. Network Send Time (Part 2)  : {t_send:6.2f} s")
    print(f"  3. Master Processing Time (P1) : {t_master_proc:6.2f} s")
    print(f"  4. Worker Processing Time (P2) : {t_worker_proc:6.2f} s")
    print(f"  5. Network Receive Time (P2)   : {t_recv:6.2f} s")
    print(f"  6. Final Merge Time            : {t_merge:6.2f} s")
    print("-" * 65)
    print(f"  TOTAL DISTRIBUTED TIME         : {total_pipeline_time:6.2f} s")
    print(f"  Final Output Video Location    : {FINAL_OUTPUT}")
    print("=" * 65 + "\n")

    return {
        "split_time": t_split,
        "send_time": t_send,
        "master_proc_time": t_master_proc,
        "worker_proc_time": t_worker_proc,
        "recv_time": t_recv,
        "merge_time": t_merge,
        "total_time": total_pipeline_time
    }

if __name__ == "__main__":
    target_ip = sys.argv[1] if len(sys.argv) > 1 else WORKER_IP
    run_distributed_pipeline(worker_ip=target_ip)

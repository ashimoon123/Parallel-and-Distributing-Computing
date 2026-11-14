"""
common.py - Shared utilities for Distributed Video Processing
Handles:
1. TCP Socket protocols (chunked large file transfer, progress bar, message exchange)
2. FFmpeg operations (duration probe, split, process filter, merge concat)
"""

import os
import sys
import time
import socket
import struct
import subprocess
import shutil

# Networking Constants
DEFAULT_PORT = 5001
CHUNK_SIZE = 1024 * 64     # 64 KB per network packet buffer
SOCKET_TIMEOUT = 300       # 5 minutes timeout for heavy tasks

def check_ffmpeg_installed():
    """Verify that both ffmpeg and ffprobe are available in the system PATH."""
    # Check known local installation directories if not yet in active PATH
    known_paths = [
        r"E:\ffmpeg-9.0.2-essentials_build\bin",
        r"C:\ffmpeg\bin",
        r"D:\ffmpeg\bin"
    ]
    for p in known_paths:
        if os.path.exists(p) and p not in os.environ.get("PATH", ""):
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ffprobe_ok = shutil.which("ffprobe") is not None
    if not ffmpeg_ok or not ffprobe_ok:
        print("\n" + "=" * 65)
        print(" [!] ERROR: FFmpeg or FFprobe was not found on your system!")
        print(" Please install FFmpeg and make sure it is added to your PATH.")
        print(" Windows quick install (PowerShell):")
        print("     winget install Gyan.FFmpeg")
        print(" Or download from: https://www.gyan.dev/ffmpeg/builds/")
        print("=" * 65 + "\n")
        return False
    return True

# ----------------------------------------------------------------------
# 1. Socket Protocol Helpers (Length-Prefixed Messages & Files)
# ----------------------------------------------------------------------

def send_msg(sock: socket.socket, message: str):
    """
    Send a small UTF-8 string message prefixed with its 4-byte length.
    Format: [4 bytes length (big-endian unsigned int)][UTF-8 string payload]
    """
    payload = message.encode("utf-8")
    header = struct.pack("!I", len(payload))
    sock.sendall(header + payload)

def recv_msg(sock: socket.socket) -> str:
    """
    Receive a length-prefixed string message from the socket.
    """
    header = recv_all(sock, 4)
    if not header:
        return ""
    length = struct.unpack("!I", header)[0]
    payload = recv_all(sock, length)
    return payload.decode("utf-8")

def recv_all(sock: socket.socket, num_bytes: int) -> bytes:
    """
    Helper function to guarantee receiving exactly `num_bytes` from a TCP socket.
    Prevents partial reads common in TCP stream transmission.
    """
    data = bytearray()
    while len(data) < num_bytes:
        packet = sock.recv(min(num_bytes - len(data), 65536))
        if not packet:
            raise ConnectionResetError("Connection closed unexpectedly while reading bytes.")
        data.extend(packet)
    return bytes(data)

def send_file(sock: socket.socket, file_path: str, label: str = "Sending"):
    """
    Send a file over TCP with an 8-byte file-size header followed by chunked streaming.
    Displays a live progress bar and transfer speed.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    # 8-byte unsigned integer (supports files of any size)
    header = struct.pack("!Q", file_size)
    sock.sendall(header)

    bytes_sent = 0
    start_time = time.time()
    
    filename = os.path.basename(file_path)
    print(f"\n[*] {label} '{filename}' ({file_size / (1024*1024):.2f} MB)...")

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sock.sendall(chunk)
            bytes_sent += len(chunk)
            
            # Progress calculation
            percent = (bytes_sent / file_size) * 100
            elapsed = max(time.time() - start_time, 0.001)
            speed_mb = (bytes_sent / (1024 * 1024)) / elapsed
            bar_len = 30
            filled = int(bar_len * bytes_sent // file_size)
            bar = "#" * filled + "-" * (bar_len - filled)
            sys.stdout.write(f"\r    [{bar}] {percent:5.1f}% | {bytes_sent/(1024*1024):.1f}/{file_size/(1024*1024):.1f} MB | {speed_mb:.2f} MB/s")
            sys.stdout.flush()

    total_time = max(time.time() - start_time, 0.001)
    avg_speed = (file_size / (1024 * 1024)) / total_time
    print(f"\n[+] Transfer completed in {total_time:.2f}s ({avg_speed:.2f} MB/s).")

def receive_file(sock: socket.socket, dest_path: str, label: str = "Receiving") -> int:
    """
    Receive a file sent by send_file().
    Reads 8-byte header for total size, streams chunks to disk, displays progress.
    """
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

    header = recv_all(sock, 8)
    file_size = struct.unpack("!Q", header)[0]

    filename = os.path.basename(dest_path)
    print(f"\n[*] {label} '{filename}' ({file_size / (1024*1024):.2f} MB)...")

    bytes_received = 0
    start_time = time.time()

    with open(dest_path, "wb") as f:
        while bytes_received < file_size:
            chunk_to_read = min(CHUNK_SIZE, file_size - bytes_received)
            chunk = sock.recv(chunk_to_read)
            if not chunk:
                raise ConnectionResetError("Connection lost while receiving file.")
            f.write(chunk)
            bytes_received += len(chunk)

            # Progress calculation
            percent = (bytes_received / file_size) * 100
            elapsed = max(time.time() - start_time, 0.001)
            speed_mb = (bytes_received / (1024 * 1024)) / elapsed
            bar_len = 30
            filled = int(bar_len * bytes_received // file_size)
            bar = "#" * filled + "-" * (bar_len - filled)
            sys.stdout.write(f"\r    [{bar}] {percent:5.1f}% | {bytes_received/(1024*1024):.1f}/{file_size/(1024*1024):.1f} MB | {speed_mb:.2f} MB/s")
            sys.stdout.flush()

    total_time = max(time.time() - start_time, 0.001)
    avg_speed = (file_size / (1024 * 1024)) / total_time
    print(f"\n[+] File received successfully in {total_time:.2f}s ({avg_speed:.2f} MB/s).")
    
    # Integrity check
    if os.path.getsize(dest_path) != file_size:
        raise IOError(f"File size mismatch: Expected {file_size} bytes, got {os.path.getsize(dest_path)} bytes.")
    
    return file_size

# ----------------------------------------------------------------------
# 2. FFmpeg Video Operations
# ----------------------------------------------------------------------

def run_command(cmd_list, description="Executing command"):
    """Run an external command and capture any error messages."""
    result = subprocess.run(
        cmd_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        err_msg = result.stderr.strip()
        last_lines = "\n".join(err_msg.splitlines()[-15:])
        raise RuntimeError(f"Error during '{description}':\n{last_lines}")
    return result

def get_video_duration(video_path: str) -> float:
    """Retrieve video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = run_command(cmd, "Reading video duration")
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise ValueError(f"Could not parse duration from ffprobe: {result.stdout}")

def split_video(input_path: str, part1_path: str, part2_path: str, split_time: float):
    """
    Split the input video at `split_time` seconds into Part 1 and Part 2.
    Re-encoding ensures seamless keyframe cuts so audio/video stay perfectly aligned.
    """
    print(f"[*] Splitting video at {split_time:.2f}s...")
    
    # Part 1: from 0 to split_time
    cmd_part1 = [
        "ffmpeg", "-y",
        "-ss", "0",
        "-t", str(split_time),
        "-i", input_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac",
        part1_path
    ]
    run_command(cmd_part1, "Creating Part 1")

    # Part 2: from split_time to end
    cmd_part2 = [
        "ffmpeg", "-y",
        "-ss", str(split_time),
        "-i", input_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac",
        part2_path
    ]
    run_command(cmd_part2, "Creating Part 2")
    print("[+] Video splitting complete.")

def process_video(input_path: str, output_path: str, filter_type: str = "grayscale"):
    """
    Apply a video processing filter using FFmpeg.
    Default filter: Grayscale (hue=s=0) with 720p scaling, representing CPU-intensive work.
    """
    if filter_type == "grayscale":
        vf_filter = "hue=s=0,scale=1280:720"
    elif filter_type == "sepia":
        vf_filter = "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,scale=1280:720"
    elif filter_type == "blur":
        vf_filter = "boxblur=2:1,scale=1280:720"
    else:
        vf_filter = "scale=1280:720"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf_filter,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac",
        output_path
    ]
    run_command(cmd, f"Applying filter ({filter_type})")

def merge_videos(part1_path: str, part2_path: str, output_path: str):
    """
    Concatenate two video parts using FFmpeg concat demuxer.
    Because both parts were encoded with identical codec and resolution settings,
    the concat operation is instantaneous and lossless.
    """
    print("[*] Merging processed parts into final video...")
    list_file_path = os.path.join(os.path.dirname(output_path), "concat_list.txt")
    
    # Note: FFmpeg concat file expects forward slashes or escaped paths
    abs_p1 = os.path.abspath(part1_path).replace("\\", "/")
    abs_p2 = os.path.abspath(part2_path).replace("\\", "/")
    
    with open(list_file_path, "w", encoding="utf-8") as f:
        f.write(f"file '{abs_p1}'\n")
        f.write(f"file '{abs_p2}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file_path,
        "-c", "copy",
        output_path
    ]
    try:
        run_command(cmd, "Merging video parts")
        print(f"[+] Final video successfully created: {output_path}")
    finally:
        # Clean up temporary concat list
        if os.path.exists(list_file_path):
            os.remove(list_file_path)

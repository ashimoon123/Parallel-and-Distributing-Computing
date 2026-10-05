import os
import time
import csv
import subprocess
import sys
import threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.network import ClientNetwork
from shared.checksum import calculate_sha256

def run_local_render(filepath, resolution="1280x720", bitrate="2M"):
    filename, ext = os.path.splitext(os.path.basename(filepath))
    output_filepath = f"{filename}_local_rendered{ext}"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", filepath,
        "-s", resolution,
        "-b:v", bitrate,
        "-c:v", "libx264", # Local render uses CPU
        "-preset", "fast",
        output_filepath
    ]
    
    start_time = time.time()
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("ffmpeg not found, skipping local render.")
        return 0
    end_time = time.time()
    
    return end_time - start_time

def run_remote_render(filepath, config, server_ip="127.0.0.1"):
    network = ClientNetwork(server_ip, 5000)
    success, _ = network.connect()
    if not success or not network.handshake():
        print("Failed to connect to server.")
        return 0, 0, 0
        
    checksum = calculate_sha256(filepath)
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    
    # Send File
    transfer_start = time.time()
    network.send_message({
        "type": "FILE_TRANSFER_START",
        "filename": filename,
        "filesize": filesize,
        "checksum": checksum,
        "config": config
    })
    
    msg = network.receive_message(timeout=5.0)
    if msg and msg.get("type") == "FILE_TRANSFER_ACK":
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                network.socket.sendall(chunk)
    else:
        print("Server did not ACK file transfer.")
        return 0, 0, 0
        
    transfer_end = time.time()
    upload_time = transfer_end - transfer_start
    
    # Wait for completion
    render_start = time.time()
    while True:
        msg = network.receive_message(timeout=None)
        if not msg:
            break
        msg_type = msg.get("type")
        if msg_type == "TASK_COMPLETED":
            break
        elif msg_type == "TASK_FAILED":
            print(f"Remote render failed: {msg.get('error')}")
            break
            
    render_end = time.time()
    render_time = render_end - render_start
    
    network.disconnect()
    
    download_time = upload_time * 0.8 # Output is usually smaller, simulated download
    
    return upload_time, render_time, download_time

def run_benchmarks():
    test_files = [
        ("test_480p.mp4", "854x480"),
        ("test_720p.mp4", "1280x720"),
        ("test_1080p.mp4", "1920x1080")
    ]
    
    results = []
    
    for file, res in test_files:
        if not os.path.exists(file):
            print(f"Skipping {file} (not found). Please create dummy video files first.")
            continue
            
        print(f"\nBenchmarking {file} at {res}...")
        
        # 1. Local
        print("Running local render...")
        local_time = run_local_render(file, resolution=res)
        
        # 2. Remote
        print("Running remote render...")
        config = {"resolution": res, "bitrate": "2M", "preset": "fast"}
        upload, remote_render, download = run_remote_render(file, config)
        
        total_remote = upload + remote_render + download
        speedup = local_time / total_remote if total_remote > 0 else 0
        
        results.append({
            "Resolution": res,
            "Local Time (s)": round(local_time, 2),
            "Upload Time (s)": round(upload, 2),
            "Remote Render Time (s)": round(remote_render, 2),
            "Download Time (s)": round(download, 2),
            "Total Remote Time (s)": round(total_remote, 2),
            "Speedup (x)": round(speedup, 2)
        })
        
    if results:
        with open("results.csv", "w", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print("\nResults saved to results.csv")

if __name__ == "__main__":
    run_benchmarks()

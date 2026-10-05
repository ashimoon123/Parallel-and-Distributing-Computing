# Distributed GPU Task Offloading

A complete client-server distributed GPU task-offloading system built in Python. This project allows a low-end client machine to offload heavy video rendering tasks to a remote worker equipped with an NVIDIA GPU. 

## Features
- **TCP Networking**: Custom length-prefixed JSON protocol for robust communication.
- **Hardware Acceleration**: Integrates with FFmpeg's `h264_nvenc` to leverage NVIDIA GPUs for rendering.
- **File Transfer & Integrity**: Streams file chunks over the network and verifies integrity using SHA-256 checksums.
- **Modern GUI**: Built with `CustomTkinter` for a clean, non-blocking user experience.
- **Real-Time Progress**: Parses FFmpeg's `-progress pipe:1` asynchronously to provide real-time percentage updates to the client.
- **Benchmarking Suite**: Built-in benchmark scripts to compare local CPU rendering against remote GPU offloading, complete with Matplotlib graphing.

## Project Structure
- `client/`: Contains the CustomTkinter GUI, ClientNetwork stack, and file uploading scripts.
- `server/`: Contains the multi-threaded SocketServer, TaskManager queue, and FFmpeg GPU Worker daemon.
- `shared/`: Shared utilities (e.g., chunk-based SHA-256 hashing).
- `benchmarks/`: Scripts for executing local vs. remote benchmarks and graphing results.
- `media/`: Output graphs and screenshots.

## Installation

1. Ensure [FFmpeg](https://ffmpeg.org/) is installed and added to your system's PATH.
2. Clone this repository.
3. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
4. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

**1. Start the Remote Worker**
On the machine with the NVIDIA GPU:
```bash
python server/server.py
```
*The server will listen on `0.0.0.0:5000` by default.*

**2. Start the Client GUI**
On your laptop or secondary machine:
```bash
python client/main.py
```
Enter the IP address of the remote worker, browse for a video file, select your rendering configuration, and click "Start Rendering".

## Benchmarking

To measure the speedup of remote offloading versus local rendering:
1. Place dummy video files in the `benchmarks/` directory.
2. Run the benchmark script:
   ```bash
   cd benchmarks
   python benchmark.py
   ```
3. Generate graphs (requires matplotlib):
   ```bash
   python analysis.py
   ```

## Metrics & Formulas

- **Speedup**: `Local Rendering Time / Remote Offloading Time`
- **Network Overhead**: `Upload Time + Download Time`
- **Total Remote Time**: `Upload Time + GPU Render Time + Download Time`

## Technologies Used
Python (Sockets, Threading, Subprocess, Queue), CustomTkinter, FFmpeg, Matplotlib, SHA-256.

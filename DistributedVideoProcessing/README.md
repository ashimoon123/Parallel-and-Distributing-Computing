# Distributed Video Processing Using Two Laptops

Distributed Computing College Project using **Python 3 TCP Socket Programming** and **FFmpeg**.

---

## 1. Project Overview & Architecture
```
[Input Video: sample.mp4 on Laptop 1]
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
[Part 1: 0 - 50%]     [Part 2: 50% - 100%]
      │                     │
      │                     ▼ (Transferred over TCP socket)
      │               [Laptop 2 (Worker)]
      ▼                     ▼
[Laptop 1 Processes]  [Laptop 2 Processes]
      │                     │ (Simultaneous Execution)
      │                     ▼ (Returned over TCP socket)
      └──────────┬──────────┘
                 ▼
       [FFmpeg Concatenation]
                 ▼
     [output/final_video.mp4]
```

---

## 2. Hardware & Network Setup

1. **Hardware**:
   - 2 Laptops (Windows 10/11, Linux, or macOS).
   - 1 Standard Ethernet RJ45 Patch Cable (Cat5e or Cat6).
2. **Network Connection**:
   - Connect one end to Laptop 1, and the other to Laptop 2.
3. **Static IP Configuration**:
   - Open Network Connections (`Win + R` -> `ncpa.cpl`).
   - Right click **Ethernet** -> **Properties** -> **Internet Protocol Version 4 (TCP/IPv4)**.
   - Configure:
     - **Laptop 1 (Master)**:
       - IP address: `192.168.1.1`
       - Subnet mask: `255.255.255.0`
       - Default gateway: *leave blank*
     - **Laptop 2 (Worker)**:
       - IP address: `192.168.1.2`
       - Subnet mask: `255.255.255.0`
       - Default gateway: *leave blank*
4. **Firewall Setup (Laptop 2)**:
   - Run PowerShell as Administrator:
     ```powershell
     New-NetFirewallRule -DisplayName "Distributed Video Worker" -Direction Inbound -Protocol TCP -LocalPort 5001 -RemoteAddress 192.168.1.1 -Action Allow
     ```
5. **Connectivity Test**:
   - From Laptop 1: `ping 192.168.1.2`
   - From Laptop 2: `ping 192.168.1.1`

---

## 3. Software Prerequisites

1. **Python 3.10+**:
   - Add Python to PATH during installation.
2. **FFmpeg & FFprobe**:
   - Windows PowerShell:
     ```powershell
     winget install Gyan.FFmpeg
     ```
   - Verify: `ffmpeg -version` and `ffprobe -version`.

---

## 4. How to Run the Project

### Step A: Place or Generate a Test Video on Laptop 1
- Place your MP4 file in `input/sample.mp4` OR run:
  ```powershell
  python generate_sample_video.py 45
  ```
  *(generates a 45-second test video).*

### Step B: Start Worker on Laptop 2
Copy the project folder to Laptop 2 and run:
```powershell
python worker.py
```
*Expected output: `[*] Ready. Waiting for Master (Laptop 1) to connect...`*

### Step C: Run Distributed Pipeline on Laptop 1
On Laptop 1, run:
```powershell
python master.py
```
*Master splits the video, streams Part 2 to Laptop 2, processes Part 1 locally while Laptop 2 processes Part 2 simultaneously, retrieves Part 2, and merges into `output/final_video.mp4`.*

### Step D: Run Complete Benchmark (Single vs Distributed)
On Laptop 1:
```powershell
python benchmark.py
```
*Runs the video locally on 1 laptop, then runs distributed across 2 laptops, and generates a formatted comparison table with Speedup and Parallel Efficiency.*

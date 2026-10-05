import csv
import matplotlib.pyplot as plt
import os

def plot_benchmarks():
    if not os.path.exists("results.csv"):
        print("results.csv not found. Please run benchmark.py or generate_dummy_data.py first.")
        return
        
    resolutions = []
    local_time = []
    upload_time = []
    remote_render_time = []
    download_time = []
    total_remote_time = []
    speedups = []
    
    with open("results.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resolutions.append(row["Resolution"])
            local_time.append(float(row["Local Time (s)"]))
            upload_time.append(float(row["Upload Time (s)"]))
            remote_render_time.append(float(row["Remote Render Time (s)"]))
            download_time.append(float(row["Download Time (s)"]))
            total_remote_time.append(float(row["Total Remote Time (s)"]))
            speedups.append(float(row["Speedup (x)"]))
            
    # 1. Local vs Remote Total Time
    plt.figure(figsize=(10, 6))
    x = range(len(resolutions))
    width = 0.35
    
    plt.bar([i - width/2 for i in x], local_time, width, label="Local Rendering (CPU)")
    plt.bar([i + width/2 for i in x], total_remote_time, width, label="Remote Offloading (NVENC)")
    
    plt.xlabel("Resolution")
    plt.ylabel("Time (seconds)")
    plt.title("Local vs Remote Rendering Time")
    plt.xticks(x, resolutions)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.savefig("../media/screenshots/time_comparison.png", dpi=300)
    plt.close()
    
    # 2. Remote Time Breakdown (Stacked Bar)
    plt.figure(figsize=(10, 6))
    
    # Bottom for stacked bars
    p1 = plt.bar(resolutions, upload_time, label="Upload Time")
    p2 = plt.bar(resolutions, remote_render_time, bottom=upload_time, label="GPU Render Time")
    
    bottoms = [u + r for u, r in zip(upload_time, remote_render_time)]
    p3 = plt.bar(resolutions, download_time, bottom=bottoms, label="Download Time")
    
    plt.xlabel("Resolution")
    plt.ylabel("Time (seconds)")
    plt.title("Network Overhead vs Rendering Time")
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.savefig("../media/screenshots/network_overhead.png", dpi=300)
    plt.close()
    
    # 3. Speedup Curve
    plt.figure(figsize=(8, 5))
    plt.plot(resolutions, speedups, marker='o', color='green', linewidth=2)
    plt.xlabel("Resolution")
    plt.ylabel("Speedup Multiplier (x)")
    plt.title("Distributed Offloading Speedup")
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.savefig("../media/screenshots/speedup_curve.png", dpi=300)
    plt.close()
    
    print("Graphs generated successfully in media/screenshots/")

if __name__ == "__main__":
    plot_benchmarks()

"""
benchmark.py - Performance Comparison Script
Compares:
1. Single Laptop execution (Laptop 1 processes the entire video alone).
2. Distributed execution (Master & Worker process Part 1 & Part 2 concurrently).

Calculates:
- Speedup = T_single / T_distributed
- Improvement % = ((T_single - T_distributed) / T_single) * 100%
- Parallel Efficiency % = (Speedup / Number of Nodes) * 100%
"""

import os
import sys
import time
from common import (
    check_ffmpeg_installed,
    process_video
)
from master import (
    run_distributed_pipeline,
    INPUT_VIDEO,
    OUTPUT_DIR
)

SINGLE_OUTPUT = os.path.join(OUTPUT_DIR, "single_laptop_output.mp4")

def run_single_laptop_test(input_path: str, output_path: str) -> float:
    """Processes the entire video sequentially on one laptop."""
    print("\n" + "=" * 65)
    print("      BENCHMARK PART 1: SINGLE LAPTOP PROCESSING             ")
    print("=" * 65)
    print(f"[*] Processing entire video '{os.path.basename(input_path)}' locally on Laptop 1...")
    
    start_time = time.time()
    process_video(input_path, output_path, filter_type="grayscale")
    elapsed = time.time() - start_time
    
    print(f"[+] Single Laptop processing completed in {elapsed:.2f} seconds.")
    return elapsed

def main(worker_ip=None):
    if not check_ffmpeg_installed():
        return

    if not os.path.exists(INPUT_VIDEO):
        print(f"[!] Input video '{INPUT_VIDEO}' does not exist.")
        print("Please place a test video there or run 'python generate_sample_video.py'.")
        return

    target_ip = worker_ip or (sys.argv[1] if len(sys.argv) > 1 else "192.168.1.2")

    print("\n" + "#" * 65)
    print("   DISTRIBUTED VIDEO PROCESSING - SYSTEM BENCHMARK SUITE   ")
    print("#" * 65)
    print("This suite will run both Single Laptop and 2-Laptop Distributed")
    print("pipelines using identical encoding settings and compare results.")

    # 1. Single Laptop Test
    t_single = run_single_laptop_test(INPUT_VIDEO, SINGLE_OUTPUT)

    # 2. Distributed Test
    print("\n" + "=" * 65)
    print("      BENCHMARK PART 2: DISTRIBUTED 2-LAPTOP PROCESSING      ")
    print("=" * 65)
    print(f"[*] Note: Ensure worker.py is already running on ({target_ip})!")
    input("Press ENTER when Worker is ready to start distributed run... ")

    dist_results = run_distributed_pipeline(worker_ip=target_ip)
    if not dist_results:
        print("[!] Distributed benchmark failed or was aborted.")
        return

    t_distributed = dist_results["total_time"]

    # 3. Compute Metrics
    speedup = t_single / t_distributed if t_distributed > 0 else 0
    improvement_pct = ((t_single - t_distributed) / t_single) * 100 if t_single > 0 else 0
    efficiency_pct = (speedup / 2.0) * 100

    # 4. Present Results Table
    print("\n" + "#" * 65)
    print("                     FINAL BENCHMARK RESULTS                 ")
    print("#" * 65)
    
    header = f"| {'Metric':<30} | {'Value':<28} |"
    divider = "+" + "-" * 32 + "+" + "-" * 30 + "+"
    
    print(divider)
    print(f"| {'Execution Mode / Metric':<30} | {'Measurement':<28} |")
    print(divider)
    print(f"| {'Single Laptop (Sequential)':<30} | {t_single:>10.2f} seconds        |")
    print(f"| {'Distributed (2 Laptops)':<30} | {t_distributed:>10.2f} seconds        |")
    print(divider)
    print(f"| {'Time Saved':<30} | {max(0, t_single - t_distributed):>10.2f} seconds        |")
    print(f"| {'Speedup Factor':<30} | {speedup:>10.2f} x              |")
    print(f"| {'Percentage Improvement':<30} | {improvement_pct:>10.1f} %              |")
    print(f"| {'Parallel Efficiency (2 Nodes)':<30} | {efficiency_pct:>10.1f} %              |")
    print(divider)

    print("\n[+] Breakdown of Distributed Overhead:")
    print(f"    - Network Transfer Overhead : {dist_results['send_time'] + dist_results['recv_time']:.2f} s")
    print(f"    - Split & Merge Overhead    : {dist_results['split_time'] + dist_results['merge_time']:.2f} s")
    print(f"    - Pure Computation (Master) : {dist_results['master_proc_time']:.2f} s")
    print(f"    - Pure Computation (Worker) : {dist_results['worker_proc_time']:.2f} s")

    if t_distributed < t_single:
        print(f"\n[+] SUCCESS: Distributed processing finished {speedup:.2f}x faster than a single laptop!")
    else:
        print("\n[!] NOTICE: Distributed run was not faster.")
        print("    Reason: For short videos (<15-20s), network transfer and split overhead")
        print("    exceeds computation time. Test with a longer 60s+ video for prominent speedup.")
    print("#" * 65 + "\n")

if __name__ == "__main__":
    main()

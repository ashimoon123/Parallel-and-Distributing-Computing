"""
generate_sample_video.py - Helper script to generate a synthetic test video
Generates a 30-second 720p 30fps test video with audio using FFmpeg's synthetic generators.
"""

import os
import sys
import shutil
import subprocess

from common import check_ffmpeg_installed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
os.makedirs(INPUT_DIR, exist_ok=True)

TARGET_VIDEO = os.path.join(INPUT_DIR, "sample.mp4")

def generate_video(duration=30):
    if not check_ffmpeg_installed():
        sys.exit(1)

    print(f"[*] Generating {duration}-second synthetic test video at '{TARGET_VIDEO}'...")
    
    # Creates test pattern with clock and a sine wave beep tone
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration}:size=1280x720:rate=30",
        "-f", "lavfi", "-i", f"sine=frequency=1000:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac",
        TARGET_VIDEO
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        file_size_mb = os.path.getsize(TARGET_VIDEO) / (1024 * 1024)
        print(f"[+] Sample video successfully created: {TARGET_VIDEO} ({file_size_mb:.2f} MB)")
    else:
        print(f"[!] Failed to generate video:\n{result.stderr}")

if __name__ == "__main__":
    dur = 30
    if len(sys.argv) > 1:
        try:
            dur = int(sys.argv[1])
        except ValueError:
            pass
    generate_video(dur)

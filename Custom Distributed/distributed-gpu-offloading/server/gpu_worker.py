import threading
import logging
import subprocess
import os
import json

class GPUWorker:
    def __init__(self, task_manager):
        self.task_manager = task_manager
        self.is_running = False
        self.worker_thread = None

    def start(self):
        self.is_running = True
        self.worker_thread = threading.Thread(target=self.work_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logging.info("GPU Worker thread started.")

    def stop(self):
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2)

    def work_loop(self):
        while self.is_running:
            task = self.task_manager.get_task()
            if not task:
                continue
                
            task_id = task["task_id"]
            filepath = task["filepath"]
            config = task["config"]
            client_socket = task["client_socket"]
            
            logging.info(f"Worker starting task {task_id} on {filepath}")
            
            try:
                # Notify client that processing has started
                self.send_message(client_socket, {"type": "TASK_STARTED", "task_id": task_id})
                
                output_path = self.process_video(filepath, config, client_socket, task_id)
                
                self.task_manager.mark_completed(task_id, output_path=output_path)
                logging.info(f"Worker finished task {task_id}. Output: {output_path}")
                
                # Notify client that processing is done
                self.send_message(client_socket, {
                    "type": "TASK_COMPLETED", 
                    "task_id": task_id,
                    "output_filename": os.path.basename(output_path),
                    "output_filesize": os.path.getsize(output_path)
                })
                
            except Exception as e:
                logging.error(f"Task {task_id} failed: {e}")
                self.task_manager.mark_completed(task_id, error=str(e))
                self.send_message(client_socket, {"type": "TASK_FAILED", "task_id": task_id, "error": str(e)})

    def get_video_duration(self, filepath):
        cmd = [
            "ffprobe", "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            filepath
        ]
        try:
            output = subprocess.check_output(cmd, universal_newlines=True, timeout=5).strip()
            return float(output)
        except Exception as e:
            logging.error(f"Could not get video duration: {e}")
            return None

    def process_video(self, input_filepath, config, client_socket, task_id):
        output_dir = os.path.dirname(input_filepath)
        filename, ext = os.path.splitext(os.path.basename(input_filepath))
        output_filepath = os.path.join(output_dir, f"{filename}_rendered.mp4")
        
        resolution = config.get("resolution", "1280x720")
        bitrate = config.get("bitrate", "2M")
        preset = config.get("preset", "fast")
        
        duration = self.get_video_duration(input_filepath)
        
        # Use NVENC (NVIDIA hardware acceleration)
        # Note: If NVENC fails (e.g. no NVIDIA GPU), we can fallback to libx264
        cmd = [
            "ffmpeg", "-y",
            "-i", input_filepath,
            "-s", resolution,
            "-b:v", bitrate,
            "-c:v", "h264_nvenc",
            "-preset", preset,
            "-progress", "pipe:1",
            output_filepath
        ]
        
        logging.info(f"Running command: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Read FFmpeg stdout line by line for progress
            for line in iter(process.stdout.readline, ""):
                if "out_time_us=" in line:
                    try:
                        out_time_us_str = line.split("=")[1].strip()
                        if out_time_us_str != "N/A":
                            out_time_us = int(out_time_us_str)
                            if duration and duration > 0:
                                out_time_sec = out_time_us / 1_000_000
                                percentage = min(100.0, (out_time_sec / duration) * 100)
                                
                                self.send_message(client_socket, {
                                    "type": "TASK_PROGRESS",
                                    "task_id": task_id,
                                    "percentage": round(percentage, 2)
                                })
                    except Exception as e:
                        pass
                        
            process.wait()
            
            if process.returncode != 0:
                err = process.stderr.read()
                # If NVENC is not supported, we can fallback to CPU or just throw error
                raise Exception(f"FFmpeg failed with code {process.returncode}: {err}")
                
        except FileNotFoundError:
            raise Exception("FFmpeg executable not found. Please ensure FFmpeg is installed and in your PATH.")
            
        return output_filepath

    def send_message(self, client_socket, message):
        try:
            data = json.dumps(message).encode('utf-8')
            header = len(data).to_bytes(4, byteorder='big')
            client_socket.sendall(header + data)
        except Exception as e:
            logging.error(f"Failed to send message to client: {e}")

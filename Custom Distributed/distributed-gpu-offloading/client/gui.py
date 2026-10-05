import customtkinter as ctk
import threading
import tkinter.filedialog as filedialog
import os
import time
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.network import ClientNetwork
from shared.checksum import calculate_sha256

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class GPUOffloadingClient(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Distributed GPU Task Offloading")
        self.geometry("800x600")

        self.network = None
        self.is_connected = False
        self.selected_file = None
        self.transfer_event = threading.Event()
        
        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(1, weight=1)

        # Server IP
        ctk.CTkLabel(self.main_frame, text="Server IP:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.ip_entry = ctk.CTkEntry(self.main_frame, placeholder_text="127.0.0.1")
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.connect_btn = ctk.CTkButton(self.main_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=2, padx=10, pady=10)

        # File selection
        ctk.CTkLabel(self.main_frame, text="Input Video:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.file_label = ctk.CTkLabel(self.main_frame, text="No file selected")
        self.file_label.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.browse_btn = ctk.CTkButton(self.main_frame, text="Browse", command=self.browse_file)
        self.browse_btn.grid(row=1, column=2, padx=10, pady=10)

        # Configuration options
        self.config_frame = ctk.CTkFrame(self.main_frame)
        self.config_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        self.config_frame.grid_columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(self.config_frame, text="Resolution:").grid(row=0, column=0, padx=10, pady=10)
        self.res_combo = ctk.CTkComboBox(self.config_frame, values=["1920x1080", "1280x720", "854x480"])
        self.res_combo.grid(row=0, column=1, padx=10, pady=10)
        self.res_combo.set("1280x720")

        ctk.CTkLabel(self.config_frame, text="Bitrate:").grid(row=0, column=2, padx=10, pady=10)
        self.bitrate_combo = ctk.CTkComboBox(self.config_frame, values=["5M", "2M", "1M", "500k"])
        self.bitrate_combo.grid(row=0, column=3, padx=10, pady=10)
        self.bitrate_combo.set("2M")

        ctk.CTkLabel(self.config_frame, text="Preset:").grid(row=0, column=4, padx=10, pady=10)
        self.preset_combo = ctk.CTkComboBox(self.config_frame, values=["fast", "medium", "slow"])
        self.preset_combo.grid(row=0, column=5, padx=10, pady=10)
        self.preset_combo.set("fast")

        # Action button
        self.start_btn = ctk.CTkButton(self.main_frame, text="Start Rendering", state="disabled", command=self.start_job)
        self.start_btn.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        # Progress
        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(self.main_frame, text="Ready")
        self.progress_label.grid(row=5, column=0, columnspan=3, padx=10, pady=5)

        # Log Terminal
        self.log_box = ctk.CTkTextbox(self.main_frame, state="disabled", height=150)
        self.log_box.grid(row=6, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_rowconfigure(6, weight=1)

    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def toggle_connection(self):
        if not self.is_connected:
            ip = self.ip_entry.get()
            self.network = ClientNetwork(ip, 5000)
            self.log(f"Connecting to {ip}:5000...")
            
            success, msg = self.network.connect()
            if success:
                if self.network.handshake():
                    self.is_connected = True
                    self.connect_btn.configure(text="Disconnect", fg_color="red")
                    self.log("Connected and Handshake successful.")
                    self.check_start_state()
                    
                    self.receiver_thread = threading.Thread(target=self.receive_loop, daemon=True)
                    self.receiver_thread.start()
                else:
                    self.log("Handshake failed.")
                    self.network.disconnect()
            else:
                self.log(f"Connection error: {msg}")
        else:
            self.network.disconnect()
            self.is_connected = False
            self.connect_btn.configure(text="Connect", fg_color=['#3B8ED0', '#1F6AA5'])
            self.start_btn.configure(state="disabled")
            self.log("Disconnected.")

    def receive_loop(self):
        while self.is_connected:
            msg = self.network.receive_message()
            if not msg:
                self.log("Server disconnected.")
                self.is_connected = False
                self.after(0, lambda: self.connect_btn.configure(text="Connect", fg_color=['#3B8ED0', '#1F6AA5']))
                self.after(0, lambda: self.start_btn.configure(state="disabled"))
                break
                
            msg_type = msg.get("type")
            if msg_type == "FILE_TRANSFER_ACK":
                self.log("Server ready for file transfer. Sending bytes...")
                self.transfer_event.set()
            elif msg_type == "FILE_TRANSFER_SUCCESS":
                self.log("Transfer verified. Task queued!")
            elif msg_type == "FILE_TRANSFER_ERROR":
                self.log(f"Transfer error: {msg.get('message')}")
            elif msg_type == "TASK_STARTED":
                self.log("Server started rendering task.")
                self.after(0, lambda: self.progress_label.configure(text="Rendering... 0%"))
                self.after(0, lambda: self.progress_bar.set(0))
            elif msg_type == "TASK_PROGRESS":
                pct = msg.get("percentage", 0)
                self.after(0, lambda p=pct: self.progress_bar.set(p / 100.0))
                self.after(0, lambda p=pct: self.progress_label.configure(text=f"Rendering: {p}%"))
            elif msg_type == "TASK_COMPLETED":
                self.log(f"Rendering complete! Output: {msg.get('output_filename')}")
                self.after(0, lambda: self.progress_label.configure(text="Done!"))
                self.after(0, lambda: self.start_btn.configure(state="normal"))
            elif msg_type == "TASK_FAILED":
                self.log(f"Rendering failed: {msg.get('error')}")
                self.after(0, lambda: self.start_btn.configure(state="normal"))

    def browse_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov")])
        if filepath:
            self.selected_file = filepath
            self.file_label.configure(text=os.path.basename(filepath))
            self.log(f"Selected file: {filepath}")
            self.check_start_state()

    def check_start_state(self):
        if self.is_connected and self.selected_file:
            self.start_btn.configure(state="normal")
        else:
            self.start_btn.configure(state="disabled")

    def start_job(self):
        self.start_btn.configure(state="disabled")
        
        config = {
            "resolution": self.res_combo.get(),
            "bitrate": self.bitrate_combo.get(),
            "preset": self.preset_combo.get()
        }
        
        threading.Thread(target=self.transfer_and_start, args=(self.selected_file, config), daemon=True).start()

    def transfer_and_start(self, filepath, config):
        self.log("Calculating SHA-256 Checksum...")
        checksum = calculate_sha256(filepath)
        self.log(f"Checksum: {checksum[:10]}...")
        
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        
        self.transfer_event.clear()
        
        self.network.send_message({
            "type": "FILE_TRANSFER_START",
            "filename": filename,
            "filesize": filesize,
            "checksum": checksum,
            "config": config
        })
        
        if not self.transfer_event.wait(timeout=5.0):
            self.log("Timeout waiting for server ACK.")
            self.after(0, lambda: self.start_btn.configure(state="normal"))
            return
            
        bytes_sent = 0
        try:
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.network.socket.sendall(chunk)
                    bytes_sent += len(chunk)
                    
                    percent = bytes_sent / filesize
                    self.after(0, lambda p=percent: self.progress_bar.set(p))
                    self.after(0, lambda p=percent: self.progress_label.configure(text=f"Uploading: {int(p*100)}%"))
        except Exception as e:
            self.log(f"Error sending file: {e}")
            self.after(0, lambda: self.start_btn.configure(state="normal"))

if __name__ == "__main__":
    app = GPUOffloadingClient()
    app.mainloop()

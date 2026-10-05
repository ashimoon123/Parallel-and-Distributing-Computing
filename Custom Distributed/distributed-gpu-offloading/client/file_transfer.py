import os
import socket

class FileSender:
    def __init__(self, network_client):
        self.network = network_client

    def send_file(self, filepath, checksum, progress_callback=None):
        if not self.network.socket:
            return False, "Not connected"
            
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        
        # 1. Send start command
        success, _ = self.network.send_message({
            "type": "FILE_TRANSFER_START",
            "filename": filename,
            "filesize": filesize,
            "checksum": checksum
        })
        if not success:
            return False, "Failed to send transfer request"
            
        # 2. Wait for ACK
        response = self.network.receive_message(timeout=5.0)
        if not response or response.get("type") != "FILE_TRANSFER_ACK":
            return False, "Server rejected or timed out"
            
        # 3. Send file bytes
        bytes_sent = 0
        try:
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.network.socket.sendall(chunk)
                    bytes_sent += len(chunk)
                    if progress_callback:
                        progress_callback(bytes_sent, filesize)
                        
            # Wait for transfer complete confirmation
            final_response = self.network.receive_message(timeout=10.0)
            if final_response and final_response.get("type") == "FILE_TRANSFER_SUCCESS":
                return True, "File transferred successfully"
            else:
                return False, f"Server reported failure: {final_response.get('message', 'Unknown error') if final_response else 'Timeout'}"
                
        except Exception as e:
            return False, f"Error during transfer: {e}"

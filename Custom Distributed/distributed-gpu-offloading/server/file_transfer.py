import os

class FileReceiver:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def receive_file(self, client_socket, filename, filesize, expected_checksum, send_message_func):
        filepath = os.path.join(self.output_dir, filename)
        
        # Send ACK
        send_message_func(client_socket, {"type": "FILE_TRANSFER_ACK", "status": "ready"})
        
        bytes_received = 0
        try:
            with open(filepath, "wb") as f:
                while bytes_received < filesize:
                    chunk_size = min(65536, filesize - bytes_received)
                    chunk = client_socket.recv(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_received += len(chunk)
                    
            if bytes_received == filesize:
                return True, filepath
            else:
                return False, None
                
        except Exception as e:
            print(f"Error receiving file: {e}")
            return False, None

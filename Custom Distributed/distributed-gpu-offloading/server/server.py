import socket
import threading
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GPUWorkerServer:
    def __init__(self, host='0.0.0.0', port=5000):
        from task_manager import TaskManager
        from gpu_worker import GPUWorker

        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.is_running = False

        self.task_manager = TaskManager()
        self.gpu_worker = GPUWorker(self.task_manager)

    def start(self):
        self.server_socket.listen(5)
        self.is_running = True
        self.gpu_worker.start()
        logging.info(f"Server listening on {self.host}:{self.port}")
        
        try:
            while self.is_running:
                client_socket, client_address = self.server_socket.accept()
                logging.info(f"Accepted connection from {client_address}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
                client_thread.daemon = True
                client_thread.start()
        except Exception as e:
            if self.is_running:
                logging.error(f"Server error: {e}")
        finally:
            self.stop()

    def stop(self):
        self.is_running = False
        self.gpu_worker.stop()
        self.server_socket.close()
        logging.info("Server stopped.")

    def handle_client(self, client_socket, client_address):
        try:
            while True:
                # Receive header (length of message)
                header = client_socket.recv(4)
                if not header:
                    break
                
                msg_length = int.from_bytes(header, byteorder='big')
                data = b""
                while len(data) < msg_length:
                    packet = client_socket.recv(4096)
                    if not packet:
                        break
                    data += packet
                
                if not data:
                    break
                
                message = json.loads(data.decode('utf-8'))
                self.process_message(client_socket, message)
        
        except ConnectionResetError:
            logging.info(f"Connection reset by {client_address}")
        except Exception as e:
            logging.error(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()
            logging.info(f"Connection closed for {client_address}")

    def process_message(self, client_socket, message):
        msg_type = message.get("type")
        if msg_type == "PING":
            self.send_message(client_socket, {"type": "PONG", "status": "available"})
        elif msg_type == "HANDSHAKE":
            self.send_message(client_socket, {"type": "HANDSHAKE_ACK", "status": "ready"})
        elif msg_type == "FILE_TRANSFER_START":
            self.handle_file_transfer(client_socket, message)
        else:
            self.send_message(client_socket, {"type": "ERROR", "message": "Unknown command"})

    def handle_file_transfer(self, client_socket, message):
        import os
        import sys
        import uuid
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from file_transfer import FileReceiver
        from shared.checksum import calculate_sha256

        filename = message.get("filename")
        filesize = message.get("filesize")
        expected_checksum = message.get("checksum")
        config = message.get("config", {})
        
        receiver = FileReceiver()
        success, filepath = receiver.receive_file(client_socket, filename, filesize, expected_checksum, self.send_message)
        
        if success:
            logging.info(f"File {filename} received. Verifying checksum...")
            actual_checksum = calculate_sha256(filepath)
            if actual_checksum == expected_checksum:
                logging.info(f"Checksum verified for {filename}")
                self.send_message(client_socket, {"type": "FILE_TRANSFER_SUCCESS", "message": "Checksum verified"})
                
                # Queue task
                task_id = str(uuid.uuid4())
                self.task_manager.add_task(client_socket, task_id, filepath, config)
                self.send_message(client_socket, {"type": "TASK_QUEUED", "task_id": task_id})
            else:
                logging.error(f"Checksum mismatch for {filename}")
                self.send_message(client_socket, {"type": "FILE_TRANSFER_ERROR", "message": "Checksum mismatch"})
                os.remove(filepath)
        else:
            logging.error(f"Incomplete transfer for {filename}")
            self.send_message(client_socket, {"type": "FILE_TRANSFER_ERROR", "message": "Incomplete transfer"})

    def send_message(self, client_socket, message):
        data = json.dumps(message).encode('utf-8')
        header = len(data).to_bytes(4, byteorder='big')
        client_socket.sendall(header + data)

if __name__ == "__main__":
    server = GPUWorkerServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

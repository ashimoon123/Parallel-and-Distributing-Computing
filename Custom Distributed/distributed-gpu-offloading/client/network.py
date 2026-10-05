import socket
import json
import time

class ClientNetwork:
    def __init__(self, host, port=5000):
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            return True, "Connected successfully"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def send_message(self, message):
        if not self.socket:
            return False, "Not connected"
            
        try:
            data = json.dumps(message).encode('utf-8')
            header = len(data).to_bytes(4, byteorder='big')
            self.socket.sendall(header + data)
            return True, "Sent"
        except Exception as e:
            return False, f"Send failed: {e}"

    def receive_message(self, timeout=None):
        if not self.socket:
            return None
            
        if timeout:
            self.socket.settimeout(timeout)
            
        try:
            header = self.socket.recv(4)
            if not header:
                return None
                
            msg_length = int.from_bytes(header, byteorder='big')
            data = b""
            while len(data) < msg_length:
                packet = self.socket.recv(4096)
                if not packet:
                    return None
                data += packet
                
            return json.loads(data.decode('utf-8'))
        except socket.timeout:
            return {"type": "TIMEOUT"}
        except Exception as e:
            print(f"Receive error: {e}")
            return None
        finally:
            if timeout:
                self.socket.settimeout(None)

    def ping(self):
        start_time = time.time()
        success, _ = self.send_message({"type": "PING"})
        if not success:
            return -1
            
        response = self.receive_message(timeout=2.0)
        if response and response.get("type") == "PONG":
            return (time.time() - start_time) * 1000 # returns ping in ms
        return -1

    def handshake(self):
        success, _ = self.send_message({"type": "HANDSHAKE"})
        if not success:
            return False
            
        response = self.receive_message(timeout=2.0)
        if response and response.get("type") == "HANDSHAKE_ACK":
            return True
        return False

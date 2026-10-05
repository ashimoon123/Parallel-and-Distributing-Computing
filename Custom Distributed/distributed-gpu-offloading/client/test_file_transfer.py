import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.network import ClientNetwork
from client.file_transfer import FileSender
from shared.checksum import calculate_sha256

def progress_callback(bytes_sent, total_bytes):
    percent = (bytes_sent / total_bytes) * 100
    print(f"\rProgress: {percent:.2f}% ({bytes_sent}/{total_bytes} bytes)", end='')

def main():
    # 1. Create a dummy file to test
    dummy_file = "test_video.mp4"
    print("Creating dummy file...")
    with open(dummy_file, "wb") as f:
        # Create a 5MB dummy file
        f.write(os.urandom(5 * 1024 * 1024))
        
    print(f"Calculating SHA-256 for {dummy_file}...")
    checksum = calculate_sha256(dummy_file)
    print(f"Checksum: {checksum}")
    
    print("\nConnecting to server...")
    client = ClientNetwork('127.0.0.1', 5000)
    success, msg = client.connect()
    if not success:
        print(f"Connection failed: {msg}")
        return
        
    sender = FileSender(client)
    print("Starting file transfer...")
    
    success, msg = sender.send_file(dummy_file, checksum, progress_callback)
    print(f"\nTransfer Result: {success}, Message: {msg}")
    
    client.disconnect()
    
    # Cleanup
    os.remove(dummy_file)

if __name__ == "__main__":
    main()

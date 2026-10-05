import hashlib

def calculate_sha256(filepath, chunk_size=8192):
    """Calculates the SHA-256 checksum of a file without loading it all into memory."""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        return None

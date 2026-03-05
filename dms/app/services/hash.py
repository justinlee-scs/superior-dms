import hashlib

def compute_content_hash(file_bytes: bytes) -> str:
    """Handle compute content hash.

    Parameters:
        file_bytes (type=bytes): Raw file content used for validation or processing.
    """
    return hashlib.sha256(file_bytes).hexdigest()

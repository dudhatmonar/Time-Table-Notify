import os
import base64
from cryptography.hazmat.primitives.asymmetric import ec

KEYS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vapid_keys")
PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "private_key.txt")
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "public_key.txt")

def generate_vapid_keys():
    """
    Generates a secure ECC R1 key pair in the standard base64url format required for VAPID.
    """
    os.makedirs(KEYS_DIR, exist_ok=True)
    
    # Generate SECP256R1 curve key
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_value = private_key.private_numbers().private_value
    
    # Extract private key bytes (32 bytes) and encode to base64url
    private_bytes = private_value.to_bytes(32, byteorder='big')
    vapid_private = base64.urlsafe_b64encode(private_bytes).decode('utf-8').rstrip('=')
    
    # Extract public key (uncompressed point format: 0x04 prefix followed by X and Y coords)
    public_numbers = private_key.public_key().public_numbers()
    x_bytes = public_numbers.x.to_bytes(32, byteorder='big')
    y_bytes = public_numbers.y.to_bytes(32, byteorder='big')
    public_bytes = b'\x04' + x_bytes + y_bytes
    vapid_public = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')
    
    # Write to local file directory
    with open(PRIVATE_KEY_PATH, "w") as f:
        f.write(vapid_private)
    with open(PUBLIC_KEY_PATH, "w") as f:
        f.write(vapid_public)
        
    return vapid_private, vapid_public

def get_vapid_keys():
    """
    Retrieves VAPID keys, generating them if they don't exist.
    """
    if not os.path.exists(PRIVATE_KEY_PATH) or not os.path.exists(PUBLIC_KEY_PATH):
        return generate_vapid_keys()
    
    with open(PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read().strip()
    with open(PUBLIC_KEY_PATH, "r") as f:
        public_key = f.read().strip()
        
    return private_key, public_key

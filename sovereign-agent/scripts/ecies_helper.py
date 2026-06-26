"""
Custom ECIES implementation compatible with eciespy (symmetric_nonce_length=12).
Uses: eth_keys (secp256k1) + pycryptodome (AES-GCM) + cryptography (HKDF).
No need for coincurve or eciespy packages.
"""

import os
import struct

from Crypto.Cipher import AES
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from eth_keys import keys as eth_keys


# ECIES config matching eciespy with symmetric_nonce_length=12
NONCE_LENGTH = 12
TAG_LENGTH = 16
KEY_LENGTH = 32  # AES-256


def _ecdh_shared_secret(private_key_bytes: bytes, public_key_bytes: bytes) -> bytes:
    """Compute ECDH shared secret using secp256k1."""
    from eth_keys.backends import NativeECCBackend
    backend = NativeECCBackend()
    
    # Parse the public key (uncompressed 65 bytes or compressed 33 bytes)
    if len(public_key_bytes) == 65:
        pub_key = eth_keys.PublicKey(public_key_bytes[1:])  # strip 0x04 prefix
    elif len(public_key_bytes) == 64:
        pub_key = eth_keys.PublicKey(public_key_bytes)
    elif len(public_key_bytes) == 33:
        # Compressed public key - need to decompress
        pub_key = _decompress_pubkey(public_key_bytes)
    else:
        raise ValueError(f"Invalid public key length: {len(public_key_bytes)}")
    
    priv_key = eth_keys.PrivateKey(private_key_bytes)
    
    # ECDH: multiply the public key by our private key
    # eth_keys doesn't have direct ECDH, so we use the low-level math
    from eth_keys.backends.native.ecdsa import (
        decode_public_key,
        encode_raw_public_key,
    )
    from eth_keys.backends.native.jacobian import (
        fast_multiply,
    )
    
    pub_point = decode_public_key(pub_key.to_bytes())
    shared_point = fast_multiply(pub_point, int.from_bytes(private_key_bytes, 'big'))
    shared_x = shared_point[0].to_bytes(32, 'big')
    
    return shared_x


def _decompress_pubkey(compressed: bytes) -> "eth_keys.PublicKey":
    """Decompress a 33-byte compressed secp256k1 public key."""
    from eth_keys.backends.native.jacobian import (
        fast_multiply,
    )
    
    P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    
    prefix = compressed[0]
    x = int.from_bytes(compressed[1:], 'big')
    
    # y^2 = x^3 + 7 (mod P)
    y_squared = (pow(x, 3, P) + 7) % P
    y = pow(y_squared, (P + 1) // 4, P)
    
    # Check parity
    if (prefix == 0x02 and y % 2 != 0) or (prefix == 0x03 and y % 2 == 0):
        y = P - y
    
    pub_bytes = x.to_bytes(32, 'big') + y.to_bytes(32, 'big')
    return eth_keys.PublicKey(pub_bytes)


def encrypt(public_key_hex: str, plaintext: bytes) -> bytes:
    """
    ECIES encrypt compatible with eciespy (nonce_length=12).
    
    Output format: ephemeral_pubkey (65 bytes) + nonce (12 bytes) + tag (16 bytes) + ciphertext
    
    Args:
        public_key_hex: Hex string of the recipient's public key
        plaintext: Data to encrypt
    
    Returns:
        Encrypted bytes
    """
    # Parse recipient public key
    pub_key_bytes = bytes.fromhex(public_key_hex)
    
    # Generate ephemeral key pair
    ephemeral_privkey_bytes = os.urandom(32)
    ephemeral_privkey = eth_keys.PrivateKey(ephemeral_privkey_bytes)
    ephemeral_pubkey = ephemeral_privkey.public_key
    
    # Uncompressed ephemeral public key (65 bytes: 0x04 + x + y)
    ephemeral_pubkey_bytes = b'\x04' + ephemeral_pubkey.to_bytes()
    
    # ECDH shared secret
    shared_secret = _ecdh_shared_secret(ephemeral_privkey_bytes, pub_key_bytes)
    
    # Derive AES key using HKDF (matching eciespy behavior)
    aes_key = HKDF(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=None,
        info=b"",
    ).derive(shared_secret)
    
    # AES-GCM encrypt
    nonce = os.urandom(NONCE_LENGTH)
    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce, mac_len=TAG_LENGTH)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    
    # Output: ephemeral_pub (65) + nonce (12) + tag (16) + ciphertext
    return ephemeral_pubkey_bytes + nonce + tag + ciphertext


if __name__ == "__main__":
    # Quick self-test
    test_privkey = eth_keys.PrivateKey(os.urandom(32))
    test_pubkey = test_privkey.public_key
    test_pubkey_hex = "04" + test_pubkey.to_bytes().hex()
    
    message = b"Hello, ECIES!"
    encrypted = encrypt(test_pubkey_hex, message)
    print(f"[OK] ECIES encrypt OK ({len(encrypted)} bytes)")
    print(f"   Ephemeral pub: {len(encrypted[:65])} bytes")
    print(f"   Nonce: {len(encrypted[65:77])} bytes")
    print(f"   Tag: {len(encrypted[77:93])} bytes")
    print(f"   Ciphertext: {len(encrypted[93:])} bytes")

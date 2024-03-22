import hashlib


def encrypt(key: str, plaintext: str) -> str:
    # use SHA-256 to generate a hash of the key
    hashed_key: bytes = hashlib.sha256(key.encode()).digest()

    # use XOR to encrypt the plaintext
    ciphertext: bytearray = bytearray(plaintext.encode())

    for i in range(len(ciphertext)):
        ciphertext[i] ^= hashed_key[i % len(hashed_key)]

    # convert the ciphertext to a hex string and return it
    return ciphertext.hex()

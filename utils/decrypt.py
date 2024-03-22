import hashlib

def decrypt(key: str, ciphertext: str) -> str:
    # use SHA-256 to generate a hash of the key
    hashed_key: bytes = hashlib.sha256(key.encode()).digest()

    # convert the ciphertext from a string to a bytearray
    byte_ciphertext: bytearray = bytearray.fromhex(ciphertext)

    # use XOR to decrypt the ciphertext
    plaintext: str = ""

    for i in range(len(byte_ciphertext)):
        plaintext += chr(byte_ciphertext[i] ^ hashed_key[i % len(hashed_key)])

    # return the decrypted plaintext
    return plaintext

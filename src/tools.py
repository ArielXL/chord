import hashlib

# Default values if command line arguments not given
IP = '127.0.0.1'
PORT = 8080
BUFFER = 4096
MAX_BITS = 10
MAX_NODES = 2 ** MAX_BITS

def getHash(key):
    '''
    Takes key string, uses SHA-1 hashing and returns 
    a 10-bit (1024) compressed integer.
    '''
    result = hashlib.sha1(key.encode())
    return int(result.hexdigest(), 16) % MAX_NODES
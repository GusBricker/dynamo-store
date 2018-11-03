from boto3.dynamodb.types import Binary
import hashlib
import base64
from Crypto import Random
from Crypto.Cipher import AES
from dynamo_store.log import logger

class AESCipher(object):

    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        enc = base64.b64encode(iv + cipher.encrypt(raw))
        logger.debug('Encrypted item: %s > %s' % (raw, enc.decode('utf-8')))
        return enc

    def decrypt(self, enc1):
        if isinstance(enc1, Binary):
            enc1 = enc1.value

        if not enc1:
            return enc1

        enc = base64.b64decode(enc1)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        data = self._unpad(cipher.decrypt(enc[AES.block_size:]))
        data = data.decode('utf-8')
        logger.debug('Decrypted item: %s > %s' % (enc1.decode('utf-8'), data))
        return data

    def _pad(self, s):
        if not isinstance(s, str):
            s = str(s)
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

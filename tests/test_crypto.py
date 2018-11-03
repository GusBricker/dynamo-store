from dynamo_store.aescrypt import AESCipher
import pytest

@pytest.mark.parametrize("inpt, output, key", [
    ("abc", "abc", "hello"),
    ("Well hello there good sir, how is your day", 'Well hello there good sir, how is your day', "hello"),
    (None, 'None', "hello"),
    ([], "[]", "hello")  # Type information is lost when encrypting, therefore best effort is to cast
])
def test_crypto(inpt, output, key):
    cipher = AESCipher(key)
    assert cipher
    enc = cipher.encrypt(inpt)
    assert inpt != enc
    dec = cipher.decrypt(enc)
    assert dec == output

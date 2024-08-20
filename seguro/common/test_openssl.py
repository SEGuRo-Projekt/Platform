import pytest
import hashlib
import seguro.common.openssl as openssl


@pytest.fixture(
    params=["default", "tpm2"],
)
def provider(request):
    return request.param


@pytest.fixture
def ssl():
    return openssl.OpenSSL(["default", "tpm2"])


@pytest.fixture(params=["rsa", "ec"])
def algorithm(request):
    return request.param


@pytest.fixture
def private_key(ssl, algorithm, provider) -> openssl.PrivateKey:
    return ssl.generate_keypair(algorithm, provider=provider)


@pytest.fixture
def public_key(private_key, ssl):
    return private_key.public_key(ssl)


@pytest.fixture
def data():
    return b"hello world"


@pytest.fixture
def digest(data):
    d = hashlib.sha256()
    d.update(data)

    return d.digest()


def test_generate_key(private_key, provider):
    with open(f"key_{provider}_{private_key.algorithm}.pem", "wb+") as f:
        private_key.write_pem(f)


def test_sign_verify(ssl, private_key, public_key, digest):
    signature = ssl.sign(private_key, digest)

    print(signature.hex())

    ssl.verify_signature(public_key, signature, digest)

    with pytest.raises(openssl.Error):
        digest = b"1" + digest[1:]
        ssl.verify_signature(public_key, signature, digest)


def test_certificate(ssl, digest):
    with open("keys/clients/mp1.key", "rb") as f:
        private_key = openssl.PrivateKey.read_pem(f)

    with open("keys/clients/mp1.crt", "rb") as f:
        cert = openssl.Certificate.read_pem(f)
        public_key = cert.public_key()

    signature = ssl.sign(private_key, digest)

    ssl.verify_signature(public_key, signature, digest)


def test_timestamp(ssl, digest):
    tsr = ssl.timestamp_query("https://freetsa.org/tsr", digest)

    ssl.timestamp_verify(
        tsr, digest, "freetsa_ca.pem", untrusteds=["freetsa_tsa.pem"]
    )

    with pytest.raises(openssl.Error):
        digest = b"1" + digest[1:]
        ssl.timestamp_verify(
            tsr, digest, "freetsa_ca.pem", untrusteds=["freetsa_tsa.pem"]
        )

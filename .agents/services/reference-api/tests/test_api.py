import base64
import os

os.environ.setdefault("MBUC_AES_KEY_BASE64", base64.b64encode(bytes(range(32))).decode("ascii"))

from fastapi.testclient import TestClient
from reference_api.main import app

client = TestClient(app)


def test_health_and_round_trip() -> None:
    assert client.get("/health").json() == {"status": "healthy"}
    encrypted = client.post("/v1/encrypt", json={"plaintext_base64": base64.b64encode(b"secret").decode(), "associated_data": "tenant:acme"})
    assert encrypted.status_code == 200
    decrypted = client.post("/v1/decrypt", json={"envelope": encrypted.json()["envelope"], "associated_data": "tenant:acme"})
    assert decrypted.status_code == 200
    assert base64.b64decode(decrypted.json()["plaintext_base64"]) == b"secret"

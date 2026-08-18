import pytest

from corporate_security import AesGcmService, CorporateError


class StaticKeyProvider:
    def get_key(self) -> bytes:
        return bytes(range(32))


@pytest.fixture
def service() -> AesGcmService:
    return AesGcmService(StaticKeyProvider())


def test_round_trip(service: AesGcmService) -> None:
    aad = b"tenant:acme|purpose:profile"
    envelope = service.encrypt(b"corporate secret", aad)
    assert envelope.startswith("v1.")
    assert service.decrypt(envelope, aad) == b"corporate secret"


def test_tampered_envelope_is_rejected(service: AesGcmService) -> None:
    aad = b"tenant:acme"
    envelope = service.encrypt(b"secret", aad)
    replacement = "A" if envelope[-1] != "A" else "B"
    with pytest.raises(CorporateError) as captured:
        service.decrypt(envelope[:-1] + replacement, aad)
    assert captured.value.code == "authentication_failed"


def test_wrong_aad_is_rejected(service: AesGcmService) -> None:
    envelope = service.encrypt(b"secret", b"tenant:acme")
    with pytest.raises(CorporateError) as captured:
        service.decrypt(envelope, b"tenant:other")
    assert captured.value.code == "authentication_failed"

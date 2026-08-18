from __future__ import annotations


class EpgSyncError(RuntimeError):
    """Erro público de sincronização sem URL, credenciais ou resposta do provedor."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code

    def __str__(self) -> str:
        return f"{super().__str__()} [{self.code}]"

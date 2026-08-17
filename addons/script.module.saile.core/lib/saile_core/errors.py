from __future__ import annotations


class SaileError(RuntimeError):
    """Erro público com código estável e mensagem segura para o usuário."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.message} (Código: {self.code})"

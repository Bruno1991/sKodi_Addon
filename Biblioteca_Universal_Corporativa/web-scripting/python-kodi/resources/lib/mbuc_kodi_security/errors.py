from __future__ import annotations


class CorporateError(Exception):
    def __init__(self, code: str, public_message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
        self.__cause__ = cause

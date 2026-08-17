"""Módulo de Controle Parental para proteção por senha (PIN de até 6 dígitos) de conteúdos adultos e configurações."""
from __future__ import annotations

import re
import unicodedata

RESTRICTED_KEYWORDS = [
    "xxx",
    "adulto",
    "adultos",
    "adult",
    "adults",
    "+18",
    "18+",
    "18 +",
    "porn",
    "porno",
    "erotico",
    "erotica",
    "eroticos",
    "eroticas",
    "for adults",
    "playboy",
    "sexy",
    "hot",
    "venus",
    "red light",
    "redlight",
    "prive",
    "sensual",
    "hentai",
    "hustler",
    "brazzers",
    "penthouse",
    "manpack",
]


def _normalize_text(text: str) -> str:
    """Remove acentuação e converte para minúsculas para comparação uniforme."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    return ascii_text.lower()


_WORD_BOUNDARY_PATTERNS = [
    re.compile(r"(?:^|\W|_)" + re.escape(kw) + r"(?:$|\W|_)", re.IGNORECASE)
    for kw in RESTRICTED_KEYWORDS
]


def is_restricted(name: str = "", plot: str = "", category_name: str = "", tmdb_adult: bool = False) -> bool:
    """Verifica se o conteúdo ou categoria possui classificação restrita/adulta."""
    if tmdb_adult:
        return True

    text_to_check = _normalize_text(f"{name} {category_name} {plot}")
    for pattern in _WORD_BOUNDARY_PATTERNS:
        if pattern.search(text_to_check):
            return True
    return False


def get_parental_pin(addon: object) -> str:
    """Recupera o PIN cadastrado nas configurações do add-on."""
    if hasattr(addon, "getSetting"):
        return str(addon.getSetting("parental_pin") or "").strip()
    return ""


def set_parental_pin(addon: object, pin: str) -> None:
    """Salva o novo PIN nas configurações do add-on."""
    if hasattr(addon, "setSetting"):
        addon.setSetting("parental_pin", pin.strip())


def prompt_pin_dialog(heading: str) -> str | None:
    """Exibe teclado numérico com máscara oculta (***) para inserção de PIN de até 6 dígitos."""
    import xbmcgui

    dialog = xbmcgui.Dialog()
    # numeric(0, heading, default) -> input numérico nativo
    entered = dialog.numeric(0, heading, "")
    if entered is None or entered == "":
        return None
    return str(entered).strip()[:6]


def verify_parental_pin(addon: object, reason: str = "Conteúdo Restrito") -> bool:
    """Verifica a senha parental. Se não houver senha cadastrada, solicita a criação inicial."""
    from saile_core.notifications import notify_error, notify_info, notify_success

    current_pin = get_parental_pin(addon)

    # 1. Caso não haja senha cadastrada ainda -> Solicita criação inicial de 1 a 6 dígitos
    if not current_pin:
        notify_info("Controle Parental", "Cadastre uma senha de até 6 dígitos para proteger o conteúdo.")
        new_pin = prompt_pin_dialog("Criar Senha Parental (até 6 dígitos):")
        if not new_pin or not new_pin.isdigit():
            notify_error("Controle Parental", "Criação de senha cancelada.")
            return False

        confirm_pin = prompt_pin_dialog("Confirme a nova Senha Parental:")
        if new_pin != confirm_pin:
            notify_error("Controle Parental", "As senhas digitadas não conferem.")
            return False

        set_parental_pin(addon, new_pin)
        notify_success("Controle Parental", "Senha cadastrada com sucesso!")
        return True

    # 2. Senha existente -> Solicita confirmação com máscara
    entered_pin = prompt_pin_dialog(f"Digite a Senha Parental ({reason}):")
    if not entered_pin:
        return False

    if entered_pin == current_pin:
        return True

    notify_error("Controle Parental", "Senha incorreta!")
    return False


def verify_settings_access(addon: object) -> bool:
    """Valida a senha antes de permitir a abertura do menu de configurações do add-on."""
    current_pin = get_parental_pin(addon)
    if not current_pin:
        return True
    return verify_parental_pin(addon, reason="Acessar Configurações")

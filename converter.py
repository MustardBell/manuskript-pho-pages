import re

from .model import PhoModelError


PhoFormatError = PhoModelError


def is_pho_page(text):
    normalized = str(text or "").replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    return bool(re.search(
        r"(?ms)^PHO Interlude[^\n]*\n.*^EOPHO Interlude[^\n]*$",
        normalized.strip(),
    ))

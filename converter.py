import re

from manuskript.converters.markdownToBBCode import markdown_to_bbcode

from .export_renderers import PhoBBCodeRenderer
from .model import PhoModelError, PhoPage
from .presentation import PhoPresentationBuilder


PhoFormatError = PhoModelError


def is_pho_page(text):
    normalized = str(text or "").replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    return bool(re.search(
        r"(?ms)^PHO Interlude[^\n]*\n.*^EOPHO Interlude[^\n]*$",
        normalized.strip(),
    ))


def convert_pho_page(text):
    """Compatibility entry point for direct PHO→BBCode rendering."""
    normalized = str(text or "").replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    if not is_pho_page(normalized):
        raise PhoFormatError(
            "A PHO page must be wrapped in PHO Interlude and "
            "EOPHO Interlude directives."
        )
    presentation = PhoPresentationBuilder().build(
        PhoPage.parse(normalized)
    )
    return PhoBBCodeRenderer().render(
        presentation,
        "bbcode",
        {},
    ).content


def convert_document(text):
    normalized = str(text or "").replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    if is_pho_page(normalized):
        return convert_pho_page(normalized)
    return markdown_to_bbcode(normalized)

import html

from manuskript.plugins import HTML, MARKDOWN
from manuskript.plugins import RenderedDocument

from .export_renderers import MARKDOWN_STYLE, PhoMarkdownRenderer
from .presentation import PhoPresentation


class PhoPageRenderer:
    """Read-only HTML view over the semantic PHO presentation model.

    PHO owns its DSL and turns it into Markdown itself; nobody else knows
    how. The hop from Markdown to HTML is not its business. Performing that
    hop here meant opting out of everything the host and other plugins had
    taught the conversion, so a page read one way in this view and another
    way in an export of the same text -- a list written ``1)`` came out a
    list in one and a paragraph in the other.

    So the conversion is asked for. This renderer does not know which
    library performs it, or that other plugins have added to it.
    """

    STYLE = """
        body { line-height: 1.35; background: #fbfaf5; color: #171717; }
        p.pho-separator { text-align: center; margin: 1.2em 0; }
        blockquote { margin: 0.7em 0 0.7em 1.4em; }
        img { max-width: 100%; }
    """

    def __init__(self, conversion, page_type=None):
        #: The host's conversion service, taken as the ``conversion``
        #: capability. Declared in plugin.json, so asking for it is allowed.
        self._conversion = conversion
        #: Named when converting, so an addition written for PHO pages
        #: applies here and one written for ordinary documents does not.
        self._page_type = page_type

    def render(self, model):
        if not isinstance(model, PhoPresentation):
            raise TypeError(
                "PHO reading views require PhoPresentation models."
            )
        markdown = PhoMarkdownRenderer().render(
            model,
            MARKDOWN,
            {},
        ).content
        if self._conversion.can_convert(MARKDOWN, HTML):
            body = self._separated(
                self._conversion.convert(
                    markdown,
                    MARKDOWN,
                    HTML,
                    page_type=self._page_type,
                )
            )
        else:
            # This Manuskript cannot produce HTML from Markdown at all. The
            # source is still readable, which beats an empty view.
            body = "<pre>{}</pre>".format(html.escape(markdown))
        return RenderedDocument(
            "<html><head><style>{}</style></head><body>{}</body></html>"
            .format(self.STYLE, body)
        )

    def _separated(self, body):
        """Give PHO's page separator its own class, once it is a paragraph.

        Presentation of PHO's own marker, so it stays here rather than
        travelling into the conversion as an addition everybody would get.
        """
        separator = html.escape(MARKDOWN_STYLE["separator"])
        return body.replace(
            "<p>{}</p>".format(separator),
            '<p class="pho-separator">{}</p>'.format(separator),
        )

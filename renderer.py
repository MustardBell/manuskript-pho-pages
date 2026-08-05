import html

from manuskript.plugins import MARKDOWN as MARKDOWN_MEDIA_TYPE
from manuskript.plugins import RenderedDocument

from .export_renderers import MARKDOWN_STYLE, PhoMarkdownRenderer
from .presentation import PhoPresentation

try:
    import markdown as MARKDOWN
except ImportError:
    MARKDOWN = None


class PhoPageRenderer:
    """Read-only HTML view over the semantic PHO presentation model."""

    STYLE = """
        body { line-height: 1.35; background: #fbfaf5; color: #171717; }
        p.pho-separator { text-align: center; margin: 1.2em 0; }
        blockquote { margin: 0.7em 0 0.7em 1.4em; }
        img { max-width: 100%; }
    """

    def render(self, model):
        if not isinstance(model, PhoPresentation):
            raise TypeError(
                "PHO reading views require PhoPresentation models."
            )
        markdown = PhoMarkdownRenderer().render(
            model,
            MARKDOWN_MEDIA_TYPE,
            {},
        ).content
        if MARKDOWN is None:
            body = "<pre>{}</pre>".format(html.escape(markdown))
        else:
            body = MARKDOWN.markdown(markdown)
            separator = html.escape(MARKDOWN_STYLE["separator"])
            body = body.replace(
                "<p>{}</p>".format(separator),
                '<p class="pho-separator">{}</p>'.format(separator),
            )
        return RenderedDocument(
            "<html><head><style>{}</style></head><body>{}</body></html>"
            .format(self.STYLE, body)
        )

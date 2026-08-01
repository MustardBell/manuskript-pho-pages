from manuskript.plugins import (
    ExtensionDescriptor,
    OptionField,
    PageRendererContribution,
    PageTypeContribution,
)

from .converter import is_pho_page
from .export_renderers import PhoBBCodeRenderer, PhoMarkdownRenderer
from .presentation import PhoPresentationParser
from .renderer import PhoPageRenderer
from .wizard import PhoPageWizard


def style_options():
    return (
        OptionField("separator", "Page separator", default="■"),
        OptionField("topic_label", "Topic label", default="♦ Topic:"),
        OptionField("board_label", "Board root", default="In: Boards"),
        OptionField("board_separator", "Board separator", default="►"),
        OptionField("reply_marker", "Reply marker", default="►"),
        OptionField(
            "welcome_title",
            "Welcome heading",
            default="Welcome to the Parahumans Online message boards.",
        ),
        OptionField(
            "showing_template",
            "Page heading template",
            default="Showing page {current} of {total}",
            description="Available fields: {current}, {total}.",
        ),
        OptionField(
            "end_template",
            "Page ending template",
            default="End of Page. {navigation}",
            description=(
                "Available fields: {current}, {total}, {navigation}."
            ),
        ),
    )


def register(api):
    api.register_page_type(
        PageTypeContribution(
            descriptor=ExtensionDescriptor(
                id="manuskript.pho-page",
                name="PHO page",
                description=(
                    "Structured Parahumans Online page with a full "
                    "rendered reading view."
                ),
            ),
            property_label="PHO page",
            detector=is_pho_page,
            parser_factory=PhoPresentationParser,
            renderer_factory=PhoPageRenderer,
            wizard_factory=PhoPageWizard,
        )
    )
    api.register_page_renderer(
        PageRendererContribution(
            descriptor=ExtensionDescriptor(
                id="manuskript.pho-renderer.markdown",
                name="PHO portable Markdown",
                description=(
                    "Format-neutral PHO presentation used as the "
                    "fallback for HTML, LaTeX, e-book, and other "
                    "ordinary conversion pipelines."
                ),
            ),
            page_type_id="manuskript.pho-page",
            renderer_factory=PhoMarkdownRenderer,
            target_formats=("markdown",),
            options=style_options(),
        )
    )
    api.register_page_renderer(
        PageRendererContribution(
            descriptor=ExtensionDescriptor(
                id="manuskript.pho-renderer.bbcode",
                name="PHO forum BBCode",
                description=(
                    "Direct PHO BBCode with forum-specific formatting "
                    "and mention neutralization."
                ),
            ),
            page_type_id="manuskript.pho-page",
            renderer_factory=PhoBBCodeRenderer,
            target_formats=("bbcode",),
            options=style_options(),
            priority=100,
        )
    )

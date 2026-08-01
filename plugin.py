from manuskript.plugins import (
    ExtensionDescriptor,
    OptionField,
    PageRendererContribution,
    PageTypeContribution,
)

from .converter import is_pho_page
from .export_renderers import (
    BBCODE_STYLE,
    MARKDOWN_STYLE,
    PhoBBCodeRenderer,
    PhoMarkdownRenderer,
)
from .presentation import PhoPresentationParser
from .renderer import PhoPageRenderer
from .wizard import PhoPageWizard


CONTENT_FIELDS = (
    ("separator", "Page separator", "General", ""),
    ("default_reader", "Default reader", "General", ""),
    ("default_topic", "Default topic", "General", ""),
    ("welcome_title", "Welcome heading", "Welcome", ""),
    (
        "logged_in_template",
        "Logged-in sentence",
        "Welcome",
        "Available fields: {reader}, {reader_name}.",
    ),
    ("viewing_title", "Viewing heading", "Welcome", ""),
    (
        "viewing_replied_threads",
        "Replied threads item",
        "Welcome",
        "",
    ),
    (
        "viewing_new_replies",
        "New replies item",
        "Welcome",
        "",
    ),
    (
        "viewing_private_replies",
        "Private replies item",
        "Welcome",
        "",
    ),
    (
        "viewing_original_post",
        "Original-post item",
        "Welcome",
        "",
    ),
    (
        "viewing_posts_per_page",
        "Posts-per-page item",
        "Welcome",
        "Available field: {posts}.",
    ),
    (
        "viewing_private_messages",
        "Private-history item",
        "Welcome",
        "Available field: {messages}.",
    ),
    (
        "viewing_chronological",
        "Chronological-order item",
        "Welcome",
        "",
    ),
    ("topic_label", "Topic label", "Thread headings", ""),
    (
        "topic_template",
        "Topic text template",
        "Thread headings",
        "Available fields: {label}, {topic}.",
    ),
    ("board_label", "Board root", "Thread headings", ""),
    ("board_separator", "Board separator", "Thread headings", ""),
    (
        "board_template",
        "Board text template",
        "Thread headings",
        "Available fields: {label}, {boards}.",
    ),
    ("reply_marker", "Reply marker", "Posts", ""),
    (
        "original_poster_label",
        "Original-poster label",
        "Posts",
        "",
    ),
    ("posted_label", "Posted label", "Posts", ""),
    ("replied_label", "Replied label", "Posts", ""),
    ("on_label", "Date preposition", "Posts", ""),
    (
        "said_template",
        "Quote attribution",
        "Posts",
        "Available field: {author}.",
    ),
    (
        "date_template",
        "Visible date",
        "Dates",
        (
            "Fields include {source_label}, {year}, {month}, "
            "{month_short}, {month_long}, {day}, {day_padded}, "
            "{ordinal}, {hour_12}, {hour_24}, {minute}, {second}, "
            "{am_pm}, {zone}, and {iso}."
        ),
    ),
    (
        "tooltip_template",
        "Date tooltip",
        "Dates",
        "The date fields plus {source_tooltip} are available.",
    ),
    (
        "showing_template",
        "Page heading text",
        "Pagination",
        "Available fields: {current}, {total}.",
    ),
    (
        "end_template",
        "Page ending text",
        "Pagination",
        "Available fields: {current}, {total}, {navigation}.",
    ),
    (
        "navigation_separator",
        "Navigation separator",
        "Pagination",
        r"Use \n for a line break.",
    ),
    (
        "navigation_ellipsis",
        "Navigation ellipsis",
        "Pagination",
        "",
    ),
)


FORMAT_FIELDS = (
    (
        "document_separator",
        "Document block separator",
        "Document structure",
        r"Use \n and \t for line breaks and tabs.",
    ),
    (
        "block_separator",
        "Thread block separator",
        "Document structure",
        r"Use \n and \t for line breaks and tabs.",
    ),
    (
        "post_separator",
        "Post field separator",
        "Document structure",
        r"Use \n and \t for line breaks and tabs.",
    ),
    (
        "separator_template",
        "Page separator template",
        "Document structure",
        "Available field: {separator}.",
    ),
    (
        "welcome_container_template",
        "Welcome block template",
        "Welcome formatting",
        (
            "Fields: {separator}, {title}, {logged_in}, "
            "{viewing_title}, {items}. Use \\n for line breaks."
        ),
    ),
    (
        "welcome_title_template",
        "Welcome title template",
        "Welcome formatting",
        "Available field: {content}.",
    ),
    (
        "reader_template",
        "Reader-name template",
        "Welcome formatting",
        "Available fields: {content}, {reader}.",
    ),
    (
        "welcome_item_template",
        "Welcome item template",
        "Welcome formatting",
        "Available field: {content}.",
    ),
    (
        "thread_heading_template",
        "Thread heading template",
        "Thread formatting",
        "Available field: {content}.",
    ),
    (
        "thread_container_template",
        "Thread block template",
        "Thread formatting",
        (
            "Fields: {headings}, {posts}, {separator}. "
            "Use \\n for line breaks."
        ),
    ),
    (
        "author_template",
        "Author line template",
        "Post formatting",
        "Fields: {marker}, {author}, {tags}, {original}.",
    ),
    (
        "tag_template",
        "Author tag template",
        "Post formatting",
        "Available field: {tag}.",
    ),
    (
        "post_meta_template",
        "Post date-line template",
        "Post formatting",
        (
            "Fields: {verb}, {on}, {timestamp}, {author}, "
            "{original}."
        ),
    ),
    (
        "timestamp_template",
        "Timestamp with tooltip",
        "Date formatting",
        (
            "Date fields plus {label}, {tooltip}, and "
            "{tooltip_attribute}."
        ),
    ),
    (
        "timestamp_without_tooltip_template",
        "Timestamp without tooltip",
        "Date formatting",
        "Date fields plus {label}.",
    ),
    (
        "quote_template",
        "Quoted-message template",
        "Post formatting",
        (
            "Fields: {author}, {attribution}, "
            "{attribution_attribute}, {body}."
        ),
    ),
    (
        "mention_template",
        "Mention marker",
        "Post formatting",
        "Replacement for @ in post bodies.",
    ),
    (
        "reply_quote_marker",
        "Reply quote marker",
        "Post formatting",
        "Used by the reply line template.",
    ),
    (
        "reply_line_template",
        "Reply line template",
        "Post formatting",
        "Fields: {marker}, {space}, {content}.",
    ),
    (
        "page_heading_template",
        "Page heading wrapper",
        "Pagination formatting",
        "Fields: {content}, {current}, {total}.",
    ),
    (
        "page_container_template",
        "Page posts template",
        "Pagination formatting",
        "Fields: {heading}, {posts}, {current}, {total}.",
    ),
    (
        "page_end_template",
        "Page ending wrapper",
        "Pagination formatting",
        (
            "Fields: {content}, {current}, {total}, "
            "{navigation}."
        ),
    ),
    (
        "navigation_current_template",
        "Current-page template",
        "Pagination formatting",
        "Available field: {page}.",
    ),
    (
        "navigation_link_template",
        "Other-page template",
        "Pagination formatting",
        "Available field: {page}.",
    ),
)


def style_options(defaults):
    return tuple(
        OptionField(
            key,
            label,
            default=defaults[key],
            description=description,
            section=section,
        )
        for key, label, section, description in (
            CONTENT_FIELDS + FORMAT_FIELDS
        )
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
            options=style_options(MARKDOWN_STYLE),
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
            options=style_options(BBCODE_STYLE),
            priority=100,
        )
    )

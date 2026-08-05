from manuskript.plugins.pho_pages.export_renderers import (
    BBCODE_STYLE,
    MARKDOWN_STYLE,
    PhoBBCodeRenderer,
    PhoMarkdownRenderer,
)
from manuskript.plugins.pho_pages.plugin import (
    CONTENT_FIELDS,
    FORMAT_FIELDS,
)
from manuskript.plugins.pho_pages.presentation import (
    PhoPresentationParser,
)


def bbcode_renderer():
    """Build the renderer the way register() does, with an injected markup.

    Tests may use core directly; plugin runtime code may not, which is why
    the renderer takes its converter as an argument.
    """
    from manuskript.plugins.capabilities import (
        CAPABILITY_MARKUP_BBCODE,
        grant,
    )

    granted, missing = grant([CAPABILITY_MARKUP_BBCODE])
    assert not missing, missing
    return PhoBBCodeRenderer(granted[CAPABILITY_MARKUP_BBCODE])


def render_pho_bbcode(source):
    """Replacement for the removed convert_pho_page helper."""
    from manuskript.plugins.pho_pages.model import PhoPage
    from manuskript.plugins.pho_pages.presentation import (
        PhoPresentationBuilder,
    )

    presentation = PhoPresentationBuilder().build(PhoPage.parse(source))
    return bbcode_renderer().render(presentation, "bbcode", {}).content


SOURCE = """PHO Interlude
SETTINGS\treader:Vaduz\tposts:7\tmessages:3\tdate:2011-02-04T12:00:00-05:00
WELCOME
USERS
Maven\ttag:Veteran Member
EOUSERS
THREAD
TOPIC\tA question
BOARD\tPlaces=>America
POSTER\tMaven
BOOP
Ask @Maven.
EOOP
REPLIES
Pyke\t+2m
------
@Maven>Quoted **reply**
EOREPLIES
EOTHREAD
EOPHO Interlude"""


def presentation():
    return PhoPresentationParser().parse(SOURCE)


def test_option_schema_covers_every_markdown_and_bbcode_setting():
    option_keys = {
        key for key, _label, _section, _description
        in CONTENT_FIELDS + FORMAT_FIELDS
    }

    assert option_keys == set(MARKDOWN_STYLE)
    assert option_keys == set(BBCODE_STYLE)


def test_presentation_keeps_counts_and_original_post_policy_semantic():
    model = presentation()
    original = model.threads[0].original_post

    assert model.posts_per_page == 7
    assert model.private_messages == 3
    assert original.original
    assert original.author.tags == ("Veteran Member",)


def test_markdown_renderer_applies_content_date_and_structure_options():
    rendered = PhoMarkdownRenderer().render(
        presentation(),
        "markdown",
        {
            "separator_template": "SEPARATOR<{separator}>",
            "welcome_title": "Custom forum",
            "logged_in_template": "SIGNED<{reader_name}>",
            "viewing_posts_per_page": "POSTS<{posts}>",
            "viewing_private_messages": "MESSAGES<{messages}>",
            "topic_template": "SUBJECT<{topic}>",
            "thread_heading_template": "HEADING<{content}>",
            "original_poster_label": "Thread starter",
            "tag_template": "TAG<{tag}>",
            "author_template": "AUTHOR<{author}|{tags}>",
            "posted_label": "Created",
            "on_label": "at",
            "date_template": "{year}/{month_padded}/{day_padded}",
            "post_meta_template": "META<{verb}|{on}|{timestamp}>",
            "page_heading_template": "PAGE<{content}>",
            "page_end_template": "ENDING<{content}>",
            "mention_template": "MENTION",
        },
    ).content

    assert "SEPARATOR<■>" in rendered
    assert "Custom forum" in rendered
    assert "SIGNED<Vaduz>" in rendered
    assert "POSTS<7>" in rendered
    assert "MESSAGES<3>" in rendered
    assert "HEADING<SUBJECT<A question>>" in rendered
    assert "AUTHOR<Maven|TAG<Thread starter>TAG<Veteran Member>>" in rendered
    assert "META<Created|at|2011/02/04>" in rendered
    assert "PAGE<Showing page 1 of 1>" in rendered
    assert "ENDING<End of Page. 1>" in rendered
    assert "Ask MENTIONMaven." in rendered


def test_bbcode_renderer_applies_its_own_quote_and_safety_templates():
    rendered = bbcode_renderer().render(
        presentation(),
        "bbcode",
        {
            "thread_heading_template": "BBCODE<{content}>",
            "date_template": "DATE<{iso}>",
            "timestamp_template": "STAMP<{label}|{tooltip}>",
            "quote_template": "QUOTE<{attribution}|{body}>",
            "said_template": "{author} wrote",
            "mention_template": "NO_PING",
        },
    ).content

    assert "BBCODE<♦ Topic: A question>" in rendered
    assert "STAMP<DATE<2011-02-04T" in rendered
    assert "QUOTE<Maven wrote|Quoted [b]reply[/b]>" in rendered
    assert "Ask NO_PINGMaven." in rendered
    assert "HEADING<" not in rendered


def test_default_bbcode_quote_has_real_attribute_quotes():
    rendered = bbcode_renderer().render(
        presentation(),
        "bbcode",
        {},
    ).content

    assert '[fieldset title="Maven said:"]' in rendered
    assert r'title=\"Maven said:\"' not in rendered

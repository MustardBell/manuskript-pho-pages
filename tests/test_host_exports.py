"""Host integration coverage owned by the PHO Pages plugin."""

from pathlib import Path
from types import SimpleNamespace

import markdown as markdown_library
import pytest

from manuskript.plugins.pho_pages.renderer import PhoPageRenderer
from manuskript.plugins.pho_pages.model import (
    PhoModelError,
    PhoPage,
)
from manuskript.plugins.pho_pages.export_renderers import (
    PhoBBCodeRenderer,
    PhoMarkdownRenderer,
)
from manuskript.plugins.pho_pages.presentation import (
    PhoPresentationParser,
)
from manuskript.converters.markdownToBBCode import markdown_to_bbcode
from manuskript.enums import Outline
from manuskript.exporter.manuskript.BBCode import BBCode
from manuskript.exporter.manuskript.HTML import HTML
from manuskript.models.outlineItem import outlineItem
from manuskript.plugins.runtime import PluginRuntime, PluginStatus
from manuskript.services.plugin_preferences import (
    InMemoryPluginPreferences,
)
from manuskript.services.plugin_options import InMemoryPluginOptionStore
from manuskript.ui.plugins.page_types import PageTypeService


PLUGIN_ROOT = Path(__file__).parents[2]


def pho_runtime():
    runtime = PluginRuntime(
        [PLUGIN_ROOT],
        InMemoryPluginPreferences(["manuskript.pho-pages"]),
    )
    runtime.discover()
    runtime.load_enabled()
    return runtime


def test_pho_plugin_does_not_register_a_bbcode_exporter():
    runtime = pho_runtime()

    record = runtime.records["manuskript.pho-pages"]
    assert record.status is PluginStatus.LOADED
    assert runtime.registry.converters == ()
    assert [
        value.descriptor.id for value in runtime.registry.page_types
    ] == ["manuskript.pho-page"]
    assert {
        value.descriptor.id for value in runtime.registry.page_renderers
    } == {
        "manuskript.pho-renderer.markdown",
        "manuskript.pho-renderer.bbcode",
    }


def test_generic_markdown_converts_to_forum_bbcode():
    converted = markdown_to_bbcode(
        "**Bold** and *italic* with [link](https://example.com)\n"
        "![alt](https://example.com/image.png)\n"
        "left -> right - aside"
    )

    assert "[b]Bold[/b]" in converted
    assert "[i]italic[/i]" in converted
    assert "[url=https://example.com]link[/url]" in converted
    assert "[img]https://example.com/image.png[/img]" in converted
    assert "left → right—aside" in converted


def test_unclosed_emphasis_cannot_consume_a_later_scene_break_heading():
    converted = markdown_to_bbcode(
        "An unfinished **emphasis marker.\n\n### ***"
    )

    assert "An unfinished **emphasis marker." in converted
    assert converted.endswith("[h3]***[/h3]")
    assert "[/b]*" not in converted


def test_emphasis_may_span_a_soft_line_but_not_a_paragraph_boundary():
    converted = markdown_to_bbcode(
        "**one\ntwo**\n\n*unfinished\n\nthen closed*"
    )

    assert "[b]one\ntwo[/b]" in converted
    assert "*unfinished\n\nthen closed*" in converted


def test_pho_interlude_directives_render_a_complete_thread():
    source = """Before
PHO Interlude
SETTINGS\treader:Vaduz\tposts:10\tdate:2011-02-04T12:00:00-05:00\tstartpage:1\trefer:1
WELCOME

USERS
Maven\taliasFor:Maven222\ttag:Veteran Member
Pyke\ttag:Verified Cape\ttag:Tinker
EOUSERS

THREAD
TOPIC\tSome topic
BOARD\tSome=>Board
POSTER\tMaven
BOOP
An **original** post
EOOP

REPLIES
Pyke\t+2m\t+0s\tid:first
------
Is it **PHO**, though?
*****
Lung\t+3m\t+0s\trefer:first
------
Ask @Pyke.
EOREPLIES
EOTHREAD

EOPHO Interlude
After
"""

    converted = render_pho_bbcode(source)

    assert "PHO Interlude" not in converted
    assert "EOPHO Interlude" not in converted
    assert "Before" in converted and "After" in converted
    assert "Welcome to the Parahumans Online message boards" in converted
    assert "[b]♦ Topic: Some topic[/b]" in converted
    assert "[b]In: Boards ► Some ► Board[/b]" in converted
    assert "[b]Maven222 [/b]" in converted
    assert "(Original Poster)" in converted
    assert "(Veteran Member)" in converted
    assert "[b]PHO[/b]" in converted
    assert "[b]►Divine_Carp [/b]" in converted
    assert "[plain]@[/plain]Pyke" in converted
    assert "[b](Showing page 1 of 1)[/b]" in converted
    assert "[CENTER]■[/CENTER]" in converted


def test_pho_page_renderer_processes_directives_before_rendering_html():
    source = """PHO Interlude
SETTINGS\treader:Vaduz\tposts:10\tdate:2011-02-04T12:00:00-05:00
WELCOME
THREAD
TOPIC\tA question
BOARD\tPlaces=>America
POSTER\tMaven
BOOP
An **original** post
EOOP
EOTHREAD
EOPHO Interlude"""

    rendered = PhoPageRenderer().render(
        PhoPresentationParser().parse(source)
    )

    assert "PHO Interlude" not in rendered.html
    assert "Welcome to the Parahumans Online message boards" in rendered.html
    assert "<strong>♦ Topic: A question</strong>" in rendered.html
    assert "Places ► America" in rendered.html
    assert render_pho_bbcode(source).startswith("[CENTER]")


def test_pho_semantics_render_portable_markdown_or_direct_safe_bbcode():
    source = """PHO Interlude
SETTINGS\treader:Vaduz\tposts:10\tdate:2011-02-04T12:00:00-05:00
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
Ask @Pyke.
EOREPLIES
EOTHREAD
EOPHO Interlude"""
    model = PhoPresentationParser().parse(source)

    markdown = PhoMarkdownRenderer().render(
        model,
        "markdown",
        {},
    ).content
    bbcode = bbcode_renderer().render(
        model,
        "bbcode",
        {},
    ).content

    assert "PHO Interlude" not in markdown
    assert "**♦ Topic: A question**" in markdown
    assert "Ask @Pyke." in markdown
    assert "PHO Interlude" not in bbcode
    assert "[b]♦ Topic: A question[/b]" in bbcode
    assert "Ask [plain]@[/plain]Pyke." in bbcode


def test_native_bbcode_export_only_delegates_pho_pages_to_plugin():
    runtime = pho_runtime()
    page_types = PageTypeService(runtime.registry)
    exporter = BBCode(SimpleNamespace(page_types=page_types))
    settings = {
        "Transform": {
            "Dash": False,
            "Ellipse": False,
            "Spaces": False,
            "Custom": [],
            "DoubleQuotes": "",
            "SingleQuote": "",
        }
    }

    ordinary = outlineItem(title="Markdown", _type="md")
    ordinary.setData(Outline.text, "An **ordinary** page")
    pho = outlineItem(title="Forum", _type="md")
    pho.setData(
        Outline.text,
        """PHO Interlude
SETTINGS\treader:Vaduz\tposts:10\tdate:2011-02-04T12:00:00-05:00
THREAD
TOPIC\tA question
BOARD\tPlaces=>America
POSTER\tMaven
BOOP
An **original** post
EOOP
EOTHREAD
EOPHO Interlude""",
    )

    assert exporter.processItemText(ordinary, settings) == (
        "An [b]ordinary[/b] page\n"
    )
    converted_pho = exporter.processItemText(pho, settings)
    assert "PHO Interlude" not in converted_pho
    assert "[b]♦ Topic: A question[/b]" in converted_pho
    assert "An [b]original[/b] post" in converted_pho


def test_native_html_pipeline_receives_semantic_markdown_not_directives():
    runtime = pho_runtime()
    page_types = PageTypeService(runtime.registry)
    exporter = HTML(SimpleNamespace(page_types=page_types))
    settings = {
        "Transform": {
            "Dash": False,
            "Ellipse": False,
            "Spaces": False,
            "Custom": [],
            "DoubleQuotes": "",
            "SingleQuote": "",
        }
    }
    pho = outlineItem(title="Forum", _type="md")
    pho.setData(
        Outline.text,
        """PHO Interlude
SETTINGS\treader:Vaduz\tposts:10\tdate:2011-02-04T12:00:00-05:00
THREAD
TOPIC\tA question
BOARD\tPlaces=>America
POSTER\tMaven
BOOP
An **original** post
EOOP
EOTHREAD
EOPHO Interlude""",
    )

    markdown = exporter.processItemText(pho, settings)

    assert "PHO Interlude" not in markdown
    assert "EOTHREAD" not in markdown
    assert "**♦ Topic: A question**" in markdown
    assert "An **original** post" in markdown
    html = markdown_library.markdown(markdown)
    assert "PHO Interlude" not in html
    assert "EOTHREAD" not in html
    assert "<strong>♦ Topic: A question</strong>" in html


def test_pho_output_renderers_have_independent_element_configuration():
    runtime = pho_runtime()
    options = InMemoryPluginOptionStore()
    options.save(
        "manuskript.pho-renderer.markdown",
        {"separator": "MARKDOWN-SEPARATOR"},
    )
    options.save(
        "manuskript.pho-renderer.bbcode",
        {"separator": "BBCODE-SEPARATOR"},
    )
    page_types = PageTypeService(runtime.registry, options)
    pho = outlineItem(title="Forum", _type="md")
    pho.setData(
        Outline.text,
        """PHO Interlude
SETTINGS\treader:Vaduz\tposts:10\tdate:2011-02-04T12:00:00-05:00
THREAD
TOPIC\tA question
BOARD\tPlaces=>America
POSTER\tMaven
BOOP
Ask @Maven.
EOOP
EOTHREAD
EOPHO Interlude""",
    )

    html_source = page_types.export_document(pho, "html")
    bbcode = page_types.export_document(pho, "bbcode")

    assert html_source.source_format == "markdown"
    assert "MARKDOWN-SEPARATOR" in html_source.content
    assert "BBCODE-SEPARATOR" not in html_source.content
    assert bbcode.source_format == "bbcode"
    assert "[CENTER]BBCODE-SEPARATOR[/CENTER]" in bbcode.content
    assert "[plain]@[/plain]Maven" in bbcode.content


def test_pho_page_model_round_trips_rich_directives_without_losing_text():
    source = """Before the forum
PHO Interlude
SETTINGS\treader:Vaduz\tposts:10\tdate:2011-02-04T12:00:00-05:00\trefer:1\tcustom:value
USERS
Maven\taliasFor:Maven222\ttag:Veteran Member
EOUSERS
THREAD
TOPIC\tSome topic
BOARD\tSome=>Board
POSTER\tMaven
BOOP
The post contains a literal directive-like line:
TOPIC\tThis is still post text
EOOP
REPLIES
Pyke\t+2m\tid:first
------
First reply
*****
Maven\t+14s\trefer:first
------
Second reply
EOREPLIES
EOTHREAD
EOPHO Interlude
After the forum"""

    page = PhoPage.parse(source)

    assert not page.welcome
    assert page.setting("custom") == "value"
    assert page.users_source.startswith("Maven\taliasFor")
    assert page.threads[0].topic == "Some topic"
    assert "TOPIC\tThis is still post text" in (
        page.threads[0].original_post
    )
    assert [reply.user for reply in page.threads[0].replies] == [
        "Pyke",
        "Maven",
    ]

    serialized = page.to_source()
    reparsed = PhoPage.parse(serialized)
    assert serialized.startswith("Before the forum\nPHO Interlude")
    assert serialized.endswith("\nAfter the forum")
    assert reparsed.settings == page.settings
    assert reparsed.threads[0].original_post == (
        page.threads[0].original_post
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
    assert render_pho_bbcode(serialized)


def test_pho_page_model_rejects_malformed_replies_before_editing():
    source = """PHO Interlude
SETTINGS\tdate:2011-02-04T12:00:00-05:00
THREAD
REPLIES
User without a separator
EOREPLIES
EOTHREAD
EOPHO Interlude"""

    with pytest.raises(PhoModelError, match="metadata"):
        PhoPage.parse(source)

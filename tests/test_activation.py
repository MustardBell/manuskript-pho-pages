from manuskript.plugins.pho_pages.model import (
    PhoPage,
    split_markdown_frontmatter,
)
from manuskript.plugins.pho_pages.plugin import activation_warning
from manuskript.plugins.pho_pages.presentation import (
    PhoPresentationParser,
)


YAML = """---
title: Forum scene
status: draft
---

"""


def test_blank_page_gets_a_virtual_pho_model_without_parser_errors():
    model = PhoPresentationParser().parse("")

    assert model.reader == "Reader"
    assert len(model.threads) == 1
    assert model.threads[0].original_post.body_markdown == ""
    assert activation_warning("") == ""


def test_frontmatter_only_page_counts_as_blank_and_is_preserved():
    prefix, body = split_markdown_frontmatter(YAML)
    page = PhoPage.initialize_from_markdown(YAML)
    model = PhoPresentationParser().parse(YAML)

    assert prefix == YAML
    assert body == ""
    assert page.prefix == YAML
    assert page.threads[0].original_post == ""
    assert model.prefix_markdown == YAML
    assert activation_warning(YAML) == ""


def test_existing_body_is_interpreted_as_original_post_after_warning():
    source = YAML + "Existing **Markdown** body."
    page = PhoPage.initialize_from_markdown(source)
    model = PhoPresentationParser().parse(source)

    assert page.prefix == YAML
    assert page.threads[0].original_post == (
        "Existing **Markdown** body."
    )
    assert model.prefix_markdown == YAML
    assert model.threads[0].original_post.body_markdown == (
        "Existing **Markdown** body."
    )
    assert "already contains body text" in activation_warning(source)


def test_existing_pho_source_needs_no_activation_warning():
    source = PhoPage.initialize("Post").to_source()

    assert activation_warning(source) == ""

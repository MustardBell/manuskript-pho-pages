"""End-to-end host page-type coverage for the PHO Pages plugin."""

from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import (
    QCheckBox,
    QApplication,
    QListWidget,
    QMessageBox,
)

from manuskript.enums import Outline
from manuskript.models.outlineItem import outlineItem
from manuskript.plugins import (
    ExtensionDescriptor,
    OptionField,
    PageExportDocument,
    PageRendererContribution,
    PageTypeContribution,
)
from manuskript.plugins.registry import PluginRegistry
from manuskript.services.plugin_options import InMemoryPluginOptionStore
from manuskript.ui.editors.markdownPresentation import (
    MarkdownPresentationMode,
)
from manuskript.ui.plugins.page_types import PageTypeService
from manuskript.ui.views.propertiesView import propertiesView
from manuskript.media_types import BBCODE, HTML, MARKDOWN


class Parser:
    def parse(self, source):
        return "PHO:" + source


class Renderer:
    def render(self, model, target_format, options):
        return PageExportDocument(model, target_format)


def make_service(activation_warning=None, source_provider=None):
    contribution = PageTypeContribution(
        ExtensionDescriptor("example.pho", "PHO"),
        "PHO page",
        detector=lambda source: source.startswith("PHO Interlude"),
        parser_factory=Parser,
        renderer_factory=object,
        wizard_factory=object,
        activation_warning=activation_warning,
    )
    renderer = PageRendererContribution(
        ExtensionDescriptor("example.pho-renderer", "PHO renderer"),
        page_type_id="example.pho",
        renderer_factory=Renderer,
        target_formats=(BBCODE, MARKDOWN),
    )
    registry = PluginRegistry()
    registrar = registry.registrar("example.plugin")
    registrar.register_page_type(contribution)
    registrar.register_page_renderer(renderer)
    registry.install("example.plugin", registrar.contributions)
    return (
        PageTypeService(
            registry,
            InMemoryPluginOptionStore(),
            source_provider=source_provider,
        ),
        contribution,
    )


def test_detected_page_type_can_be_explicitly_disabled():
    service, contribution = make_service()
    item = outlineItem(title="PHO", _type="md")
    item.setData(Outline.text, "PHO Interlude\nEOPHO Interlude")

    assert service.is_enabled(item, contribution)

    service.set_enabled(item, contribution, False)

    assert not service.is_enabled(item, contribution)


def test_page_type_activation_warns_before_committing_checkbox(
        monkeypatch):
    seen_sources = []
    service, contribution = make_service(
        activation_warning=lambda source: (
            seen_sources.append(source)
            or "Existing body text will be reinterpreted."
        ),
        source_provider=lambda _item: "live unsaved body",
    )
    item = outlineItem(title="Ordinary", _type="md")
    item.setData(Outline.text, "stale submitted body")
    view = propertiesView()
    view.setPageTypeService(service)
    view._currentPropertyItems = (item,)
    view._syncPluginProperties()
    checkbox = view.findChild(
        QCheckBox,
        "pluginPropertyexample_pho",
    )
    answers = iter((QMessageBox.Cancel, QMessageBox.Yes))
    shown = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda _parent, title, message, *_args: (
            shown.append((title, message))
            or next(answers)
        ),
    )

    checkbox.setChecked(True)

    assert not service.is_enabled(item, contribution)
    assert not checkbox.isChecked()

    checkbox.setChecked(True)

    assert service.is_enabled(item, contribution)
    assert checkbox.isChecked()
    assert seen_sources == ["live unsaved body", "live unsaved body"]
    assert shown == [
        ("Enable PHO page?", "Existing body text will be reinterpreted."),
        ("Enable PHO page?", "Existing body text will be reinterpreted."),
    ]


def test_active_page_type_owns_reading_live_and_export_behavior():
    service, contribution = make_service()
    item = outlineItem(title="PHO", _type="md")
    item.setData(Outline.text, "ordinary source")
    service.set_enabled(item, contribution, True)
    state = service.create_state(item)

    assert state.allowed_presentation_modes == (
        MarkdownPresentationMode.SOURCE,
        MarkdownPresentationMode.LIVE_PREVIEW,
        MarkdownPresentationMode.READING,
    )
    assert service.export_document(item, BBCODE) == (
        PageExportDocument("PHO:ordinary source", BBCODE)
    )


def test_page_renderer_uses_markdown_fallback_until_an_exact_route_is_selected():
    service, contribution = make_service()
    item = outlineItem(title="PHO", _type="md")
    item.setData(Outline.text, "ordinary source")
    service.set_enabled(item, contribution, True)

    fallback = service.export_document(item, HTML)

    assert fallback == PageExportDocument(
        "PHO:ordinary source",
        MARKDOWN,
    )

    class HtmlRenderer:
        def render(self, model, target_format, options):
            return PageExportDocument(
                '<section data-style="{}">{}</section>'.format(
                    options["style"],
                    model,
                ),
                target_format,
            )

    html_renderer = PageRendererContribution(
        ExtensionDescriptor(
            "another.pho-html",
            "Alternate PHO HTML",
        ),
        page_type_id="example.pho",
        renderer_factory=HtmlRenderer,
        target_formats=(HTML,),
        options=(OptionField("style", "Style", default="classic"),),
    )
    registrar = service.registry.registrar("another.plugin")
    registrar.register_page_renderer(html_renderer)
    service.registry.install("another.plugin", registrar.contributions)
    service.option_store.save(
        "another.pho-html",
        {"style": "custom"},
    )
    service.select_renderer(
        "example.pho",
        "html:html",
        "another.pho-html",
        representation_format=HTML,
    )

    rendered = service.export_document(
        item,
        HTML,
        route_id="html:html",
    )

    assert service.selected_renderer_id(
        "example.pho",
        "html:html",
    ) == "another.pho-html"
    assert rendered == PageExportDocument(
        '<section data-style="custom">PHO:ordinary source</section>',
        HTML,
    )


def test_pho_property_and_reading_projection_are_item_scoped(
        MWEmptyProject):
    window = MWEmptyProject
    plugin_id = "manuskript.pho-pages"
    was_enabled = (
        plugin_id
        in window.pluginRuntime.preferences.enabled_plugin_ids
    )
    if not was_enabled:
        window.pluginRuntime.enable(plugin_id)
        window.pluginUi.refresh_contributions()
    window.resize(960, 720)
    window.show()
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
REPLIES
Pyke\t+2m\tid:first
------
First reply
*****
Maven\t+1m\trefer:first
------
Second reply
EOREPLIES
EOTHREAD
EOPHO Interlude"""
    pho = outlineItem(title="PHO", _type="md")
    pho.setData(Outline.text, source)
    ordinary = outlineItem(title="Ordinary", _type="md")
    ordinary.setData(Outline.text, "An **ordinary** page")
    window.mdlOutline.appendItem(pho)
    window.mdlOutline.appendItem(ordinary)
    try:
        index = window.mdlOutline.indexFromItem(pho)
        window.mainEditor.setCurrentModelIndex(index, newTab=True)
        window.mainEditor.tabChanged()
        QApplication.processEvents()
        editor = window.mainEditor.currentEditor()

        assert editor.pageType.is_active
        assert editor.markdownPresentation.allowed_modes == (
            MarkdownPresentationMode.SOURCE,
            MarkdownPresentationMode.LIVE_PREVIEW,
            MarkdownPresentationMode.READING,
        )
        assert (
            editor.markupProfileButton is None
            or not editor.markupProfileButton.isVisible()
        )

        properties = window.redacMetadata.properties
        checkbox = properties.findChild(
            QCheckBox,
            "pluginPropertymanuskript_pho-page",
        )
        assert checkbox is not None
        assert checkbox.isChecked()

        canonical_document = editor.txtRedacText.document()
        editor.markdownPresentation.set_mode(
            MarkdownPresentationMode.READING
        )
        QApplication.processEvents()
        reading = editor.markdownEditorHost.readingView
        reading.refresh()

        assert reading.isReadOnly()
        assert "Welcome to the Parahumans Online" in reading.toPlainText()
        assert "Topic: A question" in reading.toPlainText()
        assert "PHO Interlude" not in reading.toPlainText()
        assert editor.txtRedacText.document() is canonical_document
        assert editor.txtRedacText.toPlainText() == source
        assert pho.text() == source

        editor.markdownPresentation.set_mode(
            MarkdownPresentationMode.LIVE_PREVIEW
        )
        QApplication.processEvents()
        wizard = editor.markdownEditorHost.pageWizard
        assert not hasattr(wizard.view, "page")
        assert wizard.controller.page is not None
        reply_list = wizard.findChild(
            QListWidget,
            "phoWizardReplyList",
        )
        assert reply_list is not None
        assert reply_list.dragDropMode() == reply_list.InternalMove
        reply_list.setCurrentRow(1)
        wizard.view.replyBodyEdit.setPlainText(
            "Edited only in the wizard"
        )
        moved = reply_list.model().moveRow(
            QModelIndex(),
            1,
            QModelIndex(),
            0,
        )
        assert moved

        # Selecting, editing and dragging affect only the wizard model.
        assert editor.txtRedacText.toPlainText() == source
        assert pho.text() == source

        wizard.view.applyButton.click()
        QApplication.processEvents()
        applied = pho.text()
        assert applied != source
        assert "Edited only in the wizard" in applied
        assert applied.index("Maven\t+1m") < applied.index("Pyke\t+2m")

        # The host owns the canonical document replacement as one undo step.
        editor.txtRedacText.undo()
        editor.txtRedacText.submit()
        assert editor.txtRedacText.toPlainText() == source
        assert pho.text() == source

        checkbox.setChecked(False)
        QApplication.processEvents()
        assert not editor.pageType.is_active
        assert tuple(editor.markdownPresentation.allowed_modes) == tuple(
            MarkdownPresentationMode
        )
        assert ordinary.pluginData() == {}
    finally:
        window.mainEditor.closeAllTabs()
        window.hide()
        if not was_enabled:
            window.pluginRuntime.disable(plugin_id)
            window.pluginUi.refresh_contributions()


def test_pho_checkbox_handles_blank_frontmatter_and_live_body_text(
        MWEmptyProject, monkeypatch):
    window = MWEmptyProject
    plugin_id = "manuskript.pho-pages"
    was_enabled = (
        plugin_id
        in window.pluginRuntime.preferences.enabled_plugin_ids
    )
    if not was_enabled:
        window.pluginRuntime.enable(plugin_id)
        window.pluginUi.refresh_contributions()
    item = outlineItem(title="New PHO page", _type="md")
    item.setData(Outline.text, "")
    window.mdlOutline.appendItem(item)
    warnings = []
    answer = [QMessageBox.Cancel]
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda _parent, title, message, *_args: (
            warnings.append((title, message))
            or answer[0]
        ),
    )
    try:
        index = window.mdlOutline.indexFromItem(item)
        window.mainEditor.setCurrentModelIndex(index, newTab=True)
        window.mainEditor.tabChanged()
        QApplication.processEvents()
        editor = window.mainEditor.currentEditor()
        checkbox = window.redacMetadata.properties.findChild(
            QCheckBox,
            "pluginPropertymanuskript_pho-page",
        )

        checkbox.setChecked(True)
        QApplication.processEvents()

        assert warnings == []
        assert checkbox.isChecked()
        assert editor.pageType.is_active
        assert editor.txtRedacText.toPlainText() == ""

        editor.markdownPresentation.set_mode(
            MarkdownPresentationMode.READING
        )
        QApplication.processEvents()
        editor.markdownEditorHost.readingView.refresh()
        assert not editor.txtRedacText._readingRenderer.failed

        checkbox.setChecked(False)
        editor.markdownPresentation.set_mode(
            MarkdownPresentationMode.SOURCE
        )
        frontmatter = "---\ntitle: Forum scene\n---\n\n"
        editor.txtRedacText.setPlainText(frontmatter)
        checkbox.setChecked(True)
        QApplication.processEvents()

        assert warnings == []
        assert checkbox.isChecked()
        assert editor.txtRedacText.toPlainText() == frontmatter

        checkbox.setChecked(False)
        source = frontmatter + "Existing **Markdown** body."
        editor.txtRedacText.setPlainText(source)
        checkbox.setChecked(True)
        QApplication.processEvents()

        assert len(warnings) == 1
        assert "already contains body text" in warnings[0][1]
        assert not checkbox.isChecked()
        assert not editor.pageType.is_active
        assert editor.txtRedacText.toPlainText() == source

        answer[0] = QMessageBox.Yes
        checkbox.setChecked(True)
        QApplication.processEvents()

        assert len(warnings) == 2
        assert checkbox.isChecked()
        assert editor.pageType.is_active
        assert editor.txtRedacText.toPlainText() == source

        editor.markdownPresentation.set_mode(
            MarkdownPresentationMode.READING
        )
        QApplication.processEvents()
        reading = editor.markdownEditorHost.readingView
        reading.refresh()
        assert "Existing Markdown body." in reading.toPlainText()
        assert not editor.txtRedacText._readingRenderer.failed
    finally:
        window.mainEditor.closeAllTabs()
        window.hide()
        if not was_enabled:
            window.pluginRuntime.disable(plugin_id)
            window.pluginUi.refresh_contributions()

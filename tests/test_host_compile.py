#!/usr/bin/env python
# --!-- coding: utf8 --!--

"""Compile-pipeline integration coverage for PHO Pages."""

from manuskript.plugins.api import (
    ConversionArtifact,
    ConversionContribution,
    ExtensionDescriptor,
)
from manuskript.enums import Outline
from manuskript.models.outlineItem import outlineItem
from manuskript.ui.plugins.export_adapter import (
    PluginConversionExportFormat,
)

def test_export_dialog_loads_manager_and_restores_format(
        MWSampleProject):
    """
    Simply tests that export widget loads properly.
    """
    MW = MWSampleProject

    # Loading from mainWindow
    MW.doCompile()
    E = MW.dialog
    assert E.isVisible()
    available_formats = []
    for index in range(E.cmbExporters.count()):
        E.cmbExporters.setCurrentIndex(index)
        selected_exporter, selected_format = E.getSelectedExporter()
        if (
            selected_exporter
            and selected_format
            and selected_format.implemented
        ):
            available_formats.append(
                (
                    index,
                    selected_exporter.name,
                    selected_format.name,
                )
            )
    assert available_formats
    selected_index, exporter_name, format_name = (
        available_formats[-1]
    )
    E.cmbExporters.setCurrentIndex(selected_index)
    assert MW.applicationPreferences.last_exporter == exporter_name
    assert MW.applicationPreferences.last_export_format == format_name
    E.hide()

    # Load exporter manager
    E.openManager()
    EM = E.dialog
    assert EM.isVisible()
    EM.updateUi("Manuskript")
    EM.updateFormatDescription("OPML")
    assert EM.lblExportToDescription.text() == "<b>OPML:</b> "
    EM.hide()

    EM.close()
    E.close()

    MW.doCompile()
    restored = MW.dialog
    selected_exporter, selected_format = (
        restored.getSelectedExporter()
    )
    assert selected_exporter.name == exporter_name
    assert selected_format.name == format_name
    restored.close()


def test_plugin_conversion_target_uses_the_compile_dialog(
        MWSampleProject):
    class Converter:
        def convert(
                self, content, source_format, target_format, options):
            return ConversionArtifact(
                "converted:{}".format(content),
                "compiled.bbcode",
                "text/plain",
            )

    window = MWSampleProject
    registry = window.pluginRuntime.registry
    registrar = registry.registrar("test.compile-converter")
    registrar.register_converter(
        ConversionContribution(
            ExtensionDescriptor(
                "test.compile-converter.bbcode",
                "Plugin BBCode",
                extensions=(".bbcode",),
            ),
            Converter,
            source_formats=("markdown",),
            target_formats=("bbcode",),
        )
    )
    registry.install(
        "test.compile-converter",
        registrar.contributions,
    )
    try:
        window.doCompile()
        dialog = window.dialog
        index = next(
            index
            for index in range(dialog.cmbExporters.count())
            if dialog.cmbExporters.itemText(index) == "Plugin BBCode"
        )

        dialog.cmbExporters.setCurrentIndex(index)
        _exporter, output_format = dialog.getSelectedExporter()

        assert isinstance(output_format, PluginConversionExportFormat)
        assert dialog.settingsWidget.sourceSettings is not None
        dialog.preview()
        assert dialog.previewWidget.toPlainText().startswith(
            "converted:"
        )
    finally:
        window.dialog.close()
        registry.remove_plugin("test.compile-converter")


def test_native_bbcode_is_a_usable_compile_target(
        MWSampleProject):
    window = MWSampleProject
    window.doCompile()
    dialog = window.dialog
    try:
        index = next(
            index
            for index in range(dialog.cmbExporters.count())
            if dialog.cmbExporters.itemText(index)
            == "BBCode"
        )

        dialog.cmbExporters.setCurrentIndex(index)
        exporter, output_format = dialog.getSelectedExporter()

        assert exporter.name == "Manuskript"
        assert output_format.isValid()
        assert output_format.format_id == "bbcode"
        dialog.preview()
        assert dialog.previewWidget.toPlainText()
    finally:
        dialog.close()


def test_compile_previews_route_pho_to_bbcode_or_semantic_html(
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
    ordinary = outlineItem(title="Scene break", _type="md")
    ordinary.setData(
        Outline.text,
        "An unfinished **emphasis marker.\n\n### ***",
    )
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
    window.mdlOutline.appendItem(ordinary)
    window.mdlOutline.appendItem(pho)
    window.doCompile()
    dialog = window.dialog
    try:
        bbcode_index = next(
            index
            for index in range(dialog.cmbExporters.count())
            if dialog.cmbExporters.itemText(index) == "BBCode"
            and dialog.cmbExporters.itemData(index) == "Manuskript"
        )
        dialog.cmbExporters.setCurrentIndex(bbcode_index)
        dialog.preview()
        bbcode = dialog.previewWidget.toPlainText()

        assert "PHO Interlude" not in bbcode
        assert "[b]♦ Topic: A question[/b]" in bbcode
        assert "[plain]@[/plain]Maven" in bbcode
        assert "[h3]***[/h3]" in bbcode
        assert "[/b]*" not in bbcode

        html_index = next(
            index
            for index in range(dialog.cmbExporters.count())
            if dialog.cmbExporters.itemText(index) == "HTML"
            and dialog.cmbExporters.itemData(index) == "Manuskript"
        )
        dialog.cmbExporters.setCurrentIndex(html_index)
        dialog.preview()
        markdown_source = dialog.previewWidget.widget(0).toPlainText()
        html_source = dialog.previewWidget.widget(1).toPlainText()

        assert "PHO Interlude" not in markdown_source
        assert "EOTHREAD" not in markdown_source
        assert "**♦ Topic: A question**" in markdown_source
        assert "PHO Interlude" not in html_source
        assert "EOTHREAD" not in html_source
        assert "<strong>♦ Topic: A question</strong>" in html_source
    finally:
        dialog.close()
        if not was_enabled:
            window.pluginRuntime.disable(plugin_id)
            window.pluginUi.refresh_contributions()

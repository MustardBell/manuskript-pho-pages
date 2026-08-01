"""Plugin-manager integration coverage for PHO Pages."""

import json
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from manuskript.plugins.runtime import PluginRuntime, PluginStatus
from manuskript.services.plugin_preferences import (
    InMemoryPluginPreferences,
)
from manuskript.services.plugin_options import InMemoryPluginOptionStore
from manuskript.exporter.page_routes import PageRendererRoute
from manuskript.tests.plugins.test_runtime import create_plugin
from manuskript.ui.plugins.manager import PluginManagerDialog
from manuskript.ui.plugins.page_types import PageTypeService


def test_manager_discovers_disabled_plugin_without_loading_it(
        tmp_path):
    create_plugin(tmp_path)
    runtime = PluginRuntime(
        [tmp_path],
        InMemoryPluginPreferences(),
    )

    dialog = PluginManagerDialog(runtime)

    assert dialog.pluginList.topLevelItemCount() == 1
    assert (
        runtime.records["example.plugin"].status
        is PluginStatus.DISABLED
    )
    assert runtime.registry.exporters == ()


def test_manager_enables_and_disables_selected_plugin(
        tmp_path, monkeypatch):
    create_plugin(tmp_path)
    runtime = PluginRuntime(
        [tmp_path],
        InMemoryPluginPreferences(),
    )
    dialog = PluginManagerDialog(runtime)
    monkeypatch.setattr(
        dialog,
        "_confirm_enable",
        lambda _plugin_id: True,
    )
    changes = []
    dialog.pluginsChanged.connect(lambda: changes.append(True))

    dialog.enable_selected()

    assert (
        runtime.records["example.plugin"].status
        is PluginStatus.LOADED
    )
    assert len(runtime.registry.exporters) == 1

    dialog.disable_selected()

    assert (
        runtime.records["example.plugin"].status
        is PluginStatus.DISABLED
    )
    assert runtime.registry.exporters == ()
    assert changes == [True, True]


def test_manager_reports_invalid_manifests(tmp_path):
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "plugin.json").write_text(
        json.dumps({
            "id": "../escape",
            "name": "Broken",
            "version": "1.0",
            "api_version": 1,
            "entry_point": "plugin:register",
        }),
        encoding="utf-8",
    )
    runtime = PluginRuntime(
        [tmp_path],
        InMemoryPluginPreferences(),
    )

    dialog = PluginManagerDialog(runtime)

    assert "Discovery problems" in dialog.discoveryLabel.text()
    assert "Invalid plugin ID" in dialog.discoveryLabel.text()


def test_preinstalled_plugin_can_be_enabled_and_disabled(monkeypatch):
    plugin_root = Path(__file__).parents[2]
    preferences = InMemoryPluginPreferences()
    runtime = PluginRuntime(
        [plugin_root],
        preferences,
    )
    runtime.discover()
    runtime.load_enabled()

    dialog = PluginManagerDialog(runtime)
    monkeypatch.setattr(
        dialog,
        "_confirm_enable",
        lambda _plugin_id: True,
    )

    assert "Installed plugin" in dialog.metadataLabel.text()
    assert dialog.enableButton.isEnabled()
    assert not dialog.disableButton.isEnabled()

    dialog.enable_selected()

    assert runtime.records["manuskript.pho-pages"].status is PluginStatus.LOADED
    assert preferences.enabled_plugin_ids == ("manuskript.pho-pages",)
    assert dialog.disableButton.isEnabled()

    dialog.disable_selected()

    assert runtime.records["manuskript.pho-pages"].status is PluginStatus.DISABLED
    assert preferences.enabled_plugin_ids == ()


def test_manager_exposes_page_renderer_routes_without_another_tools_menu():
    plugin_root = Path(__file__).parents[2]
    runtime = PluginRuntime(
        [plugin_root],
        InMemoryPluginPreferences(["manuskript.pho-pages"]),
    )
    runtime.discover()
    runtime.load_enabled()
    option_store = InMemoryPluginOptionStore()
    page_types = PageTypeService(runtime.registry, option_store)

    dialog = PluginManagerDialog(
        runtime,
        option_store=option_store,
        page_types=page_types,
        export_routes_provider=lambda: (
            PageRendererRoute(
                "bbcode:bbcode",
                "BBCode",
                "bbcode",
                "bbcode",
                "Manuskript",
            ),
            PageRendererRoute(
                "html:html",
                "HTML",
                "html",
                "html",
                "Manuskript",
            ),
        ),
    )

    assert not dialog.rendererGroup.isHidden()
    assert dialog.pageTypeCombo.currentData() == "manuskript.pho-page"

    dialog.renderTargetCombo.setCurrentIndex(
        dialog.renderTargetCombo.findData("html:html")
    )
    assert dialog.pageRendererCombo.currentData() == (
        "manuskript.pho-renderer.markdown"
    )
    assert "compatible fallback" in (
        dialog.pageRendererCombo.currentText()
    )

    dialog.renderTargetCombo.setCurrentIndex(
        dialog.renderTargetCombo.findData("bbcode:bbcode")
    )
    assert dialog.pageRendererCombo.currentData() == (
        "manuskript.pho-renderer.bbcode"
    )
    assert "compatible fallback" not in (
        dialog.pageRendererCombo.currentText()
    )
    assert dialog.configureRendererButton.isEnabled()


def test_manager_details_scroll_instead_of_clipping_renderer_controls():
    plugin_root = Path(__file__).parents[2]
    runtime = PluginRuntime(
        [plugin_root],
        InMemoryPluginPreferences(["manuskript.pho-pages"]),
    )
    runtime.discover()
    runtime.load_enabled()
    option_store = InMemoryPluginOptionStore()
    dialog = PluginManagerDialog(
        runtime,
        option_store=option_store,
        page_types=PageTypeService(runtime.registry, option_store),
        export_routes_provider=lambda: (
            PageRendererRoute(
                "plain:plain",
                "Plain text",
                "plain",
                "markdown",
                "Manuskript",
            ),
        ),
    )

    assert dialog.width() >= 960
    assert dialog.height() >= 700
    assert dialog.minimumWidth() == 720
    assert dialog.minimumHeight() == 520
    assert dialog.detailsScroll.widget() is dialog.detailsWidget

    dialog.resize(dialog.minimumSize())
    dialog.show()
    QApplication.processEvents()

    assert dialog.rendererGroup.isVisible()
    assert dialog.configureRendererButton.isVisible()
    assert dialog.rendererInfoLabel.text()
    assert dialog.detailsScroll.verticalScrollBar().maximum() > 0


def test_application_manager_uses_the_live_compile_exporter_catalog(
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
    routes = window.pluginUi._export_routes()

    window.pluginUi.show_manager()
    dialog = window.pluginUi.manager
    try:
        displayed = [
            (
                dialog.renderTargetCombo.itemText(index),
                dialog.renderTargetCombo.itemData(index),
            )
            for index in range(dialog.renderTargetCombo.count())
        ]

        assert displayed == [
            (route.label, route.id) for route in routes
        ]
        assert ("BBCode", "bbcode:bbcode") in displayed
        assert all(label != "bbcode" for label, _route in displayed)
    finally:
        dialog.close()
        if not was_enabled:
            window.pluginRuntime.disable(plugin_id)
            window.pluginUi.refresh_contributions()

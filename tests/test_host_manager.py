"""Plugin-manager integration coverage for PHO Pages."""

import json
from pathlib import Path

from manuskript.plugins.runtime import PluginRuntime, PluginStatus
from manuskript.services.plugin_preferences import (
    InMemoryPluginPreferences,
)
from manuskript.services.plugin_options import InMemoryPluginOptionStore
from manuskript.exporter.page_routes import PageRendererRoute
from manuskript.tests.plugins.test_runtime import create_plugin
from manuskript.plugins.api import PluginSettingsContext
from manuskript.ui.plugins.manager import PluginManagerDialog
from manuskript.ui.plugins.page_routing import PageRoutingGateway
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


PHO_ID = "manuskript.pho-pages"
ROUTES = (
    PageRendererRoute(
        "plain:markdown", "Plain text", "plain", "markdown", "Manuskript",
    ),
    PageRendererRoute(
        "bbcode:bbcode", "BBCode", "bbcode", "bbcode", "Manuskript",
    ),
)


def pho_runtime():
    runtime = PluginRuntime(
        [Path(__file__).parents[2]],
        InMemoryPluginPreferences([PHO_ID]),
    )
    runtime.discover()
    runtime.load_enabled()
    return runtime


def pho_panel(runtime, store):
    """Build PHO's own settings widget the way the manager would."""
    page_types = PageTypeService(runtime.registry, store)
    context = PluginSettingsContext(
        plugin_id=PHO_ID,
        page_routing=PageRoutingGateway(
            PHO_ID, runtime.registry, page_types, lambda: ROUTES,
        ),
        option_store=store,
        edit_options=lambda *a, **k: None,
        show_status=lambda *a, **k: None,
    )
    record = runtime.registry.plugin_records(PHO_ID, "settings_panel")[0]
    return record.contribution.widget_factory(context, None), context


def test_pho_registers_its_own_settings_panel():
    runtime = pho_runtime()

    records = runtime.registry.plugin_records(PHO_ID, "settings_panel")

    assert [record.id for record in records] == ["manuskript.pho-settings"]


def test_panel_offers_one_renderer_choice_per_export_format():
    runtime = pho_runtime()
    panel, _context = pho_panel(runtime, InMemoryPluginOptionStore())

    assert set(panel._combos) == {"plain:markdown", "bbcode:bbcode"}
    assert panel._combos["bbcode:bbcode"].currentData() == (
        "manuskript.pho-renderer.bbcode"
    )
    plain = panel._combos["plain:markdown"]
    assert plain.currentData() == "manuskript.pho-renderer.markdown"
    assert "compatible fallback" not in plain.currentText()


def test_panel_saves_the_chosen_renderer():
    runtime = pho_runtime()
    store = InMemoryPluginOptionStore()
    panel, context = pho_panel(runtime, store)
    combo = panel._combos["bbcode:bbcode"]

    combo.setCurrentIndex(
        combo.findData("manuskript.pho-renderer.markdown")
    )

    assert context.page_routing.selected(
        "manuskript.pho-page", "bbcode:bbcode"
    ) == "manuskript.pho-renderer.markdown"


def test_panel_cannot_route_a_page_type_pho_does_not_own():
    runtime = pho_runtime()
    _panel, context = pho_panel(runtime, InMemoryPluginOptionStore())

    assert not context.page_routing.owns("someone.else-page")


def test_manager_shows_the_pho_panel_only_under_pho(MWEmptyProject):
    window = MWEmptyProject
    was_enabled = (
        PHO_ID in window.pluginRuntime.preferences.enabled_plugin_ids
    )
    if not was_enabled:
        window.pluginRuntime.enable(PHO_ID)
        window.pluginUi.refresh_contributions()

    window.pluginUi.show_manager()
    dialog = window.pluginUi.manager
    try:
        from PyQt5.QtCore import Qt

        for index in range(dialog.pluginList.topLevelItemCount()):
            item = dialog.pluginList.topLevelItem(index)
            plugin_id = item.data(0, Qt.UserRole)
            dialog.pluginList.setCurrentItem(item)
            has_panel = dialog.pluginPanels.get(plugin_id) is not None
            assert has_panel == (plugin_id == PHO_ID), plugin_id
    finally:
        dialog.close()
        if not was_enabled:
            window.pluginRuntime.disable(PHO_ID)
            window.pluginUi.refresh_contributions()

"""Plugin-manager integration coverage for PHO Pages."""

import json

import pytest
from pathlib import Path

from manuskript.exporter.page_routes import page_renderer_route_id
from manuskript.media_types import BBCODE, MARKDOWN, PLAIN
PLAIN_ROUTE = page_renderer_route_id(PLAIN, MARKDOWN)
BBCODE_ROUTE = page_renderer_route_id(BBCODE, BBCODE)
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
from manuskript.ui.plugins.routing_panel import ExportRoutingService
from manuskript.plugins.capabilities import (
    CAPABILITY_UI_EXPORT_ROUTING,
)
from manuskript.plugins.errors import PluginScopeError


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
        PLAIN_ROUTE, "Plain text", PLAIN, MARKDOWN, "Manuskript",
    ),
    PageRendererRoute(
        BBCODE_ROUTE, "BBCode", BBCODE, BBCODE, "Manuskript",
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
    """Build PHO's own settings widget the way the manager would.

    Core no longer pushes a routing gateway at every panel, so this stands
    in for the host: it serves ui.export_routing because PHO's manifest
    declares it, and refuses anything else.
    """
    page_types = PageTypeService(runtime.registry, store)
    gateway = PageRoutingGateway(
        PHO_ID, runtime.registry, page_types, lambda: ROUTES,
    )

    def capability(name):
        if name not in runtime.records[PHO_ID].manifest.requires:
            raise PluginScopeError("PHO did not declare {!r}".format(name))
        if name != CAPABILITY_UI_EXPORT_ROUTING:
            raise PluginScopeError("Not a panel service: {!r}".format(name))
        return ExportRoutingService(gateway)

    context = PluginSettingsContext(
        plugin_id=PHO_ID,
        option_store=store,
        edit_options=lambda *a, **k: None,
        show_status=lambda *a, **k: None,
        capability=capability,
    )
    record = runtime.registry.plugin_records(PHO_ID, "settings_panel")[0]
    return record.contribution.widget_factory(context, None), gateway


def test_pho_registers_its_own_settings_panel():
    runtime = pho_runtime()

    records = runtime.registry.plugin_records(PHO_ID, "settings_panel")

    assert [record.id for record in records] == ["manuskript.pho-settings"]


def test_panel_offers_one_renderer_choice_per_export_format():
    runtime = pho_runtime()
    panel, _gateway = pho_panel(runtime, InMemoryPluginOptionStore())

    # PHO renders BBCode natively and Markdown natively, and every other
    # destination just takes the Markdown as the scene's own text. So there
    # is exactly one decision to make, and only it gets a row.
    assert set(panel._combos) == {BBCODE_ROUTE}

    bbcode = panel._combos[BBCODE_ROUTE]
    assert bbcode.currentData() == ""
    assert bbcode.itemText(0) == "Automatic — PHO forum BBCode"
    assert [
        bbcode.itemData(index) for index in range(bbcode.count())
    ] == [
        "",
        "manuskript.pho-renderer.bbcode",
        "manuskript.pho-renderer.markdown",
    ]

    # Everything else is one line naming the renderer once.
    assert panel.noticeLabel.text() == (
        "PHO portable Markdown: Plain text"
    )


def test_panel_saves_the_chosen_renderer():
    runtime = pho_runtime()
    store = InMemoryPluginOptionStore()
    panel, gateway = pho_panel(runtime, store)
    combo = panel._combos[BBCODE_ROUTE]

    combo.setCurrentIndex(
        combo.findData("manuskript.pho-renderer.markdown")
    )

    assert gateway.selected(
        "manuskript.pho-page", BBCODE_ROUTE
    ) == "manuskript.pho-renderer.markdown"


def test_panel_cannot_route_a_page_type_pho_does_not_own():
    runtime = pho_runtime()
    _panel, gateway = pho_panel(runtime, InMemoryPluginOptionStore())

    assert not gateway.owns("someone.else-page")


def test_pho_only_gets_the_services_its_manifest_declares():
    runtime = pho_runtime()
    store = InMemoryPluginOptionStore()
    _panel, _gateway = pho_panel(runtime, store)
    record = runtime.registry.plugin_records(PHO_ID, "settings_panel")[0]

    # A panel that asked for something undeclared is refused by the host,
    # not trusted to behave.
    class Undeclared:
        plugin_id = PHO_ID
        option_store = store
        edit_options = staticmethod(lambda *a, **k: None)
        show_status = staticmethod(lambda *a, **k: None)

        @staticmethod
        def capability(name):
            raise PluginScopeError("undeclared")

    with pytest.raises(PluginScopeError):
        record.contribution.widget_factory(Undeclared(), None)


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

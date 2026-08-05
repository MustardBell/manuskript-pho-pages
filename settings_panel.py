"""PHO Pages' own settings, rendered inside the plugin manager.

Manuskript hands this plugin an empty region of the plugin details pane.
Everything drawn there belongs to PHO, so PHO decides what goes in it --
including whether to ask for the routing panel at all. Core owns the widget
and fixes it once for every plugin; it does not put it here uninvited.
"""

PAGE_TYPE_ID = "manuskript.pho-page"

#: Declared in plugin.json, so asking for it is allowed.
EXPORT_ROUTING = "ui.export_routing"


def build_settings_panel(context, parent=None):
    routing = context.capability(EXPORT_ROUTING)
    return routing.panel(
        PAGE_TYPE_ID,
        parent=parent,
        intro="Render PHO pages as…",
    )

"""PHO Pages' own settings, rendered inside the plugin manager.

Manuskript hands this plugin an empty region of the plugin details pane and
a routing gateway scoped to the page types PHO registered. Everything drawn
here belongs to PHO, so it appears only while PHO Pages is selected.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


PAGE_TYPE_ID = "manuskript.pho-page"


class PhoSettingsPanel(QWidget):
    """Pick which PHO renderer produces each export format."""

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.routing = context.page_routing
        self._combos = {}
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.introLabel = QLabel(
            self.tr("Render PHO pages as…"),
            self,
        )
        self.introLabel.setWordWrap(True)
        layout.addWidget(self.introLabel)

        self.form = QFormLayout()
        self.form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        layout.addLayout(self.form)

        self.noticeLabel = QLabel(self)
        self.noticeLabel.setWordWrap(True)
        layout.addWidget(self.noticeLabel)

        self.optionsRow = QHBoxLayout()
        layout.addLayout(self.optionsRow)

        self.refresh()

    def refresh(self):
        self._syncing = True
        try:
            self._clear(self.form)
            self._combos = {}
            routes = self.routing.export_routes
            if not routes:
                self.noticeLabel.setText(
                    self.tr(
                        "No available export format consumes PHO pages."
                    )
                )
                self._build_option_buttons()
                return
            unsaved = 0
            for route in routes:
                combo = QComboBox(self)
                candidates = self.routing.candidates(
                    PAGE_TYPE_ID,
                    route.representation_format,
                )
                for renderer in candidates:
                    label = renderer.descriptor.name
                    if (
                        route.representation_format
                        not in renderer.target_formats
                    ):
                        label += self.tr(" (compatible fallback)")
                    owner = self.routing.owner_of(renderer.descriptor.id)
                    if owner and owner != self.context.plugin_id:
                        # Another plugin may render PHO pages; say whose.
                        label += " — " + owner
                    combo.addItem(label, renderer.descriptor.id)
                saved = self.routing.selected(PAGE_TYPE_ID, route.id)
                index = combo.findData(saved)
                if index < 0:
                    unsaved += 1
                combo.setCurrentIndex(max(0, index))
                combo.currentIndexChanged.connect(
                    lambda _index, route=route: self._route_changed(route)
                )
                self.form.addRow(self.tr(route.label), combo)
                self._combos[route.id] = combo
            self.noticeLabel.setText(
                self.tr(
                    "{} format(s) have no saved choice and use the "
                    "highest-priority renderer shown."
                ).format(unsaved)
                if unsaved
                else ""
            )
            self._build_option_buttons()
        finally:
            self._syncing = False

    def _build_option_buttons(self):
        self._clear(self.optionsRow)
        seen = set()
        for route in self.routing.export_routes:
            for renderer in self.routing.candidates(
                    PAGE_TYPE_ID, route.representation_format):
                owner = self.routing.owner_of(renderer.descriptor.id)
                if owner != self.context.plugin_id:
                    # Only PHO's own renderers are PHO's to configure.
                    continue
                if renderer.descriptor.id in seen:
                    continue
                if not (
                    renderer.options or renderer.options_view_factory
                ):
                    continue
                seen.add(renderer.descriptor.id)
                button = QPushButton(
                    self.tr("Configure {}…").format(
                        renderer.descriptor.name
                    ),
                    self,
                )
                button.clicked.connect(
                    lambda _checked=False, renderer=renderer:
                    self.context.edit_options(renderer, self)
                )
                self.optionsRow.addWidget(button)
        self.optionsRow.addStretch(1)

    def _route_changed(self, route):
        if self._syncing:
            return
        combo = self._combos.get(route.id)
        renderer_id = combo.currentData() if combo is not None else ""
        if not renderer_id:
            return
        try:
            self.routing.select(
                PAGE_TYPE_ID,
                route.id,
                renderer_id,
                representation_format=route.representation_format,
            )
        except Exception as error:
            self.context.show_status(
                "PHO Pages could not save that renderer: {}".format(error),
                8000,
                2,
            )
            return
        self.noticeLabel.setText("")

    def _clear(self, layout):
        while layout.count():
            entry = layout.takeAt(0)
            widget = entry.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()


def build_settings_panel(context, parent=None):
    return PhoSettingsPanel(context, parent)

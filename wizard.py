from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from .wizard_controller import PhoWizardController
from .wizard_view import PhoWizardView


class PhoPageWizard(QWidget):
    """Plugin-facing adapter composing a passive view and controller."""

    applyRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("phoPageWizard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = PhoWizardView(self)
        layout.addWidget(self.view)
        self.controller = PhoWizardController(
            self.view,
            parent=self,
        )
        self.controller.applyRequested.connect(self.applyRequested)

    def load_source(self, source):
        self.controller.load_source(source)

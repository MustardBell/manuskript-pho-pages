from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class PhoWizardView(QWidget):
    """Passive Qt view for the structured PHO editor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("phoWizardView")
        self._buildUi()

    def _buildUi(self):
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel(self.tr("PHO page wizard"), self)
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        self.statusLabel = QLabel(self)
        self.statusLabel.setObjectName("phoWizardStatus")
        self.resetButton = QPushButton(self.tr("Reset"), self)
        self.applyButton = QPushButton(
            self.tr("Apply to source"),
            self,
        )
        self.applyButton.setObjectName("phoWizardApply")
        header.addWidget(title)
        header.addWidget(self.statusLabel, 1)
        header.addWidget(self.resetButton)
        header.addWidget(self.applyButton)
        header.addSpacing(44)
        layout.addLayout(header)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._buildPageTab(), self.tr("Page"))
        self.tabs.addTab(self._buildUsersTab(), self.tr("Users"))
        self.tabs.addTab(
            self._buildThreadTab(),
            self.tr("Threads && posts"),
        )
        layout.addWidget(self.tabs, 1)

    def _buildPageTab(self):
        page = QWidget(self)
        form = QFormLayout(page)
        self.readerEdit = QLineEdit(page)
        self.dateEdit = QLineEdit(page)
        self.dateEdit.setPlaceholderText(
            "2011-02-04T12:00:00-05:00"
        )
        self.postsSpin = self._spin(page, 1, 100, 10)
        self.startPageSpin = self._spin(page, 1, 999999, 1)
        self.endPageSpin = self._spin(page, 0, 999999, 0)
        self.endPageSpin.setSpecialValueText(self.tr("Automatic"))
        self.timeZoneEdit = QLineEdit(page)
        self.timeZoneEdit.setPlaceholderText("America/New_York")
        self.welcomeCheck = QCheckBox(
            self.tr("Show the logged-in reader greeting"), page
        )
        self.referencesCheck = QCheckBox(
            self.tr("Enable message IDs and referrals"), page
        )
        self.noAbbreviationCheck = QCheckBox(
            self.tr("Show dates without hover timestamps"), page
        )
        form.addRow(self.tr("Reader"), self.readerEdit)
        form.addRow(self.tr("Original-post date"), self.dateEdit)
        form.addRow(self.tr("Posts per page"), self.postsSpin)
        form.addRow(self.tr("First page"), self.startPageSpin)
        form.addRow(self.tr("Last page"), self.endPageSpin)
        form.addRow(self.tr("Time zone"), self.timeZoneEdit)
        form.addRow("", self.welcomeCheck)
        form.addRow("", self.referencesCheck)
        form.addRow("", self.noAbbreviationCheck)
        return page

    def _buildUsersTab(self):
        page = QWidget(self)
        layout = QVBoxLayout(page)
        explanation = QLabel(
            self.tr(
                "One user per line: name, then tab-separated aliasFor: "
                "or tag: fields. This remains the raw USERS block."
            ),
            page,
        )
        explanation.setWordWrap(True)
        self.usersEdit = QPlainTextEdit(page)
        self.usersEdit.setObjectName("phoWizardUsers")
        layout.addWidget(explanation)
        layout.addWidget(self.usersEdit, 1)
        return page

    def _buildThreadTab(self):
        page = QWidget(self)
        outer = QVBoxLayout(page)
        chooser = QHBoxLayout()
        self.threadCombo = QComboBox(page)
        self.addThreadButton = QPushButton(self.tr("Add thread"), page)
        self.removeThreadButton = QPushButton(
            self.tr("Remove thread"), page
        )
        chooser.addWidget(QLabel(self.tr("Thread"), page))
        chooser.addWidget(self.threadCombo, 1)
        chooser.addWidget(self.addThreadButton)
        chooser.addWidget(self.removeThreadButton)
        outer.addLayout(chooser)

        thread_form = QFormLayout()
        self.topicEdit = QLineEdit(page)
        self.boardEdit = QLineEdit(page)
        self.boardEdit.setPlaceholderText("Places=>America")
        self.posterEdit = QLineEdit(page)
        self.noOriginalPostCheck = QCheckBox(
            self.tr("Replies only (NOOP)"), page
        )
        thread_form.addRow(self.tr("Topic"), self.topicEdit)
        thread_form.addRow(self.tr("Board path"), self.boardEdit)
        thread_form.addRow(self.tr("Original poster"), self.posterEdit)
        thread_form.addRow("", self.noOriginalPostCheck)
        outer.addLayout(thread_form)

        splitter = QSplitter(Qt.Horizontal, page)
        original_group = QGroupBox(self.tr("Original post"), splitter)
        original_layout = QVBoxLayout(original_group)
        self.originalPostEdit = QPlainTextEdit(original_group)
        self.originalPostEdit.setObjectName("phoWizardOriginalPost")
        original_layout.addWidget(self.originalPostEdit)

        replies_group = QGroupBox(
            self.tr("Replies (drag to reorder)"), splitter
        )
        replies_layout = QHBoxLayout(replies_group)
        reply_list_layout = QVBoxLayout()
        self.replyList = QListWidget(replies_group)
        self.replyList.setObjectName("phoWizardReplyList")
        self.replyList.setDragDropMode(QAbstractItemView.InternalMove)
        self.replyList.setDefaultDropAction(Qt.MoveAction)
        self.replyList.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        reply_buttons = QHBoxLayout()
        self.addReplyButton = QPushButton(self.tr("Add"), replies_group)
        self.removeReplyButton = QPushButton(
            self.tr("Remove"), replies_group
        )
        reply_buttons.addWidget(self.addReplyButton)
        reply_buttons.addWidget(self.removeReplyButton)
        reply_list_layout.addWidget(self.replyList, 1)
        reply_list_layout.addLayout(reply_buttons)

        reply_editor = QWidget(replies_group)
        reply_editor_layout = QVBoxLayout(reply_editor)
        self.replyUserEdit = QLineEdit(reply_editor)
        self.replyMetadataEdit = QPlainTextEdit(reply_editor)
        self.replyMetadataEdit.setObjectName("phoWizardReplyMetadata")
        self.replyMetadataEdit.setPlaceholderText(
            "tag:Verified Cape\n+2m\nid:message-1\nrefer:latest"
        )
        self.replyMetadataEdit.setMaximumHeight(100)
        self.replyBodyEdit = QPlainTextEdit(reply_editor)
        self.replyBodyEdit.setObjectName("phoWizardReplyBody")
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel(self.tr("Username"), reply_editor))
        user_layout.addWidget(self.replyUserEdit, 1)
        reply_editor_layout.addLayout(user_layout)
        reply_editor_layout.addWidget(QLabel(
            self.tr("Metadata (one field per line)"), reply_editor
        ))
        reply_editor_layout.addWidget(self.replyMetadataEdit)
        reply_editor_layout.addWidget(
            QLabel(self.tr("Message"), reply_editor)
        )
        reply_editor_layout.addWidget(self.replyBodyEdit, 1)
        replies_layout.addLayout(reply_list_layout, 1)
        replies_layout.addWidget(reply_editor, 2)
        splitter.addWidget(original_group)
        splitter.addWidget(replies_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([300, 600])
        outer.addWidget(splitter, 1)
        return page

    @staticmethod
    def _spin(parent, minimum, maximum, value):
        spin = QSpinBox(parent)
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

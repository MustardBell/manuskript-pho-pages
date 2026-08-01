from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox

from .converter import is_pho_page
from .model import PhoModelError, PhoPage, PhoReply, PhoThread


class PhoWizardController(QObject):
    """Own PHO wizard state and mediate view↔source changes."""

    applyRequested = pyqtSignal(str)

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self.page = None
        self._loadedSource = ""
        self._loading = False
        self._dirty = False
        self._connectView()

    def _connectView(self):
        view = self.view
        view.applyButton.clicked.connect(self._apply)
        view.resetButton.clicked.connect(self._reset)
        view.threadCombo.currentIndexChanged.connect(self._threadChanged)
        view.addThreadButton.clicked.connect(self._addThread)
        view.removeThreadButton.clicked.connect(self._removeThread)
        view.replyList.currentItemChanged.connect(self._replyChanged)
        view.replyList.model().rowsMoved.connect(self._repliesMoved)
        view.addReplyButton.clicked.connect(self._addReply)
        view.removeReplyButton.clicked.connect(self._removeReply)

        for editor, key in (
            (view.readerEdit, "reader"),
            (view.dateEdit, "date"),
            (view.timeZoneEdit, "timeZone"),
        ):
            editor.textChanged.connect(
                lambda value, setting=key:
                self._settingChanged(setting, value)
            )
        for editor, key in (
            (view.postsSpin, "posts"),
            (view.startPageSpin, "startpage"),
            (view.endPageSpin, "endpage"),
        ):
            editor.valueChanged.connect(
                lambda value, setting=key:
                self._numberSettingChanged(setting, value)
            )
        view.welcomeCheck.toggled.connect(self._welcomeChanged)
        view.referencesCheck.toggled.connect(
            lambda checked: self._flagChanged("refer", checked)
        )
        view.noAbbreviationCheck.toggled.connect(
            lambda checked: self._flagChanged("noabbr", checked)
        )
        view.usersEdit.textChanged.connect(self._usersChanged)
        for editor in (view.topicEdit, view.boardEdit, view.posterEdit):
            editor.textChanged.connect(self._threadFieldsChanged)
        view.noOriginalPostCheck.toggled.connect(
            self._threadFieldsChanged
        )
        view.originalPostEdit.textChanged.connect(
            self._threadFieldsChanged
        )
        view.replyUserEdit.textChanged.connect(self._replyFieldsChanged)
        view.replyMetadataEdit.textChanged.connect(
            self._replyFieldsChanged
        )
        view.replyBodyEdit.textChanged.connect(self._replyFieldsChanged)

    def load_source(self, source):
        source = str(source)
        if source == self._loadedSource and self._dirty:
            return
        view = self.view
        self._loading = True
        try:
            try:
                self.page = PhoPage.parse(source)
                status = ""
                dirty = False
            except PhoModelError as error:
                if is_pho_page(source):
                    self.page = None
                    view.statusLabel.setText(str(error))
                    view.statusLabel.setStyleSheet("color: #b00020;")
                    view.applyButton.setEnabled(False)
                    view.resetButton.setEnabled(False)
                    view.tabs.setEnabled(False)
                    self._loadedSource = source
                    self._dirty = False
                    return
                self.page = PhoPage.initialize_from_markdown(source)
                status = view.tr(
                    "Apply to wrap this text as a PHO page."
                )
                dirty = True
            self._loadedSource = source
            view.tabs.setEnabled(True)
            self._loadPageFields()
            self._dirty = dirty
            view.statusLabel.setText(status)
            view.statusLabel.setStyleSheet("")
            view.applyButton.setEnabled(dirty)
            view.resetButton.setEnabled(dirty)
        finally:
            self._loading = False

    def _loadPageFields(self):
        view = self.view
        page = self.page
        view.readerEdit.setText(page.setting("reader", "Reader"))
        view.dateEdit.setText(page.setting("date"))
        view.postsSpin.setValue(self._number("posts", 10, 1))
        view.startPageSpin.setValue(self._number("startpage", 1, 1))
        view.endPageSpin.setValue(self._number("endpage", 0, 0))
        view.timeZoneEdit.setText(page.setting("timeZone"))
        view.welcomeCheck.setChecked(page.welcome)
        view.referencesCheck.setChecked(bool(page.setting("refer")))
        view.noAbbreviationCheck.setChecked(bool(page.setting("noabbr")))
        view.usersEdit.setPlainText(page.users_source)
        view.threadCombo.clear()
        for thread in page.threads:
            view.threadCombo.addItem(
                thread.topic or view.tr("Untitled")
            )
        if page.threads:
            view.threadCombo.setCurrentIndex(0)
            self._loadThread(page.threads[0])
        view.removeThreadButton.setEnabled(len(page.threads) > 1)

    def _number(self, key, default, minimum):
        try:
            return max(minimum, int(self.page.setting(key, default)))
        except (TypeError, ValueError):
            return default

    def _currentThread(self):
        if self.page is None:
            return None
        index = self.view.threadCombo.currentIndex()
        if not 0 <= index < len(self.page.threads):
            return None
        return self.page.threads[index]

    def _loadThread(self, thread):
        view = self.view
        was_loading = self._loading
        self._loading = True
        try:
            view.topicEdit.setText(thread.topic)
            view.boardEdit.setText(thread.board)
            view.posterEdit.setText(thread.poster)
            view.noOriginalPostCheck.setChecked(thread.no_original_post)
            view.originalPostEdit.setPlainText(thread.original_post)
            self._loadReplies(thread)
        finally:
            self._loading = was_loading

    def _loadReplies(self, thread):
        reply_list = self.view.replyList
        reply_list.clear()
        for reply in thread.replies:
            item = QListWidgetItem(self._replyLabel(reply))
            item.setData(Qt.UserRole, reply)
            reply_list.addItem(item)
        if reply_list.count():
            reply_list.setCurrentRow(0)
            self._loadReply(thread.replies[0])
        else:
            self._loadReply(None)

    def _currentReply(self):
        item = self.view.replyList.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    def _loadReply(self, reply):
        view = self.view
        was_loading = self._loading
        self._loading = True
        try:
            enabled = reply is not None
            view.replyUserEdit.setEnabled(enabled)
            view.replyMetadataEdit.setEnabled(enabled)
            view.replyBodyEdit.setEnabled(enabled)
            view.removeReplyButton.setEnabled(enabled)
            view.replyUserEdit.setText(reply.user if reply else "")
            view.replyMetadataEdit.setPlainText(
                "\n".join(reply.metadata[1:]) if reply else ""
            )
            view.replyBodyEdit.setPlainText(reply.body if reply else "")
        finally:
            self._loading = was_loading

    @staticmethod
    def _replyLabel(reply):
        preview = " ".join(reply.body.split())[:48]
        return "{} — {}".format(reply.user, preview or "…")

    def _settingChanged(self, key, value):
        if self._loading or self.page is None:
            return
        self.page.set_setting(key, value)
        self._setDirty()

    def _numberSettingChanged(self, key, value):
        if self._loading or self.page is None:
            return
        self.page.set_setting(
            key,
            "" if key == "endpage" and value == 0 else value,
        )
        self._setDirty()

    def _flagChanged(self, key, checked):
        if self._loading or self.page is None:
            return
        self.page.set_setting(key, "1" if checked else "")
        self._setDirty()

    def _welcomeChanged(self, checked):
        if self._loading or self.page is None:
            return
        self.page.welcome = bool(checked)
        self._setDirty()

    def _usersChanged(self):
        if self._loading or self.page is None:
            return
        self.page.users_source = self.view.usersEdit.toPlainText()
        self._setDirty()

    def _threadChanged(self, index):
        if self._loading or self.page is None:
            return
        if 0 <= index < len(self.page.threads):
            self._loadThread(self.page.threads[index])

    def _threadFieldsChanged(self, *_args):
        if self._loading:
            return
        thread = self._currentThread()
        if thread is None:
            return
        view = self.view
        thread.topic = view.topicEdit.text()
        thread.board = view.boardEdit.text()
        thread.poster = view.posterEdit.text()
        thread.no_original_post = view.noOriginalPostCheck.isChecked()
        thread.original_post = view.originalPostEdit.toPlainText()
        view.threadCombo.setItemText(
            view.threadCombo.currentIndex(),
            thread.topic or view.tr("Untitled"),
        )
        self._setDirty()

    def _addThread(self):
        if self.page is None:
            return
        thread = PhoThread()
        self.page.threads.append(thread)
        self.view.threadCombo.addItem(thread.topic)
        self.view.threadCombo.setCurrentIndex(len(self.page.threads) - 1)
        self.view.removeThreadButton.setEnabled(True)
        self._setDirty()

    def _removeThread(self):
        if self.page is None or len(self.page.threads) <= 1:
            return
        view = self.view
        index = view.threadCombo.currentIndex()
        answer = QMessageBox.question(
            view,
            view.tr("Remove PHO thread"),
            view.tr("Remove this thread and all of its posts?"),
        )
        if answer != QMessageBox.Yes:
            return
        self.page.threads.pop(index)
        view.threadCombo.removeItem(index)
        view.removeThreadButton.setEnabled(len(self.page.threads) > 1)
        self._setDirty()

    def _replyChanged(self, current, _previous):
        if self._loading:
            return
        self._loadReply(
            current.data(Qt.UserRole) if current is not None else None
        )

    def _replyFieldsChanged(self):
        if self._loading:
            return
        reply = self._currentReply()
        if reply is None:
            return
        view = self.view
        reply.set_fields(
            view.replyUserEdit.text(),
            view.replyMetadataEdit.toPlainText().replace("\n", "\t"),
        )
        reply.body = view.replyBodyEdit.toPlainText()
        view.replyList.currentItem().setText(self._replyLabel(reply))
        self._setDirty()

    def _addReply(self):
        thread = self._currentThread()
        if thread is None:
            return
        view = self.view
        reply = PhoReply()
        thread.replies.append(reply)
        item = QListWidgetItem(self._replyLabel(reply))
        item.setData(Qt.UserRole, reply)
        view.replyList.addItem(item)
        view.replyList.setCurrentItem(item)
        view.replyUserEdit.setFocus()
        view.replyUserEdit.selectAll()
        self._setDirty()

    def _removeReply(self):
        thread = self._currentThread()
        item = self.view.replyList.currentItem()
        if thread is None or item is None:
            return
        reply = item.data(Qt.UserRole)
        thread.replies.remove(reply)
        self.view.replyList.takeItem(self.view.replyList.row(item))
        self._setDirty()

    def _repliesMoved(self, *_args):
        if self._loading:
            return
        thread = self._currentThread()
        if thread is None:
            return
        reply_list = self.view.replyList
        thread.replies = [
            reply_list.item(index).data(Qt.UserRole)
            for index in range(reply_list.count())
        ]
        self._setDirty()

    def _setDirty(self):
        if self._loading or self.page is None:
            return
        self._dirty = True
        self.view.statusLabel.setText(
            self.view.tr("Not applied to source")
        )
        self.view.statusLabel.setStyleSheet("")
        self.view.applyButton.setEnabled(True)
        self.view.resetButton.setEnabled(True)

    def _apply(self):
        if self.page is None:
            return
        source = self.page.to_source()
        self.applyRequested.emit(source)
        self._loadedSource = source
        self._dirty = False
        self.view.statusLabel.setText(self.view.tr("Applied"))
        self.view.applyButton.setEnabled(False)
        self.view.resetButton.setEnabled(False)

    def _reset(self):
        source = self._loadedSource
        self._loadedSource = ""
        self.load_source(source)

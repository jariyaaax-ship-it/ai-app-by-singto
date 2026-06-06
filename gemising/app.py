from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .config import APP_NAME, Settings, load_settings, save_settings
from .gemini_client import generate_ollama_reply, generate_reply
from .history import Conversation, Message, create_conversation, ensure_unique_title, load_conversations, save_conversations


APP_STYLESHEET = """
QMainWindow {
    background: #0f1220;
}
QWidget {
    color: #e8ecff;
    font-size: 13px;
    font-family: Inter, "Noto Sans", "Segoe UI", sans-serif;
}
QLabel#sidebarTitle {
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
    padding: 8px 4px;
}
QLabel#appTitle {
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
}
QLabel#statusLabel {
    color: #9ca8d8;
    padding: 4px 2px;
}
QWidget#sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a2040, stop:1 #12162a);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}
QWidget#chatPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #151a2f, stop:1 #10131f);
}
QListWidget {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    padding: 12px 10px;
    margin: 4px 2px;
    border-radius: 10px;
    color: #dce2ff;
}
QListWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6c63ff, stop:1 #26d0ce);
    color: white;
}
QPlainTextEdit, QLineEdit {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px;
    padding: 12px;
    selection-background-color: #6c63ff;
}
QPlainTextEdit {
    line-height: 1.4em;
}
QPushButton {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 12px;
    padding: 10px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: rgba(255, 255, 255, 0.14);
}
QPushButton:pressed {
    background: rgba(108, 99, 255, 0.35);
}
QPushButton#primaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6c63ff, stop:1 #26d0ce);
    border: none;
    color: white;
}
QPushButton#primaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7b74ff, stop:1 #39ddd8);
}
QPushButton#dangerButton {
    background: rgba(255, 92, 122, 0.14);
    border: 1px solid rgba(255, 92, 122, 0.30);
    color: #ffb9c6;
}
QPushButton#dangerButton:hover {
    background: rgba(255, 92, 122, 0.22);
}
QSplitter::handle {
    background: rgba(255, 255, 255, 0.06);
}
QDialog {
    background: #141827;
}
"""


class ReplyWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        api_key: str,
        messages: list[dict[str, str]],
        *,
        provider: str = "gemini",
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.1",
        enable_google_search: bool = False,
        enable_url_context: bool = False,
    ):
        super().__init__()
        self.api_key = api_key
        self.messages = messages
        self.provider = provider
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.enable_google_search = enable_google_search
        self.enable_url_context = enable_url_context

    def run(self) -> None:
        try:
            if self.provider == "ollama":
                self.finished.emit(
                    generate_ollama_reply(
                        self.ollama_base_url,
                        self.messages,
                        model=self.ollama_model,
                    )
                )
            else:
                self.finished.emit(
                    generate_reply(
                        self.api_key,
                        self.messages,
                        enable_google_search=self.enable_google_search,
                        enable_url_context=self.enable_url_context,
                    )
                )
        except Exception as exc:
            self.failed.emit(str(exc))


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.settings = settings

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Gemini API Key"))

        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setText(settings.api_key)
        layout.addWidget(self.api_key)

        layout.addWidget(QLabel("Backend"))
        self.provider = QLineEdit()
        self.provider.setText(settings.provider)
        self.provider.setPlaceholderText("gemini or ollama")
        layout.addWidget(self.provider)

        layout.addWidget(QLabel("Ollama Base URL"))
        self.ollama_base_url = QLineEdit()
        self.ollama_base_url.setText(settings.ollama_base_url)
        layout.addWidget(self.ollama_base_url)

        layout.addWidget(QLabel("Ollama Model"))
        self.ollama_model = QLineEdit()
        self.ollama_model.setText(settings.ollama_model)
        layout.addWidget(self.ollama_model)

        self.google_search = QLineEdit()
        self.google_search.setText("on" if settings.enable_google_search else "off")
        layout.addWidget(QLabel("Google Search grounding"))
        layout.addWidget(self.google_search)

        self.url_context = QLineEdit()
        self.url_context.setText("on" if settings.enable_url_context else "off")
        layout.addWidget(QLabel("URL Context"))
        layout.addWidget(self.url_context)

        self.url_sources = QPlainTextEdit()
        self.url_sources.setPlaceholderText("One URL per line for URL Context")
        self.url_sources.setPlainText(settings.url_context_sources)
        self.url_sources.setFixedHeight(110)
        layout.addWidget(QLabel("URL Context Sources"))
        layout.addWidget(self.url_sources)

        button_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(save_btn)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

    def accept(self) -> None:
        self.settings.api_key = self.api_key.text().strip()
        self.settings.provider = self.provider.text().strip().lower() or "gemini"
        self.settings.ollama_base_url = self.ollama_base_url.text().strip() or "http://localhost:11434"
        self.settings.ollama_model = self.ollama_model.text().strip() or "llama3.1"
        self.settings.enable_google_search = self.google_search.text().strip().lower() in {"on", "true", "1", "yes"}
        self.settings.enable_url_context = self.url_context.text().strip().lower() in {"on", "true", "1", "yes"}
        self.settings.url_context_sources = self.url_sources.toPlainText().strip()
        super().accept()


class RenameDialog(QDialog):
    def __init__(self, current_title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Rename chat")
        self.new_title: str | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Chat name"))

        self.title_input = QLineEdit()
        self.title_input.setText(current_title)
        self.title_input.selectAll()
        layout.addWidget(self.title_input)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def accept(self) -> None:
        title = self.title_input.text().strip() or "New chat"
        self.new_title = title[:64]
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 760)

        self.settings = load_settings()
        self.conversations = load_conversations()
        if not self.conversations:
            self.conversations = [create_conversation()]
        self.current_conversation_index = 0
        self.busy = False
        self.worker_thread: threading.Thread | None = None
        self.worker: ReplyWorker | None = None
        self.pending_conversation_index: int | None = None

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)

        splitter = QSplitter()
        outer.addWidget(splitter)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_title = QLabel("Chats")
        sidebar_title.setObjectName("sidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        self.chat_list = QListWidget()
        self.chat_list.currentRowChanged.connect(self.on_chat_selected)
        self.chat_list.itemDoubleClicked.connect(self.rename_chat_from_list)
        sidebar_layout.addWidget(self.chat_list, 1)

        sidebar_buttons = QHBoxLayout()
        self.rename_chat_btn = QPushButton("Rename")
        self.rename_chat_btn.clicked.connect(self.rename_current_chat)
        self.new_chat_btn = QPushButton("New")
        self.new_chat_btn.setObjectName("primaryButton")
        self.new_chat_btn.clicked.connect(self.new_chat)
        self.delete_chat_btn = QPushButton("Delete")
        self.delete_chat_btn.setObjectName("dangerButton")
        self.delete_chat_btn.clicked.connect(self.delete_chat)
        sidebar_buttons.addWidget(self.rename_chat_btn)
        sidebar_buttons.addWidget(self.new_chat_btn)
        sidebar_buttons.addWidget(self.delete_chat_btn)
        sidebar_layout.addLayout(sidebar_buttons)

        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(self.settings_btn)

        self.history_path_label = QLabel()
        sidebar_layout.addWidget(self.history_path_label)

        self.chat_view = QWidget()
        self.chat_view.setObjectName("chatPanel")
        chat_layout = QVBoxLayout(self.chat_view)

        header = QHBoxLayout()
        self.title_label = QLabel(APP_NAME)
        self.title_label.setObjectName("appTitle")
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        header.addWidget(self.title_label)
        header.addStretch(1)
        chat_layout.addLayout(header)

        self.status = QLabel("Ready")
        self.status.setObjectName("statusLabel")
        chat_layout.addWidget(self.status)

        self.chat_text = QPlainTextEdit()
        self.chat_text.setReadOnly(True)
        chat_layout.addWidget(self.chat_text, 1)

        composer = QVBoxLayout()
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Message")
        self.input.setFixedHeight(110)
        composer.addWidget(self.input)

        buttons = QHBoxLayout()
        clear_btn = QPushButton("Clear chat")
        clear_btn.clicked.connect(self.clear_current_chat)
        send_btn = QPushButton("Send")
        send_btn.setObjectName("primaryButton")
        send_btn.clicked.connect(self.send_message)
        buttons.addWidget(clear_btn)
        buttons.addStretch(1)
        buttons.addWidget(send_btn)
        composer.addLayout(buttons)
        chat_layout.addLayout(composer)

        splitter.addWidget(sidebar)
        splitter.addWidget(self.chat_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 900])

        self.refresh_chat_list()
        self.select_conversation(0)

    @property
    def current_conversation(self) -> Conversation:
        return self.conversations[self.current_conversation_index]

    def persist(self) -> None:
        save_conversations(self.conversations)

    def assistant_label(self) -> str:
        if self.settings.provider == "ollama":
            model = self.settings.ollama_model.strip() or "llama3.1"
            return f"Ollama ({model})"
        return "Gemini"

    def refresh_chat_list(self) -> None:
        self.chat_list.blockSignals(True)
        self.chat_list.clear()
        for conversation in self.conversations:
            self.chat_list.addItem(QListWidgetItem(conversation.title))
        self.chat_list.blockSignals(False)
        if self.conversations:
            self.chat_list.setCurrentRow(self.current_conversation_index)
        self.history_path_label.setText("History: chat_history.json")

    def select_conversation(self, index: int) -> None:
        if not self.conversations:
            self.conversations = [create_conversation()]
            self.current_conversation_index = 0
            self.persist()
            self.refresh_chat_list()
        index = max(0, min(index, len(self.conversations) - 1))
        self.current_conversation_index = index
        self.chat_list.setCurrentRow(index)
        self.refresh_current_chat()

    def on_chat_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.conversations):
            return
        self.current_conversation_index = row
        self.refresh_current_chat()

    def refresh_current_chat(self) -> None:
        conv = self.current_conversation
        if not conv.messages:
            self.chat_text.setPlainText("Start a conversation.")
        else:
            lines = []
            for msg in conv.messages:
                speaker = "You" if msg.role == "user" else self.assistant_label()
                lines.append(f"{speaker}: {msg.content}")
            self.chat_text.setPlainText("\n\n".join(lines))
            self.chat_text.verticalScrollBar().setValue(self.chat_text.verticalScrollBar().maximum())
        self.title_label.setText(conv.title)

    def rename_current_if_needed(self) -> None:
        conv = self.current_conversation
        if conv.title != "New chat":
            return
        existing_titles = [c.title for c in self.conversations]
        for msg in conv.messages:
            if msg.role == "user" and msg.content.strip():
                text = msg.content.strip().replace("\n", " ")
                desired = text[:32] + ("..." if len(text) > 32 else "")
                conv.title = ensure_unique_title(desired, existing_titles, current_title=conv.title)
                conv.updated_at = conv.messages[-1].created_at if conv.messages else conv.updated_at
                break

    def rename_chat_from_list(self, item: QListWidgetItem) -> None:
        row = self.chat_list.row(item)
        if row < 0 or row >= len(self.conversations):
            return
        self.current_conversation_index = row
        self.rename_current_chat()

    def rename_current_chat(self) -> None:
        if self.busy:
            return
        conv = self.current_conversation
        dialog = RenameDialog(conv.title, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.new_title:
            conv.title = ensure_unique_title(dialog.new_title, [c.title for c in self.conversations], current_title=conv.title)
            self.persist()
            self.refresh_chat_list()
            self.refresh_current_chat()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            save_settings(self.settings)
            self.status.setText("Settings saved.")

    def new_chat(self) -> None:
        if self.busy:
            return
        conversation = create_conversation()
        conversation.title = ensure_unique_title("New chat", [c.title for c in self.conversations])
        self.conversations.append(conversation)
        self.current_conversation_index = len(self.conversations) - 1
        self.persist()
        self.refresh_chat_list()
        self.refresh_current_chat()

    def delete_chat(self) -> None:
        if self.busy or len(self.conversations) <= 1:
            return
        current = self.current_conversation_index
        reply = QMessageBox.question(
            self,
            "Delete chat",
            f"Delete '{self.current_conversation.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self.conversations[current]
        self.current_conversation_index = max(0, current - 1)
        self.persist()
        self.refresh_chat_list()
        self.select_conversation(self.current_conversation_index)

    def append_message(self, role: str, content: str) -> None:
        conv = self.current_conversation
        conv.messages.append(Message(role=role, content=content))
        conv.updated_at = conv.messages[-1].created_at
        self.rename_current_if_needed()
        self.persist()
        self.refresh_current_chat()
        self.refresh_chat_list()

    def clear_current_chat(self) -> None:
        if self.busy:
            return
        conv = self.current_conversation
        conv.messages.clear()
        conv.title = ensure_unique_title("New chat", [c.title for c in self.conversations], current_title=conv.title)
        self.persist()
        self.refresh_current_chat()
        self.refresh_chat_list()
        self.status.setText("Chat cleared.")

    def send_message(self) -> None:
        if self.busy:
            return
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()
        self.append_message("user", text)
        self.status.setText("Thinking...")
        self.busy = True
        self.pending_conversation_index = self.current_conversation_index
        self.run_worker()

    def run_worker(self) -> None:
        target_index = self.pending_conversation_index if self.pending_conversation_index is not None else self.current_conversation_index
        payload = [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversations[target_index].messages
        ]
        if self.settings.enable_url_context and self.settings.url_context_sources.strip():
            url_lines = [line.strip() for line in self.settings.url_context_sources.splitlines() if line.strip()]
            if url_lines:
                payload = payload + [
                    {
                        "role": "user",
                        "content": "Use URL context for these sources:\n" + "\n".join(url_lines),
                    }
                ]
        self.worker = ReplyWorker(
            self.settings.api_key,
            payload,
            provider=self.settings.provider,
            ollama_base_url=self.settings.ollama_base_url,
            ollama_model=self.settings.ollama_model,
            enable_google_search=self.settings.enable_google_search,
            enable_url_context=self.settings.enable_url_context,
        )
        self.worker_thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker.finished.connect(self.on_reply)
        self.worker.failed.connect(self.on_error)
        self.worker_thread.start()

    def on_reply(self, reply: str) -> None:
        self.busy = False
        target_index = self.pending_conversation_index if self.pending_conversation_index is not None else self.current_conversation_index
        self.current_conversation_index = target_index
        self.chat_list.setCurrentRow(target_index)
        self.conversations[target_index].messages.append(Message(role="assistant", content=reply))
        self.conversations[target_index].updated_at = self.conversations[target_index].messages[-1].created_at
        self.rename_current_if_needed()
        self.persist()
        self.refresh_chat_list()
        self.refresh_current_chat()
        self.status.setText("Ready")
        self.pending_conversation_index = None

    def on_error(self, message: str) -> None:
        self.busy = False
        target_index = self.pending_conversation_index if self.pending_conversation_index is not None else self.current_conversation_index
        self.current_conversation_index = target_index
        self.chat_list.setCurrentRow(target_index)
        self.conversations[target_index].messages.append(Message(role="assistant", content=f"Error: {message}"))
        self.conversations[target_index].updated_at = self.conversations[target_index].messages[-1].created_at
        self.rename_current_if_needed()
        self.persist()
        self.refresh_chat_list()
        self.refresh_current_chat()
        self.status.setText(message)
        self.pending_conversation_index = None


def run_app() -> int:
    app = QApplication([])
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()

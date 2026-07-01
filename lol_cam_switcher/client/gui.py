"""Client agent GUI — standalone events + optional server relay."""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from lol_cam_switcher.client.config import ClientConfig
from lol_cam_switcher.client.engine import ClientEngine
from lol_cam_switcher.lol.events import GameEvent


class _EventBridge(QObject):
    event_received = Signal(str)


class ClientWindow(QMainWindow):
    def __init__(self, config: ClientConfig | None = None):
        super().__init__()
        self.config = config or ClientConfig()
        self._bridge = _EventBridge()
        self._bridge.event_received.connect(self._append_event_line)
        self.engine = ClientEngine(
            config=self.config,
            on_state_changed=self._refresh_status,
            on_event=lambda e: self._bridge.event_received.emit(str(e)),
        )
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self) -> None:
        self.setWindowTitle("LolCamSwitcher — Client")
        self.setMinimumSize(560, 520)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        identity = QGroupBox("Identité joueur")
        id_layout = QFormLayout(identity)
        self.combo_player = QComboBox()
        self.combo_player.addItem("Joueur A", "A")
        self.combo_player.addItem("Joueur B", "B")
        idx = self.combo_player.findData(self.config.player_id)
        if idx >= 0:
            self.combo_player.setCurrentIndex(idx)
        id_layout.addRow("Slot :", self.combo_player)

        self.txt_summoner = QLineEdit(self.config.summoner_name)
        id_layout.addRow("Pseudo Riot :", self.txt_summoner)
        root.addWidget(identity)

        server = QGroupBox("Serveur régie (optionnel)")
        srv_layout = QFormLayout(server)

        self.chk_relay = QCheckBox("Relayer les events vers le serveur")
        self.chk_relay.setChecked(self.config.relay_enabled)
        srv_layout.addRow(self.chk_relay)

        self.txt_server_url = QLineEdit(self.config.server_url)
        self.txt_server_url.setPlaceholderText("http://203.0.113.50 ou https://regie.example.com")
        srv_layout.addRow("URL serveur :", self.txt_server_url)

        self.txt_token = QLineEdit(self.config.api_token)
        self.txt_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_token.setPlaceholderText("Bearer token du serveur")
        srv_layout.addRow("Token API :", self.txt_token)

        srv_btns = QHBoxLayout()
        self.btn_test_server = QPushButton("Tester connexion serveur")
        self.btn_test_server.clicked.connect(self._test_server)
        srv_btns.addWidget(self.btn_test_server)
        srv_layout.addRow(srv_btns)

        root.addWidget(server)

        status = QGroupBox("État")
        st_layout = QFormLayout(status)
        self.lbl_lol = QLabel("—")
        self.lbl_server = QLabel("—")
        self.lbl_game_time = QLabel("00:00")
        self.lbl_last = QLabel("—")
        self.lbl_last.setWordWrap(True)
        st_layout.addRow("LoL :", self.lbl_lol)
        st_layout.addRow("Serveur :", self.lbl_server)
        st_layout.addRow("Temps de jeu :", self.lbl_game_time)
        st_layout.addRow("Dernier event :", self.lbl_last)
        root.addWidget(status)

        self.txt_events = QPlainTextEdit()
        self.txt_events.setReadOnly(True)
        self.txt_events.setMaximumBlockCount(500)
        self.txt_events.setFont(QFont("Consolas", 10))
        self.txt_events.setPlaceholderText("Events live (fonctionne sans serveur)…")
        root.addWidget(self.txt_events)

        btns = QHBoxLayout()
        self.btn_start = QPushButton("Démarrer")
        self.btn_start.clicked.connect(self._start)
        self.btn_stop = QPushButton("Arrêter")
        self.btn_stop.clicked.connect(self._stop)
        btns.addWidget(self.btn_start)
        btns.addWidget(self.btn_stop)
        root.addLayout(btns)

        self.statusBar().showMessage(
            "Mode standalone : events locaux sans serveur. Activez le relay pour la régie distante."
        )

    def _setup_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(500)

    def _apply_config(self) -> None:
        self.config.player_id = self.combo_player.currentData()
        self.config.summoner_name = self.txt_summoner.text().strip()
        self.config.server_url = self.txt_server_url.text().strip()
        self.config.api_token = self.txt_token.text().strip()
        self.config.relay_enabled = self.chk_relay.isChecked()
        self.engine.apply_config(self.config)

    def _start(self) -> None:
        self._apply_config()
        self.engine.start()
        mode = "relay" if self.config.relay_configured else "standalone"
        self.statusBar().showMessage(f"Client démarré — mode {mode}")

    def _stop(self) -> None:
        self.engine.stop()
        self.statusBar().showMessage("Client arrêté")

    def _test_server(self) -> None:
        self._apply_config()
        if self.engine.test_server_connection():
            self.statusBar().showMessage("Serveur OK — token valide")
        else:
            err = self.engine.relay.last_error or "unknown"
            self.statusBar().showMessage(f"Serveur KO — {err}")

    def _append_event_line(self, line: str) -> None:
        self.txt_events.appendPlainText(line)

    def _refresh_status(self) -> None:
        self.lbl_lol.setText("✓ connecté" if self.engine.lol_connected else "✗ hors partie")
        if not self.config.relay_configured:
            self.lbl_server.setText("— (standalone)")
        elif self.engine.server_connected:
            self.lbl_server.setText("✓ connecté")
        else:
            self.lbl_server.setText("✗")

        gt = self.engine.game_time
        self.lbl_game_time.setText(f"{int(gt // 60):02d}:{int(gt % 60):02d}")
        last = self.engine.last_event
        self.lbl_last.setText(str(last) if last else "—")

    def closeEvent(self, event) -> None:
        self.engine.stop()
        super().closeEvent(event)


def run_client(config: ClientConfig | None = None) -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ClientWindow(config)
    window.show()
    return app.exec()

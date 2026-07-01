"""PySide6 GUI for LoL Auto Director."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from lol_auto_director.config import AppConfig
from lol_auto_director.director.priority import FocusTarget
from lol_auto_director.director.strategy import STRATEGY_LABELS, SwitchStrategy
from lol_auto_director.engine import DirectorEngine
from lol_auto_director.lol.events import EventType


FOCUS_LABELS = {
    FocusTarget.PLAYER_A: "Joueur A",
    FocusTarget.PLAYER_B: "Joueur B",
    FocusTarget.SPLIT_SCREEN: "Écran partagé",
}


class _LogBridge(QObject):
    line_added = Signal(str)


class DirectorWindow(QMainWindow):
    def __init__(self, config: AppConfig | None = None):
        super().__init__()
        self.config = config or AppConfig()
        self._log_bridge = _LogBridge()
        self._log_bridge.line_added.connect(self._append_live_log)
        self.engine = DirectorEngine(
            config=self.config,
            on_state_changed=self._refresh_ui,
            on_log_line=self._log_bridge.line_added.emit,
        )
        self._log_view_mode = "live"
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self) -> None:
        self.setWindowTitle("LoL Auto Director")
        self.setMinimumSize(640, 720)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # Status panel
        status_group = QGroupBox("État de la régie")
        status_layout = QFormLayout(status_group)

        self.lbl_focus = QLabel("—")
        self.lbl_focus.setFont(QFont("", 16, QFont.Weight.Bold))
        status_layout.addRow("Focus actuel :", self.lbl_focus)

        self.lbl_score_a = QLabel("0")
        self.lbl_score_b = QLabel("0")
        status_layout.addRow("Score A :", self.lbl_score_a)
        status_layout.addRow("Score B :", self.lbl_score_b)

        self.lbl_last_event = QLabel("—")
        self.lbl_last_event.setWordWrap(True)
        status_layout.addRow("Dernier événement :", self.lbl_last_event)

        self.lbl_delay = QLabel(f"-{self.config.pre_event_delay:.1f}s")
        status_layout.addRow("Délai pré-événement :", self.lbl_delay)

        self.lbl_strategy = QLabel("—")
        status_layout.addRow("Stratégie :", self.lbl_strategy)

        self.lbl_game_time = QLabel("00:00")
        status_layout.addRow("Temps de jeu :", self.lbl_game_time)

        root.addWidget(status_group)

        # Connection settings
        conn_group = QGroupBox("Connexions")
        conn_layout = QFormLayout(conn_group)

        self.txt_player_a = QLineEdit(self.config.player_a.summoner_name)
        self.txt_player_b = QLineEdit(self.config.player_b.summoner_name)
        conn_layout.addRow("Joueur A (Riot) :", self.txt_player_a)
        conn_layout.addRow("Joueur B (Riot) :", self.txt_player_b)

        obs_row = QHBoxLayout()
        self.txt_obs_host = QLineEdit(self.config.obs_host)
        self.spin_obs_port = QSpinBox()
        self.spin_obs_port.setRange(1, 65535)
        self.spin_obs_port.setValue(self.config.obs_port)
        obs_row.addWidget(self.txt_obs_host)
        obs_row.addWidget(self.spin_obs_port)
        conn_layout.addRow("OBS (host:port) :", obs_row)

        self.txt_obs_password = QLineEdit(self.config.obs_password)
        self.txt_obs_password.setEchoMode(QLineEdit.EchoMode.Password)
        conn_layout.addRow("Mot de passe OBS :", self.txt_obs_password)

        root.addWidget(conn_group)

        # Strategy & timing
        strat_group = QGroupBox("Stratégie & timing")
        strat_layout = QFormLayout(strat_group)

        self.combo_strategy = QComboBox()
        for strategy, label in STRATEGY_LABELS.items():
            self.combo_strategy.addItem(label, strategy)
        current_idx = self.combo_strategy.findData(self.config.switch_strategy)
        if current_idx >= 0:
            self.combo_strategy.setCurrentIndex(current_idx)
        self.combo_strategy.currentIndexChanged.connect(self._on_strategy_changed)
        strat_layout.addRow("Stratégie de switch :", self.combo_strategy)

        self.combo_main_player = QComboBox()
        self.combo_main_player.addItem("Joueur A", "A")
        self.combo_main_player.addItem("Joueur B", "B")
        main_idx = self.combo_main_player.findData(self.config.main_player)
        if main_idx >= 0:
            self.combo_main_player.setCurrentIndex(main_idx)
        self.combo_main_player.currentIndexChanged.connect(self._on_main_player_changed)
        strat_layout.addRow("Joueur principal :", self.combo_main_player)

        self.spin_pre_delay = QDoubleSpinBox()
        self.spin_pre_delay.setRange(0.0, 30.0)
        self.spin_pre_delay.setSingleStep(0.5)
        self.spin_pre_delay.setSuffix(" s")
        self.spin_pre_delay.setValue(self.config.pre_event_delay)
        self.spin_pre_delay.valueChanged.connect(self._on_pre_delay_changed)
        strat_layout.addRow("Délai avant action :", self.spin_pre_delay)

        root.addWidget(strat_group)

        # Controls
        ctrl_group = QGroupBox("Contrôles")
        ctrl_layout = QVBoxLayout(ctrl_group)

        self.chk_auto = QCheckBox("Mode automatique")
        self.chk_auto.setChecked(self.config.auto_mode)
        self.chk_auto.stateChanged.connect(self._on_auto_changed)
        ctrl_layout.addWidget(self.chk_auto)

        btn_row = QHBoxLayout()

        self.btn_connect_obs = QPushButton("Connecter OBS")
        self.btn_connect_obs.clicked.connect(self._connect_obs)
        btn_row.addWidget(self.btn_connect_obs)

        self.btn_start = QPushButton("Démarrer")
        self.btn_start.clicked.connect(self._start_engine)
        btn_row.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Arrêter")
        self.btn_stop.clicked.connect(self._stop_engine)
        btn_row.addWidget(self.btn_stop)

        ctrl_layout.addLayout(btn_row)

        manual_row = QHBoxLayout()
        self.btn_replay = QPushButton("Replay dernier événement")
        self.btn_replay.clicked.connect(self._replay_last)
        manual_row.addWidget(self.btn_replay)

        self.btn_manual_a = QPushButton("→ Joueur A")
        self.btn_manual_a.clicked.connect(lambda: self._manual_switch(FocusTarget.PLAYER_A))
        manual_row.addWidget(self.btn_manual_a)

        self.btn_manual_b = QPushButton("→ Joueur B")
        self.btn_manual_b.clicked.connect(lambda: self._manual_switch(FocusTarget.PLAYER_B))
        manual_row.addWidget(self.btn_manual_b)

        ctrl_layout.addLayout(manual_row)

        # Test events (dev/demo without live game)
        test_row = QHBoxLayout()
        self.btn_test_kill_a = QPushButton("Test Kill A")
        self.btn_test_kill_a.clicked.connect(
            lambda: self._inject_test(EventType.KILL, "A")
        )
        test_row.addWidget(self.btn_test_kill_a)

        self.btn_test_kill_b = QPushButton("Test Kill B")
        self.btn_test_kill_b.clicked.connect(
            lambda: self._inject_test(EventType.KILL, "B")
        )
        test_row.addWidget(self.btn_test_kill_b)

        self.btn_test_split = QPushButton("Test Split")
        self.btn_test_split.clicked.connect(self._inject_split_test)
        test_row.addWidget(self.btn_test_split)

        ctrl_layout.addLayout(test_row)
        root.addWidget(ctrl_group)

        # Session log viewer
        log_group = QGroupBox("Journal de partie")
        log_layout = QVBoxLayout(log_group)

        log_toolbar = QHBoxLayout()
        self.combo_log_files = QComboBox()
        self.combo_log_files.setMinimumWidth(220)
        self.combo_log_files.currentIndexChanged.connect(self._on_log_file_selected)
        log_toolbar.addWidget(QLabel("Fichier :"))
        log_toolbar.addWidget(self.combo_log_files, stretch=1)

        self.btn_log_live = QPushButton("Live")
        self.btn_log_live.setCheckable(True)
        self.btn_log_live.setChecked(True)
        self.btn_log_live.clicked.connect(self._show_live_log)
        log_toolbar.addWidget(self.btn_log_live)

        self.btn_log_refresh = QPushButton("Actualiser")
        self.btn_log_refresh.clicked.connect(self._refresh_log_file_list)
        log_toolbar.addWidget(self.btn_log_refresh)

        self.btn_log_open_folder = QPushButton("Ouvrir dossier")
        self.btn_log_open_folder.clicked.connect(self._open_logs_folder)
        log_toolbar.addWidget(self.btn_log_open_folder)

        log_layout.addLayout(log_toolbar)

        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(3000)
        self.txt_log.setPlaceholderText("Les events et changements de caméra apparaîtront ici…")
        self.txt_log.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.txt_log)

        self.lbl_log_path = QLabel("")
        self.lbl_log_path.setWordWrap(True)
        log_layout.addWidget(self.lbl_log_path)

        root.addWidget(log_group)

        self._refresh_log_file_list()
        self.statusBar().showMessage("Prêt")

    def _setup_timer(self) -> None:
        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._refresh_ui)
        self._ui_timer.start(250)

    def _apply_config(self) -> None:
        self.config.player_a.summoner_name = self.txt_player_a.text().strip()
        self.config.player_b.summoner_name = self.txt_player_b.text().strip()
        self.config.obs_host = self.txt_obs_host.text().strip()
        self.config.obs_port = self.spin_obs_port.value()
        self.config.obs_password = self.txt_obs_password.text()
        self.engine.riot_api.player_a_name = self.config.player_a.summoner_name.lower()
        self.engine.riot_api.player_b_name = self.config.player_b.summoner_name.lower()
        self.engine.obs.host = self.config.obs_host
        self.engine.obs.port = self.config.obs_port
        self.engine.obs.password = self.config.obs_password
        self.engine.apply_settings(
            pre_event_delay=self.spin_pre_delay.value(),
            switch_strategy=self.combo_strategy.currentData(),
            main_player=self.combo_main_player.currentData(),
        )

    def _on_strategy_changed(self) -> None:
        strategy = self.combo_strategy.currentData()
        is_main = strategy == SwitchStrategy.ONE_MAIN_PLAYER
        self.combo_main_player.setEnabled(is_main)
        self.engine.apply_settings(
            switch_strategy=strategy,
            main_player=self.combo_main_player.currentData(),
        )

    def _on_main_player_changed(self) -> None:
        self.engine.apply_settings(main_player=self.combo_main_player.currentData())

    def _on_pre_delay_changed(self, value: float) -> None:
        self.lbl_delay.setText(f"-{value:.1f}s")
        self.engine.apply_settings(pre_event_delay=value)

    def _connect_obs(self) -> None:
        self._apply_config()
        if self.engine.connect_obs():
            self.statusBar().showMessage("OBS connecté")
        else:
            QMessageBox.warning(self, "OBS", "Impossible de se connecter à OBS WebSocket v5.")

    def _start_engine(self) -> None:
        self._apply_config()
        self.engine.start()
        self.statusBar().showMessage("Moteur démarré — en attente de partie LoL")

    def _stop_engine(self) -> None:
        self.engine.stop()
        self.statusBar().showMessage("Moteur arrêté")

    def _on_auto_changed(self, state: int) -> None:
        self.engine.auto_mode = state == int(Qt.CheckState.Checked)

    def _replay_last(self) -> None:
        self.engine.replay_last_event()
        self.statusBar().showMessage("Replay du dernier événement")

    def _manual_switch(self, target: FocusTarget) -> None:
        self.engine.manual_switch(target)
        self._refresh_ui()

    def _append_live_log(self, line: str) -> None:
        if self._log_view_mode != "live":
            return
        self.txt_log.appendPlainText(line)
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _show_live_log(self) -> None:
        self._log_view_mode = "live"
        self.btn_log_live.setChecked(True)
        self.combo_log_files.blockSignals(True)
        self.combo_log_files.setCurrentIndex(-1)
        self.combo_log_files.blockSignals(False)
        self.txt_log.setPlainText("\n".join(self.engine.game_log.live_lines))
        path = self.engine.current_log_file
        self.lbl_log_path.setText(f"Live — {path}" if path else "Live — en attente de partie")

    def _refresh_log_file_list(self) -> None:
        files = self.engine.game_log.list_log_files()
        self.combo_log_files.blockSignals(True)
        self.combo_log_files.clear()
        self.combo_log_files.addItem("( sélectionner un fichier )", None)
        for f in files:
            self.combo_log_files.addItem(f.name, f)
        self.combo_log_files.blockSignals(False)
        if self._log_view_mode == "live":
            self._show_live_log()

    def _on_log_file_selected(self, index: int) -> None:
        if index <= 0:
            return
        path = self.combo_log_files.itemData(index)
        if path is None:
            return
        self._log_view_mode = "file"
        self.btn_log_live.setChecked(False)
        content = self.engine.game_log.read_log_file(path)
        self.txt_log.setPlainText(content)
        self.lbl_log_path.setText(str(path))

    def _open_logs_folder(self) -> None:
        import subprocess

        folder = str(self.engine.logs_dir)
        if sys.platform == "win32":
            subprocess.run(["explorer", folder], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)

    def _inject_test(self, event_type: EventType, player: str) -> None:
        t = self.engine.game_time or 600.0
        self.engine.inject_test_event(event_type, player, t + 1)
        self.statusBar().showMessage(f"Événement test injecté : {event_type.value} ({player})")

    def _inject_split_test(self) -> None:
        t = self.engine.game_time or 600.0
        self.engine.inject_test_event(EventType.KILL, "A", t + 1)
        self.engine.inject_test_event(EventType.KILL, "B", t + 3)
        self.statusBar().showMessage("Test split screen — kills A et B")

    def _refresh_ui(self) -> None:
        focus = self.engine.current_focus
        self.lbl_focus.setText(FOCUS_LABELS.get(focus, str(focus)))
        self.lbl_score_a.setText(f"{self.engine.score_a:.0f}")
        self.lbl_score_b.setText(f"{self.engine.score_b:.0f}")

        last = self.engine.last_event
        self.lbl_last_event.setText(str(last) if last else "—")

        gt = self.engine.game_time
        minutes = int(gt // 60)
        seconds = int(gt % 60)
        self.lbl_game_time.setText(f"{minutes:02d}:{seconds:02d}")

        strategy = self.engine.switch_strategy
        self.lbl_strategy.setText(STRATEGY_LABELS.get(strategy, str(strategy)))
        self.combo_main_player.setEnabled(strategy == SwitchStrategy.ONE_MAIN_PLAYER)

        obs_status = "OBS ✓" if self.engine.obs_connected else "OBS ✗"
        riot_status = "LoL ✓" if self.engine.riot_connected else "LoL ✗"
        auto = "AUTO" if self.engine.auto_mode else "MANUEL"
        log_hint = self.engine.current_log_file
        log_name = log_hint.name if log_hint else "—"
        self.statusBar().showMessage(f"{obs_status} | {riot_status} | {auto} | log: {log_name}")

    def closeEvent(self, event) -> None:
        self.engine.stop()
        super().closeEvent(event)


def run_app(config: AppConfig | None = None) -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = DirectorWindow(config)
    window.show()
    return app.exec()

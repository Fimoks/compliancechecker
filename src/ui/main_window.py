import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem, QProgressBar,
    QTabWidget, QTextEdit, QLabel, QStatusBar, QHeaderView,
    QMessageBox, QGroupBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from core.engine import ComplianceEngine

class CheckWorker(QThread):
    progress = Signal(int, int)
    result_ready = Signal(dict)
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.checkers = []

    def set_checkers(self, checkers):
        self.checkers = checkers

    def run(self):
        total = len(self.checkers)
        for i, checker in enumerate(self.checkers):
            try:
                result = checker.check()
                self.result_ready.emit(result)
            except Exception as e:
                self.result_ready.emit({
                    'id': getattr(checker, 'rule_id', 'UNKNOWN'),
                    'name': getattr(checker, 'name', 'Неизвестная проверка'),
                    'status': False,
                    'value': None,
                    'message': f"Ошибка: {str(e)}",
                    'severity': getattr(checker, 'severity', 'medium')
                })
            self.progress.emit(i + 1, total)
        self.finished.emit()

class ComplianceCheckerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compliance Checker 152-ФЗ")
        self.setMinimumSize(1000, 700)
        self.results = []
        self.security_level = 4
        self.check_worker = None
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header = QHBoxLayout()
        title = QLabel("🛡️ COMPLIANCE CHECKER 152-ФЗ")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        about_btn = QPushButton("📖 О программе")
        about_btn.clicked.connect(self._show_about)
        header.addWidget(about_btn)
        layout.addLayout(header)

        self._setup_level_selector(layout)

        self.start_btn = QPushButton("▶ НАЧАТЬ ПРОВЕРКУ")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.clicked.connect(self._start_check)
        layout.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.tab_widget = QTabWidget()
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Проверка", "Статус", "Значение", "Рекомендация"])
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.results_tree.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tab_widget.addTab(self.results_tree, "📋 Результаты")

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.tab_widget.addTab(self.log_text, "📜 Лог")

        layout.addWidget(self.tab_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к проверке. Выберите уровень и нажмите «Начать проверку»")

    def _setup_level_selector(self, layout):
        group_box = QGroupBox("Уровень защищённости информационной системы")
        group_layout = QVBoxLayout()
        self.level_group = QButtonGroup(self)
        self.rb_level4 = QRadioButton("УЗ-4 (базовый) — для малого бизнеса, ИП")
        self.rb_level3 = QRadioButton("УЗ-3 (средний) — для большинства организаций")
        self.rb_level2 = QRadioButton("УЗ-2 (повышенный) — для крупных компаний")
        self.rb_level1 = QRadioButton("УЗ-1 (максимальный) — для спецсубъектов, гостайна")
        self.rb_level4.setChecked(True)
        self.level_group.addButton(self.rb_level4, 4)
        self.level_group.addButton(self.rb_level3, 3)
        self.level_group.addButton(self.rb_level2, 2)
        self.level_group.addButton(self.rb_level1, 1)
        self.level_group.buttonClicked.connect(self._on_level_changed)
        group_layout.addWidget(self.rb_level4)
        group_layout.addWidget(self.rb_level3)
        group_layout.addWidget(self.rb_level2)
        group_layout.addWidget(self.rb_level1)
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

    def _on_level_changed(self, button):
        self.security_level = self.level_group.id(button)
        self.status_bar.showMessage(f"Выбран уровень: УЗ-{self.security_level}")

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QPushButton { background-color: #0d7377; color: white; border: none; border-radius: 5px; padding: 10px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #14a085; }
            QTreeWidget { background-color: #1e1e1e; alternate-background-color: #252525; color: #e0e0e0; outline: none; }
            QTreeWidget::item { padding: 5px; }
            QTreeWidget::item:selected { background-color: #0d7377; }
            QHeaderView::section { background-color: #3c3c3c; color: white; padding: 5px; border: none; }
            QTabWidget::pane { background-color: #1e1e1e; border: 1px solid #3c3c3c; }
            QTabBar::tab { background-color: #3c3c3c; color: white; padding: 8px 15px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #0d7377; }
            QTextEdit { background-color: #1e1e1e; color: #e0e0e0; font-family: Consolas; }
            QLabel { color: #e0e0e0; }
            QGroupBox { color: #e0e0e0; border: 1px solid #3c3c3c; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QRadioButton { color: #e0e0e0; }
            QProgressBar { background-color: #3c3c3c; border-radius: 5px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #0d7377; border-radius: 5px; }
        """)

    def _log(self, message):
        from datetime import datetime
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def _show_about(self):
        QMessageBox.about(self, "О программе",
            "Compliance Checker 152-ФЗ\n\nВерсия: 1.0\n\n"
            "Программа автоматической проверки защищённости рабочей станции\n"
            "на соответствие требованиям 152-ФЗ и Приказа ФСТЭК №21.\n\n"
            "Разработано для магистерской диссертации\n© 2026")

    def _start_check(self):
        self.results_tree.clear()
        self.log_text.clear()
        self.results = []
        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self._log("=" * 50)
        self._log(f"ЗАПУСК ПРОВЕРКИ (УЗ-{self.security_level})")
        self._log("=" * 50)
        
        engine = ComplianceEngine(security_level=self.security_level)
        checkers = engine.get_active_checkers()
        self._log(f"Всего проверок: {len(checkers)}")
        
        self.check_worker = CheckWorker()
        self.check_worker.set_checkers(checkers)
        self.check_worker.progress.connect(self._update_progress)
        self.check_worker.result_ready.connect(self._add_result)
        self.check_worker.finished.connect(self._check_finished)  # ← ТОЛЬКО ОДИН РАЗ
        self.check_worker.start()

    def _update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"Выполняется проверка: {current} из {total}")

    def _add_result(self, result):
        self.results.append(result)
        status_text = "✅ Пройдено" if result['status'] else "❌ Не пройдено"
        item = QTreeWidgetItem()
        item.setText(0, f"{result.get('id', '???')}: {result.get('name', 'Неизвестно')}")
        item.setText(1, status_text)
        val = str(result.get('value', ''))
        if len(val) > 100:
            val = val[:100] + "..."
        item.setText(2, val)
        rec = result.get('message', '')
        if not rec and not result['status']:
            rec = "Требуется настройка"
        item.setText(3, rec[:150])
        self.results_tree.addTopLevelItem(item)
        self._log(f"{result.get('id', '???')}: {'✓' if result['status'] else '✗'} - {result.get('name', 'Неизвестно')}")

    def _check_finished(self):
        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        passed = sum(1 for r in self.results if r['status'])
        total = len(self.results)
        percent = (passed * 100 // total) if total > 0 else 0
        
        # Очищаем лог от дублирования — выводим только один раз
        self._log("=" * 50)
        self._log(f"ПРОВЕРКА ЗАВЕРШЕНА. Пройдено: {passed} из {total} ({percent}%)")
        self.status_bar.showMessage(f"Проверка завершена. Пройдено: {passed} из {total} ({percent}%)")
        
        if passed < total:
            self._log("⚠️ Нарушения:")
            for r in self.results:
                if not r['status'] and r.get('message'):
                    self._log(f"  • {r.get('id', '???')}: {r.get('message', '')[:100]}")
        
        self._log("=" * 50)


def main():
    app = QApplication([])
    window = ComplianceCheckerWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
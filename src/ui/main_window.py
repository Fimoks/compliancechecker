import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem, QProgressBar,
    QTabWidget, QTextEdit, QLabel, QStatusBar, QHeaderView,
    QMessageBox, QGroupBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
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
        self.include_manual_checks = False  # False = только авто, True = авто + ручные
        self.check_worker = None
        self._check_finished_flag = False
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

        # Панель настроек в одной строке
        settings_layout = QHBoxLayout()
        self._setup_level_selector(settings_layout)
        self._setup_check_type_selector(settings_layout)
        layout.addLayout(settings_layout)

        self.start_btn = QPushButton("▶ НАЧАТЬ ПРОВЕРКУ")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.clicked.connect(self._start_check)
        layout.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # ========== ВКЛАДКИ ==========
        self.tab_widget = QTabWidget()
        
        # --- Вкладка 1: Сводка ---
        self.summary_widget = QWidget()
        self.summary_layout = QVBoxLayout(self.summary_widget)
        
        # Сообщение "Нет данных" (показывается до проверки)
        self.summary_empty_label = QLabel("📋 Нет данных для отображения\n\nЗапустите проверку, чтобы увидеть сводку")
        self.summary_empty_label.setFont(QFont("Arial", 14))
        self.summary_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_empty_label.setStyleSheet("color: #888888; padding: 50px;")
        self.summary_layout.addWidget(self.summary_empty_label)
        
        # Контейнер с данными (скрыт до проверки)
        self.summary_data_widget = QWidget()
        self.summary_data_layout = QVBoxLayout(self.summary_data_widget)
        
        # Общий статус
        self.summary_status_label = QLabel()
        self.summary_status_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.summary_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_data_layout.addWidget(self.summary_status_label)
        
        # Процент соответствия
        self.percent_label = QLabel()
        self.percent_label.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_data_layout.addWidget(self.percent_label)
        
        # Статистика
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Arial", 12))
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_data_layout.addWidget(self.stats_label)
        
        # Результаты по категориям
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels(["Категория", "Пройдено", "Всего", "Статус"])
        self.category_tree.setAlternatingRowColors(True)
        self.category_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.category_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.category_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.category_tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.summary_data_layout.addWidget(self.category_tree)
        
        self.summary_data_layout.addStretch()
        self.summary_layout.addWidget(self.summary_data_widget)
        
        # Изначально показываем пустое сообщение, скрываем данные
        self.summary_empty_label.setVisible(True)
        self.summary_data_widget.setVisible(False)
        
        self.tab_widget.addTab(self.summary_widget, "📊 Сводка")
        
        # --- Вкладка 2: Результаты (детально) ---
        self.results_tree = QTreeWidget()
        self.results_tree.setWordWrap(True)
        self.results_tree.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.results_tree.setItemsExpandable(False)
        self.results_tree.setUniformRowHeights(False)
        self.results_tree.setHeaderLabels(["Проверка", "Статус", "Значение", "Рекомендация"])
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.results_tree.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tab_widget.addTab(self.results_tree, "📋 Результаты")
        
        # --- Вкладка 3: Лог ---
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.tab_widget.addTab(self.log_text, "📜 Лог")
        
        layout.addWidget(self.tab_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к проверке. Выберите уровень, тип проверок и нажмите «Начать проверку»")

    def _setup_level_selector(self, layout):
        group_box = QGroupBox("Уровень защищённости")
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

    def _setup_check_type_selector(self, layout):
        group_box = QGroupBox("Тип проверок")
        group_layout = QVBoxLayout()
        self.check_type_group = QButtonGroup(self)
        self.rb_auto_only = QRadioButton("Только автоматические")
        self.rb_auto_manual = QRadioButton("Автоматические + ручные")
        self.rb_auto_only.setChecked(True)
        self.check_type_group.addButton(self.rb_auto_only, 0)
        self.check_type_group.addButton(self.rb_auto_manual, 1)
        self.check_type_group.buttonClicked.connect(self._on_check_type_changed)
        group_layout.addWidget(self.rb_auto_only)
        group_layout.addWidget(self.rb_auto_manual)
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

    def _on_check_type_changed(self, button):
        self.include_manual_checks = (self.check_type_group.id(button) == 1)
        mode = "авто + ручные" if self.include_manual_checks else "только авто"
        self.status_bar.showMessage(f"Выбран режим: {mode}, уровень: УЗ-{self.security_level}")

    def _on_level_changed(self, button):
        self.security_level = self.level_group.id(button)
        mode = "авто + ручные" if self.include_manual_checks else "только авто"
        self.status_bar.showMessage(f"Выбран уровень: УЗ-{self.security_level}, режим: {mode}")

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

    def _update_summary(self):
        """Обновляет сводку по результатам проверки"""
        total = len(self.results)
        
        if total == 0:
            self.summary_empty_label.setVisible(True)
            self.summary_data_widget.setVisible(False)
            return
        else:
            self.summary_empty_label.setVisible(False)
            self.summary_data_widget.setVisible(True)
        
        passed = sum(1 for r in self.results if r['status'])
        percent = (passed * 100 // total) if total > 0 else 0
        
        # Общий статус
        if percent == 100:
            status = "✅ СООТВЕТСТВУЕТ"
            status_color = "#4caf50"
        elif percent >= 70:
            status = "⚠️ ЧАСТИЧНО СООТВЕТСТВУЕТ"
            status_color = "#ff9800"
        else:
            status = "❌ НЕ СООТВЕТСТВУЕТ"
            status_color = "#f44336"
        
        self.summary_status_label.setText(status)
        self.summary_status_label.setStyleSheet(f"color: {status_color};")
        
        # Процент
        self.percent_label.setText(f"{percent}%")
        
        # Статистика
        self.stats_label.setText(f"Пройдено проверок: {passed} из {total}")
        
        # Группировка по категориям
        categories = {}
        for r in self.results:
            cat_id = r.get('id', '???').split('.')[0]
            if cat_id not in categories:
                categories[cat_id] = {'passed': 0, 'total': 0, 'name': r.get('name', cat_id)}
            categories[cat_id]['total'] += 1
            if r['status']:
                categories[cat_id]['passed'] += 1
        
        self.category_tree.clear()
        for cat_id, data in categories.items():
            item = QTreeWidgetItem()
            item.setText(0, f"{cat_id} — {data['name'][:50]}")
            item.setText(1, str(data['passed']))
            item.setText(2, str(data['total']))
            if data['passed'] == data['total']:
                status_text = "✅"
            elif data['passed'] > 0:
                status_text = "⚠️"
            else:
                status_text = "❌"
            item.setText(3, status_text)
            self.category_tree.addTopLevelItem(item)

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
        self._check_finished_flag = False
        self.results_tree.clear()
        self.log_text.clear()
        self.results = []
        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Очищаем сводку
        self.summary_status_label.setText("Проверка выполняется...")
        self.percent_label.setText("—")
        self.stats_label.setText("")
        self.category_tree.clear()
        
        self._log("=" * 50)
        self._log(f"ЗАПУСК ПРОВЕРКИ (УЗ-{self.security_level})")
        mode = "авто + ручные" if self.include_manual_checks else "только авто"
        self._log(f"Режим: {mode}")
        self._log("=" * 50)
        
        engine = ComplianceEngine(security_level=self.security_level)
        checkers = engine.get_active_checkers()
        self._log(f"Автоматических проверок: {len(checkers)}")
        
        if self.include_manual_checks:
            self._log("Ручные проверки (опросник) будут отображены после завершения автоматических")
        
        self.check_worker = CheckWorker()
        self.check_worker.set_checkers(checkers)
        self.check_worker.progress.connect(self._update_progress)
        self.check_worker.result_ready.connect(self._add_result)
        self.check_worker.finished.connect(self._check_finished)
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
        
        # Значение (без обрезания)
        val = str(result.get('value', ''))
        item.setText(2, val)
        
        # Рекомендация (без обрезания)
        rec = result.get('message', '')
        if not rec and not result['status']:
            rec = "Требуется настройка"
        item.setText(3, rec)
        
        self.results_tree.addTopLevelItem(item)
        
        # Принудительное обновление высоты строки для переноса
        for col in range(self.results_tree.columnCount()):
            self.results_tree.resizeColumnToContents(col)
        
        self._log(f"{result.get('id', '???')}: {'✓' if result['status'] else '✗'} - {result.get('name', 'Неизвестно')}")

    def _check_finished(self):
        if self._check_finished_flag:
            return
        self._check_finished_flag = True

        if self.check_worker:
            try:
                self.check_worker.finished.disconnect(self._check_finished)
            except RuntimeError:
                pass

        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        
        # Финальное обновление высоты всех строк
        for i in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(i)
            for col in range(self.results_tree.columnCount()):
                item.setSizeHint(col, self.results_tree.sizeHintForIndex(
                    self.results_tree.indexFromItem(item, col)
                ))
        
        # Обновляем сводку
        self._update_summary()
        
        passed = sum(1 for r in self.results if r['status'])
        total = len(self.results)
        percent = (passed * 100 // total) if total > 0 else 0
        
        self._log("=" * 50)
        self._log(f"ПРОВЕРКА ЗАВЕРШЕНА. Пройдено: {passed} из {total} ({percent}%)")
        self.status_bar.showMessage(f"Проверка завершена. Пройдено: {passed} из {total} ({percent}%)")
        
        if passed < total:
            self._log("⚠️ Нарушения:")
            for r in self.results:
                if not r['status'] and r.get('message'):
                    self._log(f"  • {r.get('id', '???')}: {r.get('message', '')[:100]}")
        
        self._log("=" * 50)
        
        # TODO: Если включены ручные проверки — показать опросник
        if self.include_manual_checks:
            self._log("Ручные проверки пока не реализованы. Будет добавлен опросник.")


def main():
    app = QApplication([])
    window = ComplianceCheckerWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
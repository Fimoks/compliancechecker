# main_window.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem, QProgressBar,
    QTabWidget, QTextEdit, QLabel, QStatusBar, QHeaderView,
    QMessageBox, QGroupBox, QRadioButton, QButtonGroup, QDialog,
    QScrollArea, QStackedWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer
from PySide6.QtGui import QFont, QColor

from core.engine import ComplianceEngine


# ============================================================================
# ДИАЛОГ ДЛЯ РУЧНЫХ ПРОВЕРОК
# ============================================================================

class ManualChecksDialog(QDialog):
    answers_saved = Signal(dict)
    
    def __init__(self, manual_checks, parent=None):
        super().__init__(parent)
        self.manual_checks = manual_checks
        self.answers = {}
        self.setWindowTitle("Ручные проверки")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        self._setup_ui()
        self._load_answers()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("✋ Ответьте на вопросы")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e0e0e0; margin: 10px;")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #2b2b2b;")
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Сохранить и завершить")
        self.cancel_btn = QPushButton("Отмена")
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.question_widgets = []
        for check in self.manual_checks:
            self._add_question_widget(check)
    
    def _add_question_widget(self, check):
        group = QGroupBox(f"{check['id']}: {check['name']}")
        group.setStyleSheet("""
            QGroupBox {
                color: #e0e0e0;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                margin-top: 10px;
                background-color: #1e1e1e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        group_layout = QVBoxLayout(group)
        
        question_label = QLabel(check['question'])
        question_label.setWordWrap(True)
        question_label.setStyleSheet("color: #e0e0e0; padding: 5px;")
        group_layout.addWidget(question_label)
        
        radio_layout = QHBoxLayout()
        radio_group = QButtonGroup(self)
        
        rb_yes = QRadioButton("✅ Да")
        rb_no = QRadioButton("❌ Нет")
        
        radio_style = """
            QRadioButton {
                color: #e0e0e0;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 13px;
                height: 13px;
                border-radius: 7px;
                border: 1px solid #888888;
                background-color: #2b2b2b;
            }
            QRadioButton::indicator:checked {
                border: 1px solid #0d7377;
                background-color: #0d7377;
            }
            QRadioButton::indicator:hover {
                border: 1px solid #14a085;
            }
        """
        rb_yes.setStyleSheet(radio_style)
        rb_no.setStyleSheet(radio_style)
        
        radio_group.addButton(rb_yes, 1)
        radio_group.addButton(rb_no, 0)
        
        radio_layout.addWidget(rb_yes)
        radio_layout.addWidget(rb_no)
        radio_layout.addStretch()
        group_layout.addLayout(radio_layout)
        
        self.scroll_layout.addWidget(group)
        
        self.question_widgets.append({
            'id': check['id'],
            'group': radio_group,
            'rb_yes': rb_yes,
            'rb_no': rb_no
        })
    
    def _load_answers(self):
        import json
        import os
        
        answers_file = "manual_answers.json"
        if os.path.exists(answers_file):
            try:
                with open(answers_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    for wid in self.question_widgets:
                        if wid['id'] in saved:
                            value = saved[wid['id']]
                            if value == 1:
                                wid['rb_yes'].setChecked(True)
                            elif value == 0:
                                wid['rb_no'].setChecked(True)
            except:
                pass
    
    def _save_answers(self):
        import json
        
        self.answers = {}
        for wid in self.question_widgets:
            if wid['rb_yes'].isChecked():
                self.answers[wid['id']] = 1
            elif wid['rb_no'].isChecked():
                self.answers[wid['id']] = 0
            else:
                self.answers[wid['id']] = -1
        
        with open("manual_answers.json", 'w', encoding='utf-8') as f:
            json.dump(self.answers, f, ensure_ascii=False, indent=2)
        
        return self.answers
    
    def _on_save(self):
        answers = self._save_answers()
        self.answers_saved.emit(answers)
        self.accept()


# ============================================================================
# ДИАЛОГ ДЛЯ ПОКАЗА ПОДРОБНОЙ ИНФОРМАЦИИ
# ============================================================================

class DetailsDialog(QDialog):
    def __init__(self, title, details, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Детали: {title}")
        self.setMinimumSize(550, 450)
        self.setModal(True)
        layout = QVBoxLayout(self)
        
        text_edit = QTextEdit()
        text_edit.setPlainText(details)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Consolas", 10))
        layout.addWidget(text_edit)
        
        btn_box = QHBoxLayout()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_box.addStretch()
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)


# ============================================================================
# ОСНОВНОЕ ОКНО ПРИЛОЖЕНИЯ
# ============================================================================

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
        self.include_manual_checks = False
        self.check_worker = None
        self._check_finished_flag = False
        self._last_category = None
        self._setup_ui()
        self._apply_styles()

    def _set_status_color(self, item, status):
        """Устанавливает цвет фона только для столбца 'Статус'"""
        if status:
            color = QColor(76, 175, 80, 50)  # пастельно-зеленый
        else:
            color = QColor(244, 67, 54, 50)  # пастельно-красный
        item.setBackground(3, color)  # столбец 3 - это "Статус" (после перемещения)
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header = QHBoxLayout()
        title = QLabel("🛡️ COMPLIANCE CHECKER 152-ФЗ")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #e0e0e0;")
        header.addWidget(title)
        header.addStretch()
        about_btn = QPushButton("📖 О программе")
        about_btn.clicked.connect(self._show_about)
        header.addWidget(about_btn)
        
        # Новая кнопка для сохранения Акта
        self.act_btn = QPushButton("📄 Сохранить Акт")
        self.act_btn.setEnabled(False)  # сначала неактивна, пока нет результатов
        self.act_btn.clicked.connect(self._save_act)
        header.addWidget(self.act_btn)
        
        layout.addLayout(header)

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

        self.tab_widget = QTabWidget()
        
        # --- Вкладка 1: Сводка ---
        self.summary_widget = QWidget()
        self.summary_layout = QVBoxLayout(self.summary_widget)
        
        self.summary_stacked = QStackedWidget()
        
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_label = QLabel("📋 Нет данных для отображения\n\nЗапустите проверку, чтобы увидеть сводку")
        empty_label.setFont(QFont("Arial", 14))
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #888888; padding: 50px;")
        empty_layout.addWidget(empty_label)
        self.summary_stacked.addWidget(empty_widget)
        
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        
        self.summary_status_label = QLabel()
        self.summary_status_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.summary_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        data_layout.addWidget(self.summary_status_label)
        
        self.percent_label = QLabel()
        self.percent_label.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        data_layout.addWidget(self.percent_label)
        
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Arial", 12))
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        data_layout.addWidget(self.stats_label)
        
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels(["Категория", "Пройдено", "Всего", "Статус"])
        self.category_tree.setAlternatingRowColors(True)
        self.category_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.category_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.category_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.category_tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        data_layout.addWidget(self.category_tree)
        
        self.summary_stacked.addWidget(data_widget)
        self.summary_layout.addWidget(self.summary_stacked)
        self.tab_widget.addTab(self.summary_widget, "📊 Сводка")
        
        # --- Вкладка 2: Результаты ---
        self.results_tree = QTreeWidget()
        self.results_tree.setWordWrap(True)
        self.results_tree.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.results_tree.setItemsExpandable(False)
        self.results_tree.setUniformRowHeights(False)
        self.results_tree.setIndentation(0)
        self.results_tree.setRootIsDecorated(False)
        self.results_tree.header().setStretchLastSection(True)
        self.results_tree.header().setMinimumSectionSize(0)
        self.results_tree.setStyleSheet("QTreeWidget::item { white-space: normal; }")
        self.results_tree.header().setSectionResizeMode(0, QHeaderView.Interactive)
        self.results_tree.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.results_tree.header().setSectionResizeMode(2, QHeaderView.Interactive)
        self.results_tree.header().setSectionResizeMode(3, QHeaderView.Stretch)
        
        # Устанавливаем заголовки столбцов в новом порядке: Проверка, Значение, Рекомендация, Статус
        self.results_tree.setHeaderLabels(["Проверка", "Значение", "Рекомендация", "Статус"])
        
        # Устанавливаем начальную ширину столбцов (в новом порядке)
        self.results_tree.setColumnWidth(0, 350)  # Проверка
        self.results_tree.setColumnWidth(1, 200)  # Значение
        self.results_tree.setColumnWidth(2, 300)  # Рекомендация
        self.results_tree.setColumnWidth(3, 100)  # Статус
        
        # Выравниваем заголовки по центру
        self.results_tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tab_widget.addTab(self.results_tree, "📋 Результаты")
        
        QTimer.singleShot(50, self._resize_columns)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # --- Вкладка 3: Лог ---
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.tab_widget.addTab(self.log_text, "📜 Лог")
        
        layout.addWidget(self.tab_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к проверке. Выберите уровень, тип проверок и нажмите «Начать проверку»")
        
        self.summary_stacked.setCurrentIndex(0)
        QTimer.singleShot(100, self._resize_columns)

    def _resize_columns(self):
        total_width = self.results_tree.viewport().width()
        if total_width <= 0:
            total_width = self.width() - 50
            if total_width < 200:
                total_width = 1000
        # Пропорции для нового порядка столбцов: [Проверка, Значение, Рекомендация, Статус]
        widths = [0.35, 0.20, 0.30, 0.15]  # 35%, 20%, 30%, 15%
        for col, ratio in enumerate(widths):
            self.results_tree.setColumnWidth(col, int(total_width * ratio))
        self.results_tree.header().updateGeometry()
        self.results_tree.updateGeometry()

    def _on_tab_changed(self, index):
        if index == 1:
            QTimer.singleShot(50, self._resize_columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_columns()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(50, self._resize_columns)

    def _setup_level_selector(self, layout):
        group_box = QGroupBox("Уровень защищённости")
        group_box.setStyleSheet("QGroupBox { color: #e0e0e0; border: 1px solid #3c3c3c; margin-top: 10px; }")
        group_layout = QVBoxLayout()
        self.level_group = QButtonGroup(self)
        
        rb_style = """
            QRadioButton {
                color: #e0e0e0;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 13px;
                height: 13px;
                border-radius: 7px;
                border: 1px solid #888888;
                background-color: #2b2b2b;
            }
            QRadioButton::indicator:checked {
                border: 1px solid #0d7377;
                background-color: #0d7377;
            }
            QRadioButton::indicator:hover {
                border: 1px solid #14a085;
            }
        """
        
        self.rb_level4 = QRadioButton("УЗ-4 (базовый) — для малого бизнеса, ИП")
        self.rb_level3 = QRadioButton("УЗ-3 (средний) — для большинства организаций")
        self.rb_level2 = QRadioButton("УЗ-2 (повышенный) — для крупных компаний")
        self.rb_level1 = QRadioButton("УЗ-1 (максимальный) — для спецсубъектов, гостайна")
        
        self.rb_level4.setStyleSheet(rb_style)
        self.rb_level3.setStyleSheet(rb_style)
        self.rb_level2.setStyleSheet(rb_style)
        self.rb_level1.setStyleSheet(rb_style)
        
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
        group_box.setStyleSheet("QGroupBox { color: #e0e0e0; border: 1px solid #3c3c3c; margin-top: 10px; }")
        group_layout = QVBoxLayout()
        self.check_type_group = QButtonGroup(self)
        
        rb_style = """
            QRadioButton {
                color: #e0e0e0;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 13px;
                height: 13px;
                border-radius: 7px;
                border: 1px solid #888888;
                background-color: #2b2b2b;
            }
            QRadioButton::indicator:checked {
                border: 1px solid #0d7377;
                background-color: #0d7377;
            }
            QRadioButton::indicator:hover {
                border: 1px solid #14a085;
            }
        """
        
        self.rb_auto_only = QRadioButton("Только автоматические")
        self.rb_auto_manual = QRadioButton("Автоматические + ручные")
        
        self.rb_auto_only.setStyleSheet(rb_style)
        self.rb_auto_manual.setStyleSheet(rb_style)
        
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
            QWidget { background-color: #2b2b2b; }
            QPushButton { background-color: #0d7377; color: white; border: none; border-radius: 5px; padding: 10px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #14a085; }
            QTreeWidget { background-color: #1e1e1e; alternate-background-color: #252525; color: #e0e0e0; outline: none; }
            QTreeWidget::item { padding: 5px; }
            QTreeWidget::item:selected { background-color: #0d7377; }
            QHeaderView::section { background-color: #3c3c3c; color: white; padding: 5px; border: none; }
            QHeaderView::section { text-align: center; }
            QTabWidget::pane { background-color: #1e1e1e; border: 1px solid #3c3c3c; }
            QTabBar::tab { background-color: #3c3c3c; color: white; padding: 8px 15px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #0d7377; }
            QTextEdit { background-color: #1e1e1e; color: #e0e0e0; font-family: Consolas; }
            QLabel { color: #e0e0e0; }
            QProgressBar { background-color: #3c3c3c; border-radius: 5px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #0d7377; border-radius: 5px; }
            QGroupBox { color: #e0e0e0; border: 1px solid #3c3c3c; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)

    def _update_summary(self):
        real_results = [r for r in self.results if r.get('status') is not None]
        total = len(real_results)
        
        if total == 0:
            self.summary_stacked.setCurrentIndex(0)
            return
        else:
            self.summary_stacked.setCurrentIndex(1)
        
        passed = sum(1 for r in real_results if r['status'])
        percent = (passed * 100 // total) if total > 0 else 0
        
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
        self.percent_label.setText(f"{percent}%")
        self.stats_label.setText(f"Пройдено проверок: {passed} из {total}")
        
        categories = {}
        for r in real_results:
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
    
    def _save_act(self):
        """Сохраняет Акт о готовности АРМ к работе с ПДн"""
        from datetime import datetime
        from reporting.act_generator import ActGenerator
        
        if not self.results:
            QMessageBox.warning(self, "Нет данных", 
                "Сначала выполните проверку")
            return
        
        try:
            # Фильтруем только реальные результаты (не заглушки)
            real_results = [r for r in self.results if r.get('status') is not None]
            
            generator = ActGenerator(
                results=real_results,
                security_level=self.security_level,
                system_info={
                    'computer_name': os.environ.get('COMPUTERNAME', 'UNKNOWN'),
                    'user_name': os.environ.get('USERNAME', 'UNKNOWN'),
                    'os': 'Windows',
                    'check_date': datetime.now().strftime("%d.%m.%Y"),
                    'check_time': datetime.now().strftime("%H:%M:%S")
                }
            )
            
            output_path = generator.generate()
            
            QMessageBox.information(self, "Акт сохранён", 
                f"Акт о готовности АРМ сохранён в файл:\n{output_path}")
            self._log(f"Акт сохранён: {output_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", 
                f"Не удалось сохранить Акт:\n{str(e)}")
            self._log(f"Ошибка сохранения Акта: {str(e)}")

    def _start_check(self):
        self._check_finished_flag = False
        self.results_tree.clear()
        self.log_text.clear()
        self.results = []
        self._last_category = None
        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.summary_status_label.setText("Проверка выполняется...")
        self.percent_label.setText("—")
        self.stats_label.setText("")
        self.category_tree.clear()
        self.summary_stacked.setCurrentIndex(1)
        
        self._log("=" * 50)
        self._log(f"ЗАПУСК ПРОВЕРКИ (УЗ-{self.security_level})")
        mode = "авто + ручные" if self.include_manual_checks else "только авто"
        self._log(f"Режим: {mode}")
        self._log("=" * 50)

        engine = ComplianceEngine(security_level=self.security_level, include_manual=self.include_manual_checks)
        checkers = engine.get_active_checkers()
        self._log(f"Всего проверок: {len(checkers)}")
        
        if self.include_manual_checks:
            manual_count = sum(1 for c in checkers if getattr(c, 'is_manual', False))
            self._log(f"Из них ручных: {manual_count}")
        
        self.check_worker = CheckWorker()
        self.check_worker.set_checkers(checkers)
        self.check_worker.progress.connect(self._update_progress)
        self.check_worker.result_ready.connect(self._add_result_with_grouping)
        self.check_worker.finished.connect(self._check_finished)
        self.check_worker.start()

    def _add_result_with_grouping(self, result):
        result_id = result.get('id', '???')
        category = result_id.split('.')[0] if '.' in result_id else result_id
        
        category_names = {
            "ИАФ": "I. Идентификация и аутентификация (ИАФ)",
            "УПД": "II. Управление доступом (УПД)",
            "ОПС": "III. Ограничение программной среды (ОПС)",
            "ЗНИ": "IV. Защита машинных носителей (ЗНИ)",
            "РСБ": "V. Регистрация событий безопасности (РСБ)",
            "АВЗ": "VI. Антивирусная защита (АВЗ)",
            "СОВ": "VII. Обнаружение вторжений (СОВ)",
            "АНЗ": "VIII. Контроль защищённости (АНЗ)",
            "ОЦЛ": "IX. Обеспечение целостности (ОЦЛ)",
            "ОДТ": "X. Обеспечение доступности (ОДТ)",
            "ЗСВ": "XI. Защита среды виртуализации (ЗСВ)",
            "ЗТС": "XII. Защита технических средств (ЗТС)",
            "ЗИС": "XIII. Защита ИС и связи (ЗИС)",
            "ИНЦ": "XIV. Выявление инцидентов (ИНЦ)",
            "УКФ": "XV. Управление конфигурацией (УКФ)",
        }
        
        if self._last_category != category:
            self._last_category = category
            header_name = category_names.get(category, category)
            self._add_header(header_name)
        
        self._add_result_item(result, add_to_list=True)
    
    def _add_header(self, header_name):
        item = QTreeWidgetItem()
        item.setText(0, header_name)
        font = QFont()
        font.setBold(True)
        item.setFont(0, font)
        for col in range(self.results_tree.columnCount()):
            item.setBackground(col, QColor(60, 60, 80))
        item.setFirstColumnSpanned(True)
        self.results_tree.addTopLevelItem(item)
        self.results_tree.scheduleDelayedItemsLayout()
    
    def _add_result_item(self, result, add_to_list=False):
        if add_to_list:
            self.results.append(result)
        status_text = "Пройдено" if result['status'] else "Не пройдено"
        item = QTreeWidgetItem()
        item.setText(0, f"{result.get('id', '???')}: {result.get('name', 'Неизвестно')}")
        item.setText(1, str(result.get('value', '')))  # Значение
        rec = result.get('message', '')
        if not rec and not result['status']:
            rec = "Требуется настройка"
        item.setText(2, rec)  # Рекомендация
        item.setText(3, status_text)  # Статус
        self.results_tree.addTopLevelItem(item)
        
        # Выравниваем текст в столбце "Статус" по центру
        item.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)
        
        self._set_status_color(item, result['status'])
        self.results_tree.scheduleDelayedItemsLayout()
        self._log(f"{result.get('id', '???')}: {'✓' if result['status'] else '✗'} - {result.get('name', 'Неизвестно')}")

    def _on_item_double_clicked(self, item, column):
        # Пропускаем заголовки групп
        if item.text(3) == "" and item.text(1) == "" and item.text(2) == "":
            return
        item_text = item.text(0)
        if ":" in item_text:
            check_id = item_text.split(":")[0].strip()
        else:
            check_id = item_text
        result = None
        for r in self.results:
            if r.get('id') == check_id:
                result = r
                break
        if not result:
            return
        details = f"""ID: {result.get('id', '???')}
Название: {result.get('name', 'Неизвестно')}
Статус: {'Пройдено' if result.get('status') else 'Не пройдено'}
Значение:
{result.get('value', '')}

Рекомендация:
{result.get('message', '')}
"""
        dialog = DetailsDialog(check_id, details, self)
        dialog.exec()

    def _update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"Выполняется проверка: {current} из {total}")

    def _show_manual_checks_dialog(self):
        self._log("Начало _show_manual_checks_dialog")
        manual_checks = [{'id': r['id'], 'name': r['name'], 'question': r['message']} for r in self.results if r.get('is_manual')]
        if not manual_checks:
            self._log("Нет ручных проверок для отображения")
            return
        dialog = ManualChecksDialog(manual_checks, self)
        dialog.answers_saved.connect(self._on_manual_answers_saved)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.exec()
    
    def _on_manual_answers_saved(self, answers):
        self._log("Начало обработки сохранённых ответов")
        for r in self.results:
            if r.get('is_manual') and r['id'] in answers and r.get('status') is not None:
                r['status'] = (answers[r['id']] == 1)
                r['message'] = "Пользователь подтвердил выполнение" if r['status'] else "Пользователь не подтвердил выполнение"
        
        self.results_tree.clear()
        self._last_category = None
        category_order = ["ИАФ", "УПД", "ОПС", "ЗНИ", "РСБ", "АВЗ", "СОВ", "АНЗ", "ОЦЛ", "ОДТ", "ЗСВ", "ЗТС", "ЗИС", "ИНЦ", "УКФ"]
        category_names = {
            "ИАФ": "I. Идентификация и аутентификация (ИАФ)",
            "УПД": "II. Управление доступом (УПД)",
            "ОПС": "III. Ограничение программной среды (ОПС)",
            "ЗНИ": "IV. Защита машинных носителей (ЗНИ)",
            "РСБ": "V. Регистрация событий безопасности (РСБ)",
            "АВЗ": "VI. Антивирусная защита (АВЗ)",
            "СОВ": "VII. Обнаружение вторжений (СОВ)",
            "АНЗ": "VIII. Контроль защищённости (АНЗ)",
            "ОЦЛ": "IX. Обеспечение целостности (ОЦЛ)",
            "ОДТ": "X. Обеспечение доступности (ОДТ)",
            "ЗСВ": "XI. Защита среды виртуализации (ЗСВ)",
            "ЗТС": "XII. Защита технических средств (ЗТС)",
            "ЗИС": "XIII. Защита ИС и связи (ЗИС)",
            "ИНЦ": "XIV. Выявление инцидентов (ИНЦ)",
            "УКФ": "XV. Управление конфигурацией (УКФ)",
        }
        real_results = [r for r in self.results if r.get('status') is not None]
        grouped = {}
        for r in real_results:
            cat = r['id'].split('.')[0]
            grouped.setdefault(cat, []).append(r)
        for cat in category_order:
            if cat in grouped:
                self._add_header(category_names.get(cat, cat))
                for r in grouped[cat]:
                    self._add_result_item(r, add_to_list=False)
        self._update_summary()
        self._log("Ручные проверки сохранены")
        QApplication.processEvents()

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
        for i in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(i)
            for col in range(self.results_tree.columnCount()):
                item.setSizeHint(col, self.results_tree.sizeHintForIndex(self.results_tree.indexFromItem(item, col)))
        QTimer.singleShot(50, self._resize_columns)
        self._update_summary()
        real_results = [r for r in self.results if r.get('status') is not None]
        passed = sum(1 for r in real_results if r['status'])
        total = len(real_results)
        percent = (passed * 100 // total) if total > 0 else 0
        self._log("=" * 50)
        self._log(f"ПРОВЕРКА ЗАВЕРШЕНА. Пройдено: {passed} из {total} ({percent}%)")
        self.status_bar.showMessage(f"Проверка завершена. Пройдено: {passed} из {total} ({percent}%)")
        if passed < total:
            self._log("⚠️ Нарушения:")
            for r in real_results:
                if not r['status'] and r.get('message'):
                    self._log(f"  • {r.get('id', '???')}: {r.get('message', '')[:100]}")
        self._log("=" * 50)
        QApplication.processEvents()
        
        # Активируем кнопку сохранения Акта (теперь есть результаты)
        self.act_btn.setEnabled(True)
        
        if self.include_manual_checks:
            self._show_manual_checks_dialog()


def main():
    app = QApplication([])
    window = ComplianceCheckerWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
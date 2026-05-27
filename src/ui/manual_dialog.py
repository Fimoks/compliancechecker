# src/ui/manual_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QScrollArea, QWidget,
    QGroupBox, QRadioButton, QButtonGroup, QPushButton,
    QLabel, QProgressBar, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal

class ManualChecksDialog(QDialog):
    """Модальное окно для ручных проверок"""
    
    # Сигнал, когда пользователь сохранил ответы
    answers_saved = Signal(dict)
    
    def __init__(self, manual_checks, parent=None):
        super().__init__(parent)
        self.manual_checks = manual_checks  # список ручных проверок
        self.answers = {}  # словарь ответов {id: status}
        self.setWindowTitle("Ручные проверки")
        self.setMinimumSize(600, 500)
        self.setModal(True)  # модальное окно
        self._setup_ui()
        self._load_answers()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Заголовок
        title = QLabel("✋ Ответьте на вопросы")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Область прокрутки с вопросами
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Сохранить и завершить")
        self.cancel_btn = QPushButton("Отмена")
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # Создаём виджеты для каждого вопроса
        self.question_widgets = []
        for check in self.manual_checks:
            self._add_question_widget(check)
        
        self._update_progress()
    
    def _add_question_widget(self, check):
        """Создаёт виджет для одного вопроса"""
        group = QGroupBox(f"{check['id']}: {check['name']}")
        group_layout = QVBoxLayout(group)
        
        question_label = QLabel(check['question'])
        question_label.setWordWrap(True)
        group_layout.addWidget(question_label)
        
        # Радиокнопки Да/Нет
        radio_layout = QHBoxLayout()
        radio_group = QButtonGroup(self)
        
        rb_yes = QRadioButton("✅ Да")
        rb_no = QRadioButton("❌ Нет")
        rb_unknown = QRadioButton("❓ Не знаю")
        
        radio_group.addButton(rb_yes, 1)
        radio_group.addButton(rb_no, 0)
        radio_group.addButton(rb_unknown, -1)
        
        radio_layout.addWidget(rb_yes)
        radio_layout.addWidget(rb_no)
        radio_layout.addWidget(rb_unknown)
        radio_layout.addStretch()
        group_layout.addLayout(radio_layout)
        
        self.scroll_layout.addWidget(group)
        
        # Сохраняем виджеты для доступа
        self.question_widgets.append({
            'id': check['id'],
            'group': radio_group,
            'rb_yes': rb_yes,
            'rb_no': rb_no,
            'rb_unknown': rb_unknown
        })
    
    def _load_answers(self):
        """Загружает сохранённые ответы"""
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
                            else:
                                wid['rb_unknown'].setChecked(True)
            except:
                pass
    
    def _save_answers(self):
        """Сохраняет ответы в JSON"""
        import json
        
        self.answers = {}
        for wid in self.question_widgets:
            if wid['rb_yes'].isChecked():
                self.answers[wid['id']] = 1
            elif wid['rb_no'].isChecked():
                self.answers[wid['id']] = 0
            else:
                self.answers[wid['id']] = -1  # не знаю/не отвечено
        
        # Сохраняем в файл
        with open("manual_answers.json", 'w', encoding='utf-8') as f:
            json.dump(self.answers, f, ensure_ascii=False, indent=2)
        
        return self.answers
    
    def _update_progress(self):
        """Обновляет прогресс-бар"""
        answered = 0
        for wid in self.question_widgets:
            if (wid['rb_yes'].isChecked() or 
                wid['rb_no'].isChecked() or 
                wid['rb_unknown'].isChecked()):
                answered += 1
        
        total = len(self.question_widgets)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(answered)
        self.progress_bar.setFormat(f"Отвечено: {answered} из {total}")
    
    def _on_save(self):
        """Обработчик сохранения"""
        answers = self._save_answers()
        self.answers_saved.emit(answers)
        self.accept()
"""
Модуль генерации Акта о готовности АРМ к работе с персональными данными
в соответствии с требованиями Приказа ФСТЭК №21 и 152-ФЗ
"""

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import platform


class ActGenerator:
    """Генератор Акта о готовности АРМ к работе с ПДн"""

    def __init__(self, results: list, security_level: int, system_info: dict = None):
        self.results = results
        self.security_level = security_level
        self.system_info = system_info or self._get_system_info()
        self.passed = sum(1 for r in results if r.get('status', False))
        self.total = len(results)
        self.percent = (self.passed * 100 // self.total) if self.total > 0 else 0
        self.is_ready = (self.percent >= 70)
        self.font_name = None

    def _get_system_info(self) -> dict:
        import socket
        import getpass
        return {
            'computer_name': socket.gethostname(),
            'user_name': getpass.getuser(),
            'os': platform.system() + ' ' + platform.release(),
            'check_date': datetime.now().strftime("%d.%m.%Y"),
            'check_time': datetime.now().strftime("%H:%M:%S")
        }

    def _find_cyrillic_font(self):
        possible_fonts = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/times.ttf",
            "C:/Windows/Fonts/timesbd.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/DejaVuSans.ttf",
            "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
        ]
        
        for font_path in possible_fonts:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('CustomFont', font_path))
                    bold_path = font_path.replace('.ttf', 'bd.ttf').replace('.ttf', 'b.ttf')
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont('CustomFont-Bold', bold_path))
                    else:
                        pdfmetrics.registerFont(TTFont('CustomFont-Bold', font_path))
                    return 'CustomFont'
                except:
                    continue
        return 'Helvetica'

    def _register_fonts(self):
        self.font_name = self._find_cyrillic_font()
        return self.font_name

    def generate(self, output_path: str = None) -> str:
        if output_path is None:
            output_path = os.path.join(
                os.getcwd(),
                f"Акт_готовности_АРМ_{self.system_info['computer_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            topMargin=20*mm,
            bottomMargin=20*mm,
            leftMargin=25*mm,
            rightMargin=25*mm
        )

        font_name = self._register_fonts()

        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            name='RussianNormal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            alignment=0,
            spaceAfter=6,
            encoding='utf-8'
        ))
        styles.add(ParagraphStyle(
            name='RussianTitle',
            parent=styles['Title'],
            fontName=font_name,
            fontSize=14,
            alignment=1,
            spaceAfter=4,
            spaceBefore=4,
            encoding='utf-8'
        ))
        styles.add(ParagraphStyle(
            name='RussianHeading',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=13,
            alignment=1,  # CENTER
            spaceAfter=8,
            spaceBefore=12,
            encoding='utf-8'
        ))
        styles.add(ParagraphStyle(
            name='RussianCenter',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            alignment=1,
            spaceAfter=6,
            encoding='utf-8'
        ))
        styles.add(ParagraphStyle(
            name='Signature',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            alignment=0,
            spaceAfter=2,
            encoding='utf-8'
        ))

        story = []

        # ========== НАЗВАНИЕ ДОКУМЕНТА ==========
        story.append(Paragraph(
            "<b>АКТ № __________</b>", 
            styles['RussianTitle']
        ))
        story.append(Paragraph(
            "<b>о готовности автоматизированного рабочего<br/>"
            "места к обработке персональных данных</b>", 
            styles['RussianTitle']
        ))
        story.append(Spacer(1, 16))

        # ========== СОСТАВ КОМИССИИ ==========
        story.append(Paragraph(
            "<b>Комиссия в составе:</b>", 
            styles['RussianNormal']
        ))
        story.append(Spacer(1, 6))
        
        story.append(Paragraph(
            "<b>Председатель комиссии:</b>", 
            styles['RussianNormal']
        ))
        story.append(Spacer(1, 4))
        
        story.append(Paragraph(
            "____________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(____________________)", 
            styles['Signature']
        ))
        story.append(Spacer(1, 16))
        
        story.append(Paragraph(
            "<b>Члены комиссии:</b>", 
            styles['RussianNormal']
        ))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "____________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(____________________)", 
            styles['Signature']
        ))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            "____________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(____________________)", 
            styles['Signature']
        ))
        story.append(Spacer(1, 16))

        # ========== ОБЪЕКТ ПРОВЕРКИ ==========
        story.append(Paragraph(
            f"провела проверку автоматизированного рабочего места (АРМ) "
            f"<b>«{self.system_info['computer_name']}»</b> "
            f"(пользователь: <b>{self.system_info['user_name']}</b>) на предмет соответствия требованиям "
            f"Федерального закона №152-ФЗ «О персональных данных» и Приказа ФСТЭК России №21 "
            f"(уровень защищённости <b>УЗ-{self.security_level}</b>).", 
            styles['RussianNormal']
        ))
        story.append(Spacer(1, 16))

        # ========== РЕЗУЛЬТАТЫ ПРОВЕРКИ (ЗАГОЛОВОК ПО ЦЕНТРУ, БЕЗ ЦИФРЫ) ==========
        story.append(Paragraph(
            "<b>Результаты проверки технических мер защиты</b>", 
            styles['RussianHeading']
        ))

        # Группируем результаты по категориям
        categories = {}
        category_names = {
            "ИАФ": "Идентификация и аутентификация",
            "УПД": "Управление доступом",
            "ОПС": "Ограничение программной среды",
            "ЗНИ": "Защита машинных носителей",
            "РСБ": "Регистрация событий безопасности",
            "АВЗ": "Антивирусная защита",
            "СОВ": "Обнаружение вторжений",
            "АНЗ": "Контроль защищённости",
            "ОЦЛ": "Обеспечение целостности",
            "ОДТ": "Обеспечение доступности",
            "ЗСВ": "Защита среды виртуализации",
            "ЗТС": "Защита технических средств",
            "ЗИС": "Защита ИС и связи",
            "ИНЦ": "Выявление инцидентов",
            "УКФ": "Управление конфигурацией",
        }
        
        for r in self.results:
            cat_id = r.get('id', '???').split('.')[0]
            if cat_id not in categories:
                categories[cat_id] = {'passed': 0, 'total': 0, 'name': category_names.get(cat_id, cat_id)}
            categories[cat_id]['total'] += 1
            if r.get('status', False):
                categories[cat_id]['passed'] += 1

        # Таблица с результатами по категориям
        cat_table_data = [
            [Paragraph("<b>Категория мер</b>", styles['RussianCenter']),
             Paragraph("<b>Пройдено</b>", styles['RussianCenter']),
             Paragraph("<b>Всего</b>", styles['RussianCenter']),
             Paragraph("<b>Статус</b>", styles['RussianCenter'])]
        ]

        for cat_id, data in categories.items():
            if data['passed'] == data['total']:
                status = "СООТВЕТСТВУЕТ"
            elif data['passed'] > 0:
                status = "ЧАСТИЧНО"
            else:
                status = "НЕ СООТВЕТСТВУЕТ"
            cat_table_data.append([
                Paragraph(f"{cat_id}. {data['name']}", styles['RussianNormal']),
                Paragraph(str(data['passed']), styles['RussianCenter']),
                Paragraph(str(data['total']), styles['RussianCenter']),
                Paragraph(status, styles['RussianCenter'])
            ])

        cat_table = Table(cat_table_data, colWidths=[70*mm, 30*mm, 30*mm, 50*mm])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 16))

        # ========== ЗАКЛЮЧЕНИЕ КОМИССИИ (ЗАГОЛОВОК ПО ЦЕНТРУ, БЕЗ ЦИФРЫ) ==========
        story.append(Paragraph(
            "<b>Заключение комиссии</b>", 
            styles['RussianHeading']
        ))
        
        if self.is_ready:
            conclusion = (
                f"АРМ «{self.system_info['computer_name']}» признаётся <b>ГОТОВЫМ</b> к обработке персональных данных "
                f"с уровнем защищённости УЗ-{self.security_level}. "
                f"Процент соответствия требованиям составляет <b>{self.percent}%</b> "
                f"(пройдено {self.passed} из {self.total} проверок)."
            )
        else:
            conclusion = (
                f"АРМ «{self.system_info['computer_name']}» признаётся <b>НЕ ГОТОВЫМ</b> к обработке персональных данных "
                f"с уровнем защищённости УЗ-{self.security_level}. "
                f"Процент соответствия требованиям составляет {self.percent}% "
                f"(пройдено {self.passed} из {self.total} проверок), что ниже установленного порога (70%)."
            )

        story.append(Paragraph(conclusion, styles['RussianNormal']))
        story.append(Spacer(1, 24))

        # ========== ПОДПИСИ (дата справа) ==========
        story.append(Paragraph(
            "____________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;____________________", 
            styles['Signature']
        ))
        story.append(Paragraph(
            "<i>(подпись председателя)</i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<i>(дата)</i>", 
            styles['Signature']
        ))
        
        story.append(Spacer(1, 24))
        
        story.append(Paragraph(
            "____________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;____________________", 
            styles['Signature']
        ))
        story.append(Paragraph(
            "<i>(подпись члена комиссии)</i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<i>(дата)</i>", 
            styles['Signature']
        ))
        
        story.append(Spacer(1, 24))
        
        story.append(Paragraph(
            "____________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;____________________", 
            styles['Signature']
        ))
        story.append(Paragraph(
            "<i>(подпись члена комиссии)</i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<i>(дата)</i>", 
            styles['Signature']
        ))

        doc.build(story)
        return output_path
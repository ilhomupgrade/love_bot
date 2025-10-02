"""
Генератор PDF отчётов о совместимости
"""

from fpdf import FPDF
from datetime import datetime
import os


class PDF(FPDF):
    def header(self):
        # Заголовок
        self.set_font('Arial', 'B', 20)
        self.set_text_color(102, 126, 234)
        self.cell(0, 10, 'LoveBot - Report', align='C', ln=True)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', '', 8)
        self.set_text_color(156, 163, 175)
        self.cell(0, 10, f'Created: {datetime.now().strftime("%d.%m.%Y %H:%M")}', align='C')


def generate_pdf_report(
    compatibility_score: int,
    report: str,
    partner1_name: str = "Партнёр 1",
    partner2_name: str = "Партнёр 2",
    output_path: str = None
) -> str:
    """
    Генерирует красивый PDF отчёт о совместимости

    Args:
        compatibility_score: процент совместимости (0-100)
        report: текст отчёта от AI
        partner1_name: имя первого партнёра
        partner2_name: имя второго партнёра
        output_path: путь для сохранения PDF

    Returns:
        str: путь к созданному PDF файлу
    """

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"reports/compatibility_report_{timestamp}.pdf"

    # Создаём директорию если её нет
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Определяем уровень совместимости
    if compatibility_score >= 80:
        color = (16, 185, 129)  # зелёный
        emoji = "💚"
        level = "Отличная"
    elif compatibility_score >= 60:
        color = (245, 158, 11)  # оранжевый
        emoji = "💛"
        level = "Хорошая"
    elif compatibility_score >= 40:
        color = (59, 130, 246)  # синий
        emoji = "💙"
        level = "Средняя"
    else:
        color = (239, 68, 68)  # красный
        emoji = "❤️"
        level = "Требует работы"

    # Создаём PDF
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)

    # Блок с процентом совместимости
    pdf.set_fill_color(*color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 40)
    pdf.cell(0, 30, f'{compatibility_score}%', align='C', fill=True, ln=True)

    # Уровень совместимости
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 15, f'{level}', align='C', ln=True)
    pdf.ln(10)

    # Партнёры
    pdf.set_text_color(31, 41, 55)
    pdf.set_font('Arial', '', 14)
    pdf.cell(0, 10, f'{partner1_name} x {partner2_name}', align='C', ln=True)
    pdf.ln(10)

    # Разделитель
    pdf.set_draw_color(229, 231, 235)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(10)

    # Заголовок отчёта
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(102, 126, 234)
    pdf.cell(0, 10, 'Analysis Results', ln=True)
    pdf.ln(5)

    # Текст отчёта
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(75, 85, 99)

    # Разбиваем отчёт на параграфы и форматируем
    paragraphs = report.split('\n\n')
    for paragraph in paragraphs:
        if paragraph.strip():
            # Убираем markdown символы и неподдерживаемые символы
            clean_text = paragraph.replace('**', '').replace('*', '').replace('#', '')
            # Оставляем только ASCII и базовые символы
            clean_text = clean_text.encode('ascii', 'ignore').decode('ascii')

            if not clean_text.strip():
                continue

            # Если это заголовок (начинается с цифры)
            if clean_text.strip()[0].isdigit() and '.' in clean_text[:5]:
                pdf.ln(3)
                pdf.set_font('Arial', 'B', 12)
                pdf.set_text_color(102, 126, 234)
                try:
                    pdf.multi_cell(0, 7, clean_text)
                except:
                    pass
                pdf.set_font('Arial', '', 11)
                pdf.set_text_color(75, 85, 99)
            else:
                try:
                    pdf.multi_cell(0, 7, clean_text)
                    pdf.ln(3)
                except:
                    pass

    # Сохраняем PDF
    pdf.output(output_path)

    return output_path

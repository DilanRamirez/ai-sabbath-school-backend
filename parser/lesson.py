import fitz  # PyMuPDF
import os
import re

PDF_PATH = "app/data/2025/Q2/lesson-09/lesson9.pdf"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def clean(text):
    lines = [line.strip() for line in text.strip().splitlines()]
    return "\n".join(lines)


def save_markdown(filename, content):
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write(content)


def extract_and_write_markdown():
    doc = fitz.open(PDF_PATH)
    pages = [(i + 1, page.get_text()) for i, page in enumerate(doc)]
    text = "\n".join([page_text for _, page_text in pages])
    lesson_number_match = re.search(r"Lección\s+(\d+):", text)
    lesson_number = lesson_number_match.group(1) if lesson_number_match else "unknown"

    # Saturday - Intro Page
    intro_match = re.search(
        r"Lección\s+(\d+):\s+Para el\s+(\d{1,2} de \w+ de \d{4})\s+(.*?)\n+Sábado\s+(\d{1,2} de \w+)\n+(.*?)(?=\n+(?:\|\s*)?Lección \d+\s*\|?\s*Domingo)",
        text,
        re.DOTALL,
    )
    if intro_match:
        lesson_number, end_date, title, sabado_date, content = intro_match.groups()
        memory_verse_match = re.search(
            r"PARA MEMORIZAR:\s*(.*?)\s*(?=\n[A-Z]|$)", content, re.DOTALL
        )
        if memory_verse_match:
            memory_verse = clean(memory_verse_match.group(1))
            content = content.replace(memory_verse_match.group(0), "").strip()
        else:
            memory_verse = ""
        study_texts_match = re.search(
            r"LEE PARA EL ESTUDIO DE ESTA SEMANA:\s*(.*?)\s*(?=\n[A-Z]|$)",
            content,
            re.DOTALL,
        )
        if study_texts_match:
            study_texts = clean(study_texts_match.group(1))
            content = content.replace(study_texts_match.group(0), "").strip()
        else:
            study_texts = ""
        filename = f"{lesson_number}_sabado_{sabado_date.replace(' ', '_')}.md"
        md = f"### Título:\n{title.strip()}\n### Fecha:\n{sabado_date}\n\n"
        if study_texts:
            md += f"### Lecturas para esta semana:\n{study_texts}\n\n"
        if memory_verse:
            md += f"### Para memorizar:\n{memory_verse}\n\n"
        page_number_match = re.search(r"\n(\d{1,4})\s*$", content.strip())
        page_number = page_number_match.group(1) if page_number_match else "N/A"
        content = re.sub(r"\n" + re.escape(page_number) + r"\s*$", "", content)
        md += "\n\n### Contenido:\n" + clean(content)
        md += f"\n\n### Página:\n{page_number}"
        save_markdown(filename, md)

    # Weekdays Domingo to Jueves
    days = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves"]
    for day in days:
        pattern = rf"(?:\|\s*)?Lección \d+\s*\|?\s*{day}\s+(\d{{1,2}} de \w+)\s*\n(.*?)\n(.*?)(?=\n(?:\|\s*)?Lección \d+\s*\|?\s*(?:Domingo|Lunes|Martes|Miércoles|Jueves|Viernes)|\n+PREGUNTAS PARA DIALOGAR|\Z)"

        for match in re.finditer(pattern, text, re.DOTALL):
            date_str, title_block, body = match.groups()
            title_lines = []
            for line in title_block.strip().splitlines():
                if line.isupper() or re.fullmatch(
                    r"[A-ZÁÉÍÓÚÑ0-9\s,.;:¡!¿?\"'-]+", line
                ):
                    title_lines.append(line.strip())
                else:
                    break
            title = clean(" ".join(title_lines))
            questions = re.findall(r"¿.*?\?", body)
            main_prompt = questions[0] if questions else ""
            filename = f"{lesson_number}_{day.lower()}_{date_str.replace(' ', '_')}.md"
            md = f"### Título:\n{title}\n\n### Fecha:\n{day}-{date_str}\n\n"
            if main_prompt:
                md += f"### Lectura principal:\n{main_prompt}\n\n"
            if questions:
                md += (
                    "### Reflexionar:\n" + "\n".join(f"- {q}" for q in questions) + "\n"
                )
            page_number_match = re.search(r"\n(\d{1,4})\s*$", body.strip())
            page_number = page_number_match.group(1) if page_number_match else "N/A"
            body = re.sub(r"\n" + re.escape(page_number) + r"\s*$", "", body)
            md += f"\n\n### Contenido:\n{clean(body)}"
            md += f"\n\n### Página:\n{page_number}"
            save_markdown(filename, md)

    # Friday
    friday_match = re.search(
        r"Viernes (\d{1,2} de \w+)\nPARA ESTUDIAR Y MEDITAR:(.*?)PREGUNTAS PARA DIALOGAR:(.*?)\Z",
        text,
        re.DOTALL,
    )
    if friday_match:
        date_str, meditation, q_block = friday_match.groups()
        questions = re.findall(
            r"\d+\.\s*(.*?)(?=\n\d+\.|\Z)", q_block.strip(), re.DOTALL
        )
        filename = f"{lesson_number}_viernes_{date_str.replace(' ', '_')}.md"
        page_number_match = re.search(r"\n(\d{1,4})\s*$", meditation.strip())
        page_number = page_number_match.group(1) if page_number_match else "N/A"
        meditation = re.sub(r"\n" + re.escape(page_number) + r"\s*$", "", meditation)
        md = f"### Título:\nPara Estudiar y Meditar\n\n### Fecha:\nViernes {date_str}\n\n### Contenido:\n{clean(meditation)}\n\n"
        if questions:
            md += "### Reflexionar: para dialogar:\n" + "\n".join(
                f"- {clean(q)}" for q in questions
            )

        md += f"\n\n### Página:\n{page_number}"
        save_markdown(filename, md)


# Batch parse all lessons in a directory
def parse_all_lessons_in_directory(base_dir="app/data/2025/Q2"):
    for folder in sorted(os.listdir(base_dir)):
        lesson_path = os.path.join(base_dir, folder)
        pdf_file = os.path.join(lesson_path, "lesson.pdf")
        if os.path.exists(pdf_file):
            print(f"Parsing: {pdf_file}")
            global PDF_PATH, OUTPUT_DIR
            PDF_PATH = pdf_file
            OUTPUT_DIR = lesson_path
            extract_and_write_markdown()


if __name__ == "__main__":
    parse_all_lessons_in_directory()

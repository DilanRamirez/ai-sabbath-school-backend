import os
import sys
import json
import re

OUTPUT_FILE = "lesson.json"


def extract_lines(block, key):
    match = re.search(rf"\*\*{key}:\*\*\s*(.*?)(?=\n\*\*|$)", block, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def extract_questions(block):
    questions = re.findall(r"[-*]\s+(.*)", block)
    return [q.strip() for q in questions]


def clean_lines(lines):
    return [line.strip() for line in lines if line.strip()]


def main(input_path):

    for filename in sorted(os.listdir(input_path)):
        if not filename.endswith(".md"):
            continue

        with open(os.path.join(input_path, filename), "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        title_line = lines[0].strip()
        lesson_title = title_line.replace("#", "").strip().split(" - ")[-1]
        day = re.search(r"_(\w+)_", filename).group(1).capitalize()

        date = extract_lines(content, "Fecha")
        study_texts = extract_lines(content, "Lecturas para esta semana")
        memory_verse = extract_lines(content, "Para memorizar")
        main_prompt = extract_lines(content, "Lectura principal")
        page = extract_lines(content, "Página")

        if "dialogar" in content:
            question_key = "Preguntas para dialogar"
        else:
            question_key = "Preguntas"

        q_block_match = re.search(
            rf"### {question_key}:\n(.*?)\n\*\*Página:", content, re.DOTALL)
        question_block = q_block_match.group(1) if q_block_match else ""
        questions = extract_questions(question_block)

        # Grab content between the last known field and "Página"
        content_lines = []
        if "**Content:**" in content:
            content_start = content.find("**Content:**") + len("**Content:**")
            content_end = content.find("**Página:**")
            content_block = content[content_start:content_end].strip()
            content_lines = clean_lines(content_block.split("\n\n"))

        output = {
            "lesson_number": lesson_title.split()[0],
            "title": lesson_title,
            "day": day,
            "date": date,
            "study_texts": study_texts if study_texts else None,
            "memory_verse": memory_verse if memory_verse else None,
            "main_prompt": main_prompt if main_prompt else None,
            "questions": questions,
            "content": content_lines,
            "page_number": page
        }

        out_file = os.path.splitext(filename)[0] + ".json"
        with open(os.path.join(input_path, out_file), "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main("app/data/2025/Q2/lesson-07")

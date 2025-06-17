import os
import re
import json


def parse_markdown_file(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    data = {}
    filename = os.path.basename(md_path)
    data["filename"] = filename

    day_match = re.search(
        r"(sabado|domingo|lunes|martes|miércoles|jueves|viernes)",
        filename,
        re.IGNORECASE,
    )
    if day_match:
        data["day"] = day_match.group(1).capitalize()

    title_match = re.search(r"### Título:\s*\n(.+?)\n\n", content, re.DOTALL)

    # Parse lesson_number from filename since it's no longer in the title
    lesson_number_match = re.search(r"(\d+)", filename)
    data["lesson_number"] = lesson_number_match.group(1) if lesson_number_match else ""
    data["title"] = title_match.group(1).strip() if title_match else ""

    date_match = re.search(r"\*\*### Fecha:\*\* (.+)", content)
    if date_match:
        data["date"] = date_match.group(1).strip()

    # Detect Sabbath
    if "sabado" in day_match.group(1) or "sabado" in data.get("date", ""):
        title_match = re.search(r"### Título:\s*\n(.+?)\n\n", content, re.DOTALL)
        data["title"] = title_match.group(1).strip() if title_match else ""

        lecturas_match = re.search(
            r"### Lecturas para esta semana:\s*\n(.+?)\n\n", content, re.DOTALL
        )
        data["study_texts"] = lecturas_match.group(1).strip() if lecturas_match else ""

        mem_match = re.search(r"### Para memorizar:\s*\n(.+?)\n\n", content, re.DOTALL)
        data["memory_verse"] = mem_match.group(1).strip() if mem_match else ""
    elif (
        "viernes" in day_match.group(1).lower()
        or "viernes" in data.get("date", "").lower()
    ):
        reflect_block = re.search(
            r"### Reflexionar: para dialogar:\s*\n(.*?)(?=\n### |\Z)",
            content,
            re.DOTALL,
        )
        if reflect_block:
            raw_block = reflect_block.group(1).strip()
            paragraphs = [p.strip() for p in raw_block.split("\n\n") if p.strip()]
            data["reflexionar"] = paragraphs
        else:
            data["reflexionar"] = []
    else:
        reflect_block = re.search(
            r"### Reflexionar:\s*\n(.*?)(?=\n### |\Z)", content, re.DOTALL
        )
        if reflect_block:
            raw_block = reflect_block.group(1).strip()
            paragraphs = [p.strip() for p in raw_block.split("\n\n") if p.strip()]
            data["reflexionar"] = paragraphs
        else:
            data["reflexionar"] = []

    content_match = re.search(
        r"### Contenido:\s*\n(.*?)(?=\n### |\Z)", content, re.DOTALL
    )
    if content_match:
        raw_content = content_match.group(1).strip()
        data["content"] = [
            block.strip() for block in raw_content.split("\n\n") if block.strip()
        ]
    else:
        data["content"] = []

    page_match = re.search(r"### Página:\s*\n?(\d+)", content, re.IGNORECASE)
    data["page_number"] = page_match.group(1) if page_match else ""

    return data


def convert_md_files_to_json(directory):
    for fname in os.listdir(directory):
        if fname.endswith(".md"):
            md_path = os.path.join(directory, fname)
            json_path = os.path.join(directory, fname.replace(".md", ".json"))
            data = parse_markdown_file(md_path)
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(data, jf, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    base_dir = "app/data/2025/Q2"
    for folder in sorted(os.listdir(base_dir)):
        path = os.path.join(base_dir, folder)
        if os.path.isdir(path) and folder.startswith("lesson-"):
            convert_md_files_to_json(path)

import os
import pdfplumber
import json
import re
from datetime import datetime, timedelta

# --- Configuration & Helper Functions ---

SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

DAYS_OF_WEEK_SPANISH = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]
DAYS_OF_WEEK_ORDER = [
    "Sábado",
    "Domingo",
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
]


def extract_text_from_pdf(pdf_path):
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"  # Add newline as page separator
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None
    # Basic text cleaning
    # Normalize newlines
    full_text = re.sub(r"\s*\n\s*", "\n", full_text).strip()
    full_text = re.sub(r" +", " ", full_text)  # Normalize spaces
    return full_text


def parse_spanish_date(date_str):
    # e.g., "10 DE MAYO DE 2025" or "3 DE MAYO DE 2025"
    match = re.search(
        r"(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+DE\s+(\d{4})", date_str.upper()
    )
    if match:
        day, month_name, year = match.groups()
        month = SPANISH_MONTHS.get(month_name.lower())
        if month:
            return datetime(int(year), month, int(day))
    return None


def format_date_iso(dt_obj):
    return dt_obj.strftime("%Y-%m-%d") if dt_obj else None


# --- Main Parsing Logic ---


def parse_lesson_pdf(pdf_path):
    full_text = extract_text_from_pdf(pdf_path)
    if not full_text:
        return None, None

    lesson_data = {"lesson": {}}
    metadata = {}

    # 1. Lesson Number and Title
    # Use a robust regex for "Lección X: Para el DD de MMMM de YYYY" and multiline title
    lesson_header_match = re.search(
        r"(?:Lección|LECCIÓN)\s*(\d+):?\s+Para el\s+(\d{1,2}\s+DE\s+[A-ZÁÉÍÓÚÑ]+\s+DE\s+\d{4})\s*\n+(.*?)(?=\n(?:Sábado|Domingo|Lunes|Martes|Miércoles|Jueves|Viernes)|\n+LEE PARA EL ESTUDIO|VERSÍCULO PARA MEMORIZAR|PARA MEMORIZAR:)",
        full_text,
        re.IGNORECASE | re.DOTALL,
    )
    if lesson_header_match:
        lesson_num_str, week_end_date_str, title_str = lesson_header_match.groups()
    else:
        print("Error: Could not find lesson number, title, and week end date.")
        return None, None

    lesson_data["lesson"]["lesson_number"] = int(lesson_num_str)
    # As per example
    lesson_data["lesson"]["title"] = title_str.strip().upper()

    week_end_dt = parse_spanish_date(week_end_date_str)
    if not week_end_dt:
        print(f"Error: Could not parse week end date: {week_end_date_str}")
        return None, None
    lesson_data["lesson"]["week_end_date"] = format_date_iso(week_end_dt)

    # Generate ID
    month_name_for_id = [
        k for k, v in SPANISH_MONTHS.items() if v == week_end_dt.month
    ][0]
    lesson_data["lesson"][
        "id"
    ] = f"leccion_{lesson_data['lesson']['lesson_number']}_{month_name_for_id}_{week_end_dt.day}_{week_end_dt.year}"

    # Metadata fields
    metadata["id"] = lesson_data["lesson"]["id"]
    metadata["lesson_number"] = lesson_data["lesson"]["lesson_number"]
    metadata["title"] = lesson_data["lesson"]["title"]
    metadata["week_end_date"] = lesson_data["lesson"]["week_end_date"]
    week_start_dt = week_end_dt - timedelta(days=6)
    metadata["week_start_date"] = format_date_iso(week_start_dt)

    # 2. Study Texts
    # "LEE PARA EL ESTUDIO DE ESTA SEMANA:" followed by list, ending before "VERSÍCULO PARA MEMORIZAR"
    study_texts_match = re.search(
        r"Lee para el estudio de esta semana:\s*(.*?)(?=\s*VERSÍCULO PARA MEMORIZAR|PARA MEMORIZAR:)",
        full_text,
        re.IGNORECASE | re.DOTALL,
    )
    study_texts_list = []
    if study_texts_match:
        texts_block = study_texts_match.group(1).strip()
        study_texts_list = [
            line.strip() for line in texts_block.split("\n") if line.strip()
        ]
    lesson_data["lesson"]["study_texts"] = study_texts_list
    # Also in metadata as per example
    metadata["study_texts"] = study_texts_list

    # 3. Memory Verse
    # "VERSÍCULO PARA MEMORIZAR:" or "PARA MEMORIZAR:" followed by text and (reference)
    memory_verse_match = re.search(
        r"(?:VERSÍCULO PARA MEMORIZAR|PARA MEMORIZAR:)\s*(.*?)\s*\((.*?)\)",
        full_text,
        re.IGNORECASE | re.DOTALL,
    )
    memory_verse_obj = {"text": "", "reference": ""}
    if memory_verse_match:
        verse_text = memory_verse_match.group(1).replace("\n", " ").strip()
        # Clean up multiple spaces
        verse_text = re.sub(r"\s{2,}", " ", verse_text)
        memory_verse_obj["text"] = verse_text
        memory_verse_obj["reference"] = memory_verse_match.group(2).strip()
    lesson_data["lesson"]["memory_verse"] = memory_verse_obj
    metadata["memory_verse_reference"] = memory_verse_obj["reference"]

    # 4. Daily Sections
    # This is the most complex. We'll split the text by day headers.
    # The end of daily sections is marked by "PARA ESTUDIAR Y MEDITAR"
    daily_sections_text_match = re.search(
        r"(Sábado.*?)(?=\nPARA ESTUDIAR Y MEDITAR)",
        full_text,
        re.IGNORECASE | re.DOTALL,
    )

    daily_sections_list = []
    metadata_daily_titles = []
    has_egw_quotes_lesson = False

    if daily_sections_text_match:
        content_for_days = daily_sections_text_match.group(1)

        # Regex to find day headers and their content until the next day or end marker
        day_pattern = re.compile(
            r"(Sábado|Domingo|Lunes|Martes|Miércoles|Jueves|Viernes)\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})\s*\n(.*?)\n(.*?)(?=\n(?:Sábado|Domingo|Lunes|Martes|Miércoles|Jueves|Viernes)\s+\d{1,2}\s+de|\n+PREGUNTAS PARA DIALOGAR|\Z)",
            re.IGNORECASE | re.DOTALL,
        )

        current_date_iter = week_start_dt  # Start from Saturday

        for day_match in day_pattern.finditer(content_for_days):
            day_name, day_date_str, day_title, day_content_block = day_match.groups()
            day_name = day_name.strip()
            day_title = day_title.strip()
            day_content_block = day_content_block.strip()

            day_dt = parse_spanish_date(day_date_str.strip())

            daily_section = {
                "day": day_name,
                "date": format_date_iso(day_dt),
                "title": day_title,
                "main_prompt": "",
                "content": [],
                "quotes": [],
                "questions": [],
            }

            # Extract main_prompt (heuristic: first paragraph, often a question or "Lee...")
            # Then content, quotes, and questions from day_content_block

            # Split block by potential section headers within a day
            # Heuristic: main_prompt is often the first paragraph that looks like a question or starts with "Lee", "Compara" etc.
            # Content paragraphs follow.
            # EGW quotes are identified by "Elena G. de White" or "Elena de White".
            # Daily questions might be after "Preguntas:" or numbered/bulleted list at the end of day's content.

            paragraphs = [p.strip() for p in day_content_block.split("\n") if p.strip()]

            # Main prompt: Assume it's the first substantial paragraph if it sounds like one
            # Or if it's clearly separated. This is tricky.
            # For now, let's assume the first non-empty line *after* the title is the main prompt IF it starts with a verb or question
            prompt_found = False
            content_paras = []

            # A more robust way to find main_prompt might be to look for specific starting words
            if paragraphs:
                first_para = paragraphs[0]
                if first_para.endswith("?") or any(
                    first_para.lower().startswith(verb)
                    for verb in [
                        "lee",
                        "compara",
                        "reflexiona",
                        "analiza",
                        "considera",
                        "examina",
                    ]
                ):
                    daily_section["main_prompt"] = first_para
                    paragraphs = paragraphs[1:]  # Consume the prompt
                    prompt_found = True

            # Process remaining paragraphs for content, quotes, questions
            idx = 0
            while idx < len(paragraphs):
                para = paragraphs[idx]

                # Check for EGW quote
                egw_quote_match = re.match(
                    r"“?(.*)”\s*—\s*Elena G?\.?\s*de White,\s*(.*?),\s*([pPágG\.\s\d,-]+)\.?$",
                    para,
                    re.IGNORECASE,
                )
                # Simpler EGW based on example:
                # "Elena de White", "Patriarcas y profetas", "pp. 59, 60", "text"
                # This is tricky. Let's assume EGW quotes start with her name or are clearly demarcated.
                # For the example structure: Author, Book, Page Range, Text
                # This is hard without clearer delimiters in raw text.
                # Let's try to match a block initiated by "Elena de White"

                if (
                    "elena g. de white" in para.lower()
                    or "elena de white" in para.lower()
                ):  # Simple check for now
                    # Try to parse the example EGW structure
                    # "author": "Elena de White", "book": "Patriarcas y profetas", "page_range": "pp. 59, 60", "text": "..."
                    # This requires a more structured approach. For now, let's assume a quote block.
                    # If the example format is "Author, Book, Page: Text"
                    # Or if it's a block starting with "—Elena G. de White, ..."
                    # The provided example has EGW quotes as a list of dicts.

                    # For this example, the EGW quote is complex. Let's assume this format based on Domingo:
                    # "Elena de White\nPatriarcas y profetas\npp. 59, 60\n\"Actual quote text...\"" (this is a guess)
                    # Or if the text has "Elena de White" and "book" and "page_range" and "text" as keys (from example)
                    # The PDF usually has the text and then attribute "—Elena G. de White, Book Name, pp. X."

                    # Trying to match the structure provided in the JSON example where quote text is separate
                    # This is very hard with flat text. Let's assume EGW quote starts with a quote mark
                    # and ends with "—Elena G. de White..."
                    # For now, placeholder for EGW quotes parsing

                    # Let's try a simplified approach for the provided example structure.
                    # If we find "Elena de White", assume the *next few lines* might be book, page, then text.
                    # This is highly heuristic.
                    # A better way: find "Elena de White", then backtrack for the quote text if it's above.

                    # Based on Sunday's example:
                    # The quote text is first, then attribution.
                    # "text"
                    # "author", "book", "page_range" (these are not explicitly in the text like that)
                    # It's more like: "Quote text in quotes." - Author, Book, page.

                    # Let's assume EGW quote text is often in quotation marks.
                    if para.startswith('"') or para.startswith("“"):  # Start of a quote
                        quote_text = para
                        author = ""
                        book = ""
                        page_range = ""

                        # Look ahead for attribution
                        if idx + 1 < len(paragraphs):
                            attribution_line = paragraphs[idx + 1]
                            if (
                                "elena g. de white" in attribution_line.lower()
                                or "elena de white" in attribution_line.lower()
                            ):
                                author = "Elena de White"  # Default
                                # Simplistic parse of Book, pp. range from attribution_line
                                parts = attribution_line.split(",")
                                if len(parts) > 1:
                                    book = parts[1].replace("—", "").strip()
                                if len(parts) > 2:
                                    page_range = parts[2].strip()
                                idx += 1  # Consumed attribution line

                        if author:  # If we found attribution
                            daily_section["quotes"].append(
                                {
                                    "author": author,
                                    "book": book,
                                    "page_range": page_range,
                                    "text": quote_text.strip('"“” '),
                                }
                            )
                            has_egw_quotes_lesson = True
                            idx += 1
                            continue  # Move to next paragraph block

                # Check for daily questions (simple check: starts with number. or specific phrasing)
                if (
                    re.match(r"^\d+\.\s+", para)
                    or para.endswith("?")
                    or para.startswith("¡")
                    or para.startswith("¿")
                ):
                    # Heuristic: if it looks like a question and we are past some content
                    # Add to questions if some content exists or no prompt
                    if len(daily_section["content"]) > 0 or not prompt_found:
                        daily_section["questions"].append(para)
                    else:  # Otherwise, it's likely content
                        daily_section["content"].append(para)
                else:  # Regular content
                    daily_section["content"].append(para)
                idx += 1
                print(f"daily_section: {daily_section}")
                print("--" * 30)

            # If main_prompt wasn't found via specific keywords and content exists, take first content as prompt
            if not daily_section["main_prompt"] and daily_section["content"]:
                # Arbitrary length to avoid tiny lines
                if len(daily_section["content"][0]) > 50:
                    daily_section["main_prompt"] = daily_section["content"].pop(0)

            daily_sections_list.append(daily_section)
            metadata_daily_titles.append({"day": day_name, "title": day_title})
            current_date_iter += timedelta(days=1)

        # Reorder daily sections to match example (Sat, Sun, Mon...)
        daily_sections_list.sort(key=lambda x: DAYS_OF_WEEK_ORDER.index(x["day"]))
        metadata_daily_titles.sort(key=lambda x: DAYS_OF_WEEK_ORDER.index(x["day"]))

    lesson_data["lesson"]["daily_sections"] = daily_sections_list
    metadata["has_egw_quotes"] = has_egw_quotes_lesson
    metadata["daily_titles"] = metadata_daily_titles

    # 5. "PARA ESTUDIAR Y MEDITAR" section (Friday's content effectively)
    # This part seems to be the content for the "Viernes" / "PARA ESTUDIAR Y MEDITAR" section in the example
    study_meditate_match = re.search(
        r"PARA ESTUDIAR Y MEDITAR\s*\n(.*?)(?=\nPREGUNTAS PARA DIALOGAR|\Z)",
        full_text,
        re.IGNORECASE | re.DOTALL,
    )
    if study_meditate_match:
        friday_content_block = study_meditate_match.group(1).strip()
        friday_paras = [
            p.strip() for p in friday_content_block.split("\n") if p.strip()
        ]

        friday_section = next(
            (ds for ds in daily_sections_list if ds["day"] == "Viernes"), None
        )
        if friday_section:
            # Similar logic to other days for quotes within this block
            temp_content = []
            idx = 0
            while idx < len(friday_paras):
                para = friday_paras[idx]
                # EGW Quote check for Friday
                if para.startswith('"') or para.startswith("“"):
                    quote_text = para
                    author = ""
                    book = ""
                    page_range = ""
                    if idx + 1 < len(friday_paras):
                        attribution_line = friday_paras[idx + 1]
                        if (
                            "elena g. de white" in attribution_line.lower()
                            or "elena de white" in attribution_line.lower()
                        ):
                            author = "Elena de White"
                            parts = attribution_line.split(",")
                            if len(parts) > 1:
                                book = parts[1].replace("—", "").strip()
                            if len(parts) > 2:
                                page_range = parts[2].strip()
                            idx += 1
                    if author:
                        friday_section["quotes"].append(
                            {
                                "author": author,
                                "book": book,
                                "page_range": page_range,
                                "text": quote_text.strip('"“” '),
                            }
                        )
                        metadata["has_egw_quotes"] = True  # Ensure this is set
                        idx += 1
                        continue
                temp_content.append(para)
                idx += 1
            friday_section["content"].extend(temp_content)  # Add remaining as content

    # 6. Discussion Questions
    # "PREGUNTAS PARA DIALOGAR" followed by numbered questions
    discussion_questions_match = re.search(
        # Assuming AUTORÍA might be a footer
        r"PREGUNTAS PARA DIALOGAR\s*\n(.*?)(?:\nAUTORÍA|\Z)",
        full_text,
        re.IGNORECASE | re.DOTALL,
    )
    discussion_questions_list = []
    if discussion_questions_match:
        questions_block = discussion_questions_match.group(1).strip()
        # Questions are numbered: "1. Question text"
        for q_match in re.finditer(
            r"(\d+)\.\s*(.*?)(?=\n\d+\.|\Z)", questions_block, re.DOTALL
        ):
            num, q_text = q_match.groups()
            discussion_questions_list.append(
                {"number": int(num), "question": q_text.replace("\n", " ").strip()}
            )
    lesson_data["lesson"]["discussion_questions"] = discussion_questions_list
    metadata["discussion_question_count"] = len(discussion_questions_list)

    return lesson_data, metadata


# --- Main Execution ---


if __name__ == "__main__":
    BASE_DIR = "app/data/2025/Q2"

    for lesson_dir in sorted(os.listdir(BASE_DIR)):
        lesson_path = os.path.join(BASE_DIR, lesson_dir)
        pdf_file_path = os.path.join(lesson_path, "lesson.pdf")

        if not os.path.isfile(pdf_file_path):
            continue

        print(f"Parsing {pdf_file_path}...")
        lesson_json, metadata_json = parse_lesson_pdf(pdf_file_path)

        if lesson_json and metadata_json:
            try:
                with open(
                    os.path.join(lesson_path, "lesson.json"), "w", encoding="utf-8"
                ) as f_lesson:
                    json.dump(lesson_json, f_lesson, ensure_ascii=False, indent=2)
                print(f"Saved lesson.json in {lesson_path}")
            except Exception as e:
                print(f"Error writing lesson.json in {lesson_path}: {e}")

            try:
                with open(
                    os.path.join(lesson_path, "metadata.json"), "w", encoding="utf-8"
                ) as f_meta:
                    json.dump(metadata_json, f_meta, ensure_ascii=False, indent=2)
                print(f"Saved metadata.json in {lesson_path}")
            except Exception as e:
                print(f"Error writing metadata.json in {lesson_path}: {e}")
        else:
            print(f"Failed to parse {pdf_file_path}")

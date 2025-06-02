import os
import requests
import re
from typing import Optional, List
from pathlib import Path


def clean_text(text: str) -> str:
    """
    Normalize text by:
    - Stripping leading/trailing whitespace
    - Replacing multiple whitespace characters with a single space
    - Removing control characters
    - Replacing double quotes with single quotes
    - Removing non-printable or weird characters
    """
    import re

    # Replace control characters with space
    text = re.sub(r"[\r\n\t]+", " ", text)
    # Replace multiple spaces
    text = re.sub(r" +", " ", text)
    # Replace double quotes with single quotes
    text = text.replace('"', "'")
    # Remove any remaining non-printable characters
    text = "".join(ch for ch in text if ch.isprintable())
    return text.strip()


# Map Spanish book names to their English counterparts for API
SPANISH_BOOK_MAP = {
    # Pentateuch
    "Génesis": "Genesis",
    "Gén.": "Genesis",
    "Éxodo": "Exodus",
    "Éxo.": "Exodus",
    "Levítico": "Leviticus",
    "Lev.": "Leviticus",
    "Números": "Numbers",
    "Núm.": "Numbers",
    "Deuteronomio": "Deuteronomy",
    "Deut.": "Deuteronomy",
    # Historical Books
    "Josué": "Joshua",
    "Jos.": "Joshua",
    "Jueces": "Judges",
    "Jue.": "Judges",
    "Rut": "Ruth",
    "1 Samuel": "1 Samuel",
    "1 Sam.": "1 Samuel",
    "2 Samuel": "2 Samuel",
    "2 Sam.": "2 Samuel",
    "1 Reyes": "1 Kings",
    "1 Rey.": "1 Kings",
    "2 Reyes": "2 Kings",
    "2 Rey.": "2 Kings",
    "1 Crónicas": "1 Chronicles",
    "1 Crón.": "1 Chronicles",
    "2 Crónicas": "2 Chronicles",
    "2 Crón.": "2 Chronicles",
    "Esdras": "Ezra",
    "Esd.": "Ezra",
    "Nehemías": "Nehemiah",
    "Neh.": "Nehemiah",
    "Ester": "Esther",
    "Est.": "Esther",
    # Poetic & Wisdom
    "Job": "Job",
    "Salmos": "Psalms",
    "Sal.": "Psalms",
    "Proverbios": "Proverbs",
    "Prov.": "Proverbs",
    "Eclesiastés": "Ecclesiastes",
    "Ecl.": "Ecclesiastes",
    "Cantares": "Song of Solomon",
    "Cant.": "Song of Solomon",
    # Major Prophets
    "Isaías": "Isaiah",
    "Isa.": "Isaiah",
    "Jeremías": "Jeremiah",
    "Jer.": "Jeremiah",
    "Lamentaciones": "Lamentations",
    "Lam.": "Lamentations",
    "Ezequiel": "Ezekiel",
    "Ezeq.": "Ezekiel",
    "Daniel": "Daniel",
    "Dan.": "Daniel",
    # Minor Prophets
    "Oseas": "Hosea",
    "Os.": "Hosea",
    "Joel": "Joel",
    "Amós": "Amos",
    "Abdías": "Obadiah",
    "Abd.": "Obadiah",
    "Jonás": "Jonah",
    "Jon.": "Jonah",
    "Miqueas": "Micah",
    "Mic.": "Micah",
    "Nahúm": "Nahum",
    "Nah.": "Nahum",
    "Habacuc": "Habakkuk",
    "Hab.": "Habakkuk",
    "Sofonías": "Zephaniah",
    "Sof.": "Zephaniah",
    "Hageo": "Haggai",
    "Hag.": "Haggai",
    "Zacarías": "Zechariah",
    "Zac.": "Zechariah",
    "Malaquías": "Malachi",
    "Mal.": "Malachi",
    # Gospels
    "Mateo": "Matthew",
    "Mat.": "Matthew",
    "Marcos": "Mark",
    "Mr.": "Mark",
    "Lucas": "Luke",
    "Luc.": "Luke",
    "Juan": "John",
    "Jn.": "John",
    # Acts
    "Hechos": "Acts",
    "Hech.": "Acts",
    # Pauline Epistles
    "Romanos": "Romans",
    "Rom.": "Romans",
    "1 Corintios": "1 Corinthians",
    "1 Cor.": "1 Corinthians",
    "2 Corintios": "2 Corinthians",
    "2 Cor.": "2 Corinthians",
    "Gálatas": "Galatians",
    "Gal.": "Galatians",
    "Efesios": "Ephesians",
    "Efe.": "Ephesians",
    "Filipenses": "Philippians",
    "Fil.": "Philippians",
    "Colosenses": "Colossians",
    "Col.": "Colossians",
    "1 Tesalonicenses": "1 Thessalonians",
    "1 Tes.": "1 Thessalonians",
    "2 Tesalonicenses": "2 Thessalonians",
    "2 Tes.": "2 Thessalonians",
    "1 Timoteo": "1 Timothy",
    "1 Tim.": "1 Timothy",
    "2 Timoteo": "2 Timothy",
    "2 Tim.": "2 Timothy",
    "Tito": "Titus",
    "Filemón": "Philemon",
    "Flm.": "Philemon",
    "Hebreos": "Hebrews",
    "Heb.": "Hebrews",
    # General Epistles
    "Santiago": "James",
    "Sant.": "James",
    "1 Pedro": "1 Peter",
    "1 Pe.": "1 Peter",
    "2 Pedro": "2 Peter",
    "2 Pe.": "2 Peter",
    "1 Juan": "1 John",
    "1 Jn.": "1 John",
    "2 Juan": "2 John",
    "2 Jn.": "2 John",
    "3 Juan": "3 John",
    "3 Jn.": "3 John",
    "Judas": "Jude",
    # Revelation
    "Apocalipsis": "Revelation",
    "Apoc.": "Revelation",
}

# Directory where prompt templates are stored (each mode has its own .txt file)
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "prompts"


def find_bible_references(text: str) -> List[str]:
    """
    Finds Bible references in Spanish within the text using defined book names.
    Returns references like 'Juan 3:16'.
    Raises a ValueError if the input is not a valid string.
    """
    if not isinstance(text, str):
        raise ValueError("Input text must be a string.")

    try:
        # Build regex for Spanish books
        book_names = sorted(SPANISH_BOOK_MAP.keys(), key=len, reverse=True)
        escaped_books = [re.escape(book) for book in book_names]
        pattern_books = "|".join(escaped_books)
        # Allow preceding start, whitespace, or '('
        pattern = rf"(?:(?<=^)|(?<=[\s(]))(?:{pattern_books})\s*\d+:\d+(?:-\d+)?(?:(?:,\s*\d+(?:-\d+)?))*\b"
        matches = re.findall(pattern, text)
        return matches
    except re.error as regex_error:
        # Log regex errors and return an empty list for graceful handling
        print(f"Regex error occurred: {regex_error}")
        return []
    except Exception as e:
        # Catch any unexpected exceptions and return an empty list
        print(f"Unexpected error occurred in find_bible_references: {e}")
        return []


def fetch_bible_text(ref: str) -> str:
    # Validate input
    if not isinstance(ref, str) or not ref.strip():
        print("Invalid Bible reference input.")
        return ""
    try:
        # Split book and chapter:verse
        parts = ref.strip().split(" ", 1)
        if not parts[0]:
            print("Bible reference missing book information.")
            return ""
        book_part = parts[0]
        chapter_verse = parts[1] if len(parts) > 1 and parts[1].strip() else ""
        # Map Spanish book names to English
        eng_book = SPANISH_BOOK_MAP.get(book_part, book_part)
        api_ref = f"{eng_book} {chapter_verse}".strip()
        if not api_ref:
            print("Incomplete Bible reference.")
            return ""
        url = f"https://bible-api.com/{api_ref.replace(' ', '+')}"
        print(f"Bible reference: {api_ref}")
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            print(f"API error: {data['error']}")
            return ""
        # Combine all verses if present
        verses = data.get("verses", [])
        if verses:
            texts = [v.get("text", "").strip() for v in verses]
            combined = " ".join(texts)
            translation = data.get("translation_name", "")
            return f"{ref} ({translation}): {combined}"
        fallback_text = data.get("text", "").strip()
        if fallback_text:
            return fallback_text
        print("No text found in API response.")
        return ""
    except requests.exceptions.Timeout:
        print("Request to Bible API timed out.")
        return ""
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return ""
    except Exception as e:
        print(f"Unexpected error occurred in fetch_bible_text: {e}")
        return ""


def load_template(mode: str) -> str:
    """
    Load the prompt template for the given mode from the prompts directory.
    """
    template_path = TEMPLATES_DIR / f"{mode}.txt"
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template for mode '{mode}' not found at {template_path}"
        )
    return template_path.read_text(encoding="utf-8")


def truncate_context(context: str, max_chars: int = 2000) -> str:
    """
    Truncate the context string to at most `max_chars` characters,
    preserving the beginning of the text for relevance.
    Includes robust input validation and error handling.
    """
    # Validate inputs
    if not isinstance(context, str):
        raise ValueError("Expected 'context' to be a string.")
    if not isinstance(max_chars, int) or max_chars <= 0:
        raise ValueError("Expected 'max_chars' to be a positive integer.")

    try:
        # If context length is within the limit, return as is.
        if len(context) <= max_chars:
            return context
        # Otherwise, return only the first max_chars characters.
        return context[:max_chars]
    except Exception as e:
        print(f"Unexpected error during context truncation: {e}")
        # In an error scenario, attempt a safe fallback truncation
        return context[:max_chars]


def build_prompt(
    mode: str,
    question: str,
    context: str,
    lang: str = "es",
    max_context_chars: Optional[int] = 2000,
) -> dict:
    """
    Build the final LLM prompt by:
    1. Loading the template for `mode` (e.g., 'explain', 'reflect', 'apply', 'summarize', 'ask').
    2. Truncating the context to avoid exceeding token limits.
    3. Replacing placeholders in the template with the truncated context, question, and language.

    Templates should use placeholders:
      {context}, {question}, {lang}

    Returns a dictionary with the keys:
      - "prompt": the final prompt string
      - "refs": a set of Bible references found (which might be empty)

    Errors are logged and a fallback prompt is returned in case of failure.
    """
    # Input validation and guard clauses
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("Invalid input: 'mode' must be a non-empty string.")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Invalid input: 'question' must be a non-empty string.")
    if not isinstance(context, str):
        raise ValueError("Invalid input: 'context' must be a string.")
    if not isinstance(lang, str) or not lang.strip():
        raise ValueError("Invalid input: 'lang' must be a non-empty string.")
    if not isinstance(max_context_chars, int) or max_context_chars <= 0:
        raise ValueError(
            "Invalid input: 'max_context_chars' must be a positive integer."
        )

    try:
        # Clean inputs
        question = clean_text(question)
        context = clean_text(context)

        # Load template text
        template = load_template(mode)

        # Find Bible references from question and context
        refs = set(find_bible_references(question) + find_bible_references(context))

        # Prepare Bible references section
        bible_section = ""
        if refs:
            lines = []
            for ref in refs:
                fetched = fetch_bible_text(ref)
                if fetched:
                    lines.append(fetched)
                else:
                    # Log a warning if a particular reference didn't yield text
                    print(f"Warning: No text fetched for Bible reference: {ref}")
            bible_section = "\n".join(lines)

        # Prepare the full context by including Bible references if available
        if bible_section:
            full_context = f"Bible references: {bible_section}\nRAG: {context}"
            effective_max = max_context_chars + len(bible_section)
        else:
            full_context = context
            effective_max = max_context_chars

        # Truncate full context ensuring Bible references are retained
        truncated = truncate_context(full_context, max_chars=effective_max)

        # Build the final prompt using the template
        prompt = template.format(context=truncated, question=question, lang=lang)

        return {"prompt": prompt, "refs": refs}
    except Exception as e:
        # Log the error and return a fallback prompt
        print(f"Error generating prompt: {e}")
        fallback_prompt = (
            "An error occurred while building the prompt. Please try again later."
        )
        return {"prompt": fallback_prompt, "refs": set()}

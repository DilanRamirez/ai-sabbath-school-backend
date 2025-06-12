import re

# Complete list of 66 books in Reina-Valera 1960 canonical order
FULL_BOOKS = [
    "Génesis",
    "Éxodo",
    "Levítico",
    "Números",
    "Deuteronomio",
    "Josué",
    "Jueces",
    "Rut",
    "1 Samuel",
    "2 Samuel",
    "1 Reyes",
    "2 Reyes",
    "1 Crónicas",
    "2 Crónicas",
    "Esdras",
    "Nehemías",
    "Ester",
    "Job",
    "Salmos",
    "Proverbios",
    "Eclesiastés",
    "Cantares",
    "Isaías",
    "Jeremías",
    "Lamentaciones",
    "Ezequiel",
    "Daniel",
    "Oseas",
    "Joel",
    "Amós",
    "Abdías",
    "Jonás",
    "Miqueas",
    "Nahúm",
    "Habacuc",
    "Sofonías",
    "Hageo",
    "Zacarías",
    "Malaquías",
    "S. Mateo",
    "S. Marcos",
    "S. Lucas",
    "S. Juan",
    "Hechos",
    "Romanos",
    "1 Corintios",
    "2 Corintios",
    "Gálatas",
    "Efesios",
    "Filipenses",
    "Colosenses",
    "1 Tesalonicenses",
    "2 Tesalonicenses",
    "1 Timoteo",
    "2 Timoteo",
    "Tito",
    "Filemón",
    "Hebreos",
    "Santiago",
    "1 Pedro",
    "2 Pedro",
    "1 Juan",
    "2 Juan",
    "3 Juan",
    "Judas",
    "Apocalipsis",
]

# Map Spanish book names and common abbreviations to Spanish full book names (Reina-Valera 1960)
SPANISH_BOOK_MAP = {
    # Pentateuco
    "Génesis": "Génesis",
    "Gén.": "Génesis",
    "Éxodo": "Éxodo",
    "Éxo.": "Éxodo",
    "Levítico": "Levítico",
    "Lev.": "Levítico",
    "Números": "Números",
    "Núm.": "Números",
    "Deuteronomio": "Deuteronomio",
    "Deut.": "Deuteronomio",
    # Libros históricos
    "Josué": "Josué",
    "Jos.": "Josué",
    "Jueces": "Jueces",
    "Jue.": "Jueces",
    "Rut": "Rut",
    "1 Samuel": "1 Samuel",
    "1 Sam.": "1 Samuel",
    "2 Samuel": "2 Samuel",
    "2 Sam.": "2 Samuel",
    "1 Reyes": "1 Reyes",
    "1 Rey.": "1 Reyes",
    "2 Reyes": "2 Reyes",
    "2 Rey.": "2 Reyes",
    "1 Crónicas": "1 Crónicas",
    "1 Crón.": "1 Crónicas",
    "2 Crónicas": "2 Crónicas",
    "2 Crón.": "2 Crónicas",
    "Esdras": "Esdras",
    "Esd.": "Esdras",
    "Nehemías": "Nehemías",
    "Neh.": "Nehemías",
    "Ester": "Ester",
    "Est.": "Ester",
    # Poéticos y sabiduría
    "Job": "Job",
    "Salmos": "Salmos",
    "Sal.": "Salmos",
    "Proverbios": "Proverbios",
    "Prov.": "Proverbios",
    "Eclesiastés": "Eclesiastés",
    "Ecl.": "Eclesiastés",
    "Cantares": "Cantares",
    "Cant.": "Cantares",
    # Profetas mayores
    "Isaías": "Isaías",
    "Isa.": "Isaías",
    "Jeremías": "Jeremías",
    "Jer.": "Jeremías",
    "Lamentaciones": "Lamentaciones",
    "Lam.": "Lamentaciones",
    "Ezequiel": "Ezequiel",
    "Ezeq.": "Ezequiel",
    "Daniel": "Daniel",
    "Dan.": "Daniel",
    # Profetas menores
    "Oseas": "Oseas",
    "Os.": "Oseas",
    "Joel": "Joel",
    "Jon.": "Joel",
    "Amós": "Amós",
    "Am.": "Amós",
    "Abdías": "Abdías",
    "Abd.": "Abdías",
    "Jonás": "Jonás",
    "Jon.": "Jonás",
    "Miqueas": "Miqueas",
    "Mic.": "Miqueas",
    "Nahúm": "Nahúm",
    "Nah.": "Nahúm",
    "Habacuc": "Habacuc",
    "Hab.": "Habacuc",
    "Sofonías": "Sofonías",
    "Sof.": "Sofonías",
    "Hageo": "Hageo",
    "Hag.": "Hageo",
    "Zacarías": "Zacarías",
    "Zac.": "Zacarías",
    "Malaquías": "Malaquías",
    "Mal.": "Malaquías",
    # Evangelios
    "Mateo": "S. Mateo",
    "Mat.": "S. Mateo",
    "Marcos": "S. Marcos",
    "Mr.": "S. Marcos",
    "Lucas": "S. Lucas",
    "Luc.": "S. Lucas",
    "Juan": "S. Juan",
    "Jn.": "S. Juan",
    # Hechos
    "Hechos": "Hechos",
    "Hech.": "Hechos",
    # Epístolas Paulinas
    "Romanos": "Romanos",
    "Rom.": "Romanos",
    "1 Corintios": "1 Corintios",
    "1 Cor.": "1 Corintios",
    "2 Corintios": "2 Corintios",
    "2 Cor.": "2 Corintios",
    "Gálatas": "Gálatas",
    "Gal.": "Gálatas",
    "Efesios": "Efesios",
    "Efe.": "Efesios",
    "Filipenses": "Filipenses",
    "Fil.": "Filipenses",
    "Colosenses": "Colosenses",
    "Col.": "Colosenses",
    "1 Tesalonicenses": "1 Tesalonicenses",
    "1 Tes.": "1 Tesalonicenses",
    "2 Tesalonicenses": "2 Tesalonicenses",
    "2 Tes.": "2 Tesalonicenses",
    "1 Timoteo": "1 Timoteo",
    "1 Tim.": "1 Timoteo",
    "2 Timoteo": "2 Timoteo",
    "2 Tim.": "2 Timoteo",
    "Tito": "Tito",
    "Ti.": "Tito",
    "Filemón": "Filemón",
    "Flm.": "Filemón",
    "Hebreos": "Hebreos",
    "Heb.": "Hebreos",
    # Epístolas generales
    "Santiago": "Santiago",
    "Sant.": "Santiago",
    "1 Pedro": "1 Pedro",
    "1 Pe.": "1 Pedro",
    "2 Pedro": "2 Pedro",
    "2 Pe.": "2 Pedro",
    "1 Juan": "1 Juan",
    "1 Jn.": "1 Juan",
    "2 Juan": "2 Juan",
    "2 Jn.": "2 Juan",
    "3 Juan": "3 Juan",
    "3 Jn.": "3 Juan",
    "Judas": "Judas",
    # Apocalipsis
    "Apocalipsis": "Apocalipsis",
    "Apoc.": "Apocalipsis",
}


def parse_reference(ref: str) -> dict:
    """
    Parse a scripture reference string into its components.
    Supports formats like:
      - 'Mateo 12:9-14'
      - 'Juan 5:1-16'
      - '2 Tim. 1:7'
    Returns a dict with keys:
      book: full book name matching BIBLE keys
      chapter: str chapter number
      verse_start: str starting verse
      verse_end: optional ending verse or same as start if single
    """
    # Normalize spacing
    ref = ref.strip()
    # Split book and rest
    match = re.match(r"^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$", ref)
    if not match:
        raise ValueError(f"Invalid reference format: '{ref}'")
    book_part, chapter, verse_start, verse_end = match.groups()
    # Extract numeric prefix
    num_prefix = ""
    book_name = book_part
    num_match = re.match(r"^(?P<num>\d+)\s*(?P<name>.+)$", book_part)
    print(num_match)
    if num_match:
        num_prefix = num_match.group("num") + " "
        book_name = num_match.group("name")
    # Normalize book name using SPANISH_BOOK_MAP
    # Prefer matching the entire book_part (including number prefix)
    if book_part in SPANISH_BOOK_MAP:
        book_key = SPANISH_BOOK_MAP[book_part]
    else:
        # Then match the base name without numeric prefix
        mapped = SPANISH_BOOK_MAP.get(book_name)
        if mapped:
            book_key = f"{num_prefix}{mapped}"
        else:
            # fallback to reconstructed name
            book_key = f"{num_prefix}{book_name}"
    # Build result
    return {
        "book": book_key,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end or verse_start,
    }

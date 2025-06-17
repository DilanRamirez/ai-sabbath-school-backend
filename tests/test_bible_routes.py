import pytest
from fastapi.testclient import TestClient
from app.main import app  # adjust import as needed

client = TestClient(app)


def test_list_books_returns_books_and_missing():
    response = client.get("/api/v1/bible/books")
    assert response.status_code == 200
    data = response.json()
    assert "books" in data and isinstance(data["books"], list)
    # Ensure a known book is available and a known missing (if any) is correct type
    assert "Génesis" in data["books"]


@pytest.mark.parametrize(
    "book,chapter,expected_first_verse",
    [
        ("Génesis", "1", "En el principio creó Dios los cielos y la tierra."),
        # example expected start
        ("S. Juan", "3", "Había un hombre de"),
    ],
)
def test_get_chapter_valid(book, chapter, expected_first_verse):
    response = client.get(f"/api/v1/bible/{book}/{chapter}")
    assert response.status_code == 200
    data = response.json()
    assert data["book"] == book
    assert data["chapter"] == chapter
    verses = data["verses"]
    assert isinstance(verses, dict)
    # check first verse text starts correctly
    assert verses.get("1", "").startswith(expected_first_verse)


@pytest.mark.parametrize(
    "book,chapter,verse,expected_text",
    [
        ("Génesis", "1", "1", "En el principio creó Dios los cielos y la tierra."),
        ("S. Juan", "3", "16", "Porque de tal manera amó Dios al mundo,"),  # example
    ],
)
def test_get_verse_valid(book, chapter, verse, expected_text):
    response = client.get(f"/api/v1/bible/{book}/{chapter}/{verse}")
    assert response.status_code == 200
    data = response.json()
    assert data["book"] == book
    assert data["chapter"] == chapter
    assert data["verse"] == verse
    assert data["text"].startswith(expected_text)


@pytest.mark.parametrize(
    "ref,expect_type,expect_key",
    [
        ("Génesis 1:1", "text", "text"),
        ("S. Juan 3:16-18", "verses", "verses"),
        ("2 Tim. 1:7", "text", "text"),
    ],
)
def test_reference_endpoint(ref, expect_type, expect_key):
    response = client.get("/api/v1/bible/reference", params={"ref": ref})
    assert response.status_code == 200
    data = response.json()
    # Single verse returns 'text', range returns 'verses'
    assert expect_key in data
    if expect_key == "text":
        assert "verse" in data and "text" in data
    else:
        assert isinstance(data["verses"], dict)
        # Verify the range includes the start verse


@pytest.mark.parametrize(
    "endpoint,params,status",
    [
        ("/api/v1/bible/nonexistent/1", None, 404),
        ("/api/v1/bible/Génesis/999", None, 404),
        ("/api/v1/bible/nonexistent/1/1", None, 404),
        ("/api/v1/bible/Génesis/1/999", None, 404),
    ],
)
def test_invalid_requests(endpoint, params, status):
    response = client.get(endpoint, params=params)
    assert response.status_code == status

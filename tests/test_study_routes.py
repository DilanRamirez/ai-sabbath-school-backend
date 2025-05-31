# import pytest
# from fastapi.testclient import TestClient
# from app.main import app
# from unittest.mock import patch
# from datetime import datetime

# client = TestClient(app)


# @pytest.fixture
# def progress_payload():
#     return {
#         "user_id": "test-user",
#         "quarter": "2025-Q2",
#         "lesson_id": "test-lesson",
#         "day": "sunday",
#         "note": "Great lesson today!",
#         "cohort_id": "COHORT#xyz",
#         "mark_studied": True,
#     }


# @patch("app.api.v1.study.table.put_item", return_value={})
# @patch(
#     "app.api.v1.study.table.get_item",
#     return_value={
#         "Item": {
#             "PK": "USER#test-user",
#             "SK": "LESSON#test-lesson",
#             "lesson_id": "test-lesson",
#             "days_completed": ["sunday"],
#             "notes": [{"day": "sunday", "note": "Great lesson today!"}],
#             "last_accessed": datetime.utcnow().isoformat(),
#             "cohort_id": "COHORT#xyz",
#             "score": 0.2,
#             "quarter": "2025-Q2",
#         }
#     },
# )
# def test_update_study(mock_get, mock_put, progress_payload):
#     response = client.post("/api/v1/study/progress", json=progress_payload)
#     assert response.status_code == 200
#     data = response.json()
#     assert data["status"] == "updated"
#     assert "score" in data
#     # new last_position field should be present
#     assert "last_position" in data
#     assert data["last_position"]["quarter"] == progress_payload["quarter"]
#     assert data["last_position"]["lesson_id"] == progress_payload["lesson_id"]
#     assert data["last_position"]["day"] == progress_payload["day"]


# @patch(
#     "app.api.v1.study.table.get_item",
#     return_value={
#         "Item": {
#             "PK": "USER#test-user",
#             "SK": "LESSON#test-lesson",
#             "lesson_id": "test-lesson",
#             "days_completed": ["sunday"],
#             "notes": [{"day": "sunday", "note": "Great lesson today!"}],
#             "last_accessed": datetime.utcnow().isoformat(),
#             "cohort_id": "COHORT#xyz",
#             "score": 0.2,
#             "quarter": "2025-Q2",
#         }
#     },
# )
# def test_get_study(mock_get):
#     response = client.get("/api/v1/study/progress/test-user/test-lesson")
#     assert response.status_code == 200
#     data = response.json()
#     assert data["lesson_id"] == "test-lesson"
#     assert "days_completed" in data


# @patch("app.api.v1.study.table.get_item", side_effect=Exception("boom"))
# def test_get_study_exception(mock_get):
#     response = client.get("/api/v1/study/progress/test-user/test-lesson")
#     assert response.status_code == 500
#     assert "boom" in response.json()["detail"]


# @patch("app.api.v1.study.table.put_item", side_effect=Exception("boom"))
# @patch("app.api.v1.study.table.get_item", return_value={})
# def test_update_study_exception(mock_get, mock_put, progress_payload):
#     response = client.post("/api/v1/study/progress", json=progress_payload)
#     assert response.status_code == 500
#     assert "boom" in response.json()["detail"]


# @patch("app.api.v1.study.table.put_item", return_value={})
# @patch(
#     "app.api.v1.study.table.get_item",
#     return_value={
#         "Item": {
#             "PK": "USER#test-user",
#             "SK": "LESSON#test-lesson",
#             "lesson_id": "test-lesson",
#             "days_completed": [],
#             "notes": [],
#             "last_accessed": datetime.utcnow().isoformat(),
#             "cohort_id": "COHORT#xyz",
#             "score": 0.0,
#             "quarter": "2025-Q2",
#         }
#     },
# )
# def test_update_study_without_marking(mock_get, mock_put, progress_payload):
#     progress_payload["mark_studied"] = False
#     response = client.post("/api/v1/study/progress", json=progress_payload)
#     assert response.status_code == 200
#     assert "score" in response.json()


# @patch("app.api.v1.study.table.put_item", return_value={})
# @patch(
#     "app.api.v1.study.table.get_item",
#     return_value={
#         "Item": {
#             "PK": "USER#test-user",
#             "SK": "LESSON#test-lesson",
#             "lesson_id": "test-lesson",
#             "days_completed": ["sunday"],
#             "notes": [{"day": "sunday", "note": "Old note"}],
#             "last_accessed": datetime.utcnow().isoformat(),
#             "cohort_id": "COHORT#xyz",
#             "score": 0.1,
#             "quarter": "2025-Q2",
#         }
#     },
# )
# def test_update_study_duplicate_note_updates(mock_get, mock_put, progress_payload):
#     response = client.post("/api/v1/study/progress", json=progress_payload)
#     assert response.status_code == 200
#     assert "score" in response.json()

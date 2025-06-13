from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.core.config import dynamodb

router = APIRouter()
table = dynamodb.Table("SabbathSchoolApp")


class StudyProgressUpdate(BaseModel):
    user_id: str
    lesson_id: str
    day: str
    quarter: str
    note: Optional[str] = None
    cohort_id: Optional[str] = None
    mark_studied: Optional[bool] = False
    question_id: Optional[str] = None
    content: Optional[str] = None


def normalize_user_id(user_id: str) -> str:
    return user_id.replace("@", "-at-").replace(".", "-dot-")


def compute_score(days_completed: List[str], notes: List[dict]) -> Decimal:
    score = len(set(days_completed)) * 0.1 + len(notes) * 0.1
    return min(Decimal(str(score)), Decimal("1.0"))


@router.post("/progress")
def update_study_progress(payload: StudyProgressUpdate):
    normalized_id = normalize_user_id(payload.user_id)
    pk = f"USER#{normalized_id}"
    sk = f"LESSON#{payload.lesson_id}"

    try:
        result = table.get_item(Key={"PK": pk, "SK": sk})
        item = result.get(
            "Item",
            {
                "PK": pk,
                "SK": sk,
                "lesson_id": payload.lesson_id,
                "days_completed": [],
                "notes": [],
            },
        )

        if payload.mark_studied and payload.day not in item["days_completed"]:
            item["days_completed"].append(payload.day)

        # Update or delete note entry based on payload.note
        existing_note = next(
            (
                n
                for n in item["notes"]
                if n["day"] == payload.day
                and n.get("question_id") == payload.question_id
            ),
            None,
        )
        if payload.note and payload.note.strip():
            # Add or update note
            if existing_note:
                existing_note["note"] = payload.note
            else:
                item["notes"].append(
                    {
                        "day": payload.day,
                        "note": payload.note,
                        "question_id": payload.question_id,
                        "lesson_id": payload.lesson_id,
                        "quarter": payload.quarter,
                        "content": payload.content,
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
        else:
            # Delete existing note if present
            if existing_note:
                item["notes"] = [
                    n
                    for n in item["notes"]
                    if not (
                        n["day"] == payload.day
                        and n.get("question_id") == payload.question_id
                    )
                ]

        item["last_position"] = {
            "quarter": payload.quarter,
            "lesson_id": payload.lesson_id,
            "day": payload.day,
        }
        item["last_accessed"] = datetime.utcnow().isoformat()
        item["cohort_id"] = payload.cohort_id or item.get("cohort_id")
        item["score"] = compute_score(item["days_completed"], item["notes"])

        table.put_item(Item=item)
        return {"status": "updated", "score": item["score"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# New route to get study progress for a specific user and lesson
@router.get("/progress/{user_id}/{lesson_id}")
def get_study_progress(user_id: str, lesson_id: str):
    normalized_id = normalize_user_id(user_id)
    pk = f"USER#{normalized_id}"
    sk = f"LESSON#{lesson_id}"

    try:
        result = table.get_item(Key={"PK": pk, "SK": sk})
        item = result.get("Item")
        if not item:
            raise HTTPException(status_code=404, detail="Progress not found")
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to get all study progress records for a user
@router.get("/progress/{user_id}")
def get_all_study_progress_for_user(user_id: str):
    normalized_id = normalize_user_id(user_id)
    pk = f"USER#{normalized_id}"
    try:
        response = table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": pk},
        )
        items = response.get("Items", [])
        if not items:
            raise HTTPException(
                status_code=404, detail="No progress records found for user"
            )
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint to return a summary of the user's study progress


def is_this_week(date_str: str) -> bool:
    try:
        today = datetime.utcnow()
        date = datetime.fromisoformat(date_str)
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week.date() <= date.date() <= end_of_week.date()
    except Exception:
        return False


@router.get("/progress-summary/{user_id}")
def get_study_progress_summary(user_id: str):
    normalized_id = normalize_user_id(user_id)
    pk = f"USER#{normalized_id}"
    try:
        response = table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": pk},
        )
        items = response.get("Items", [])
        if not items:
            raise HTTPException(
                status_code=404, detail="No progress records found for user"
            )

        total_lessons_in_quarter = 13  # Ideally dynamic based on current quarter
        days_this_week = set()
        notes_this_week = 0
        lessons_completed = 0

        for item in items:
            days_completed = item.get("days_completed", [])
            notes = item.get("notes", [])
            if len(set(days_completed)) >= 7:
                lessons_completed += 1
            for note in notes:
                if note.get("created_at") and is_this_week(note["created_at"]):
                    notes_this_week += 1
            if is_this_week(item.get("last_accessed", "")):
                days_this_week.update(days_completed)

        return {
            "daysCompletedThisWeek": len(days_this_week),
            "notesWrittenThisWeek": notes_this_week,
            "lessonsCompleted": lessons_completed,
            "totalLessonsInQuarter": total_lessons_in_quarter,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint to get the last viewed position of the user
@router.get("/last-position/{user_id}")
def get_last_position(user_id: str):
    normalized_id = normalize_user_id(user_id)
    pk = f"USER#{normalized_id}"
    try:
        response = table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": pk},
        )
        items = response.get("Items", [])
        if not items:
            raise HTTPException(
                status_code=404, detail="No progress records found for user"
            )

        last_item = max(items, key=lambda x: x.get("last_accessed", ""))
        return last_item.get("last_position", {})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint to get progress for a specific lesson (with explicit Path params)
@router.get("/progress/{user_id}/{lesson_id}")
def get_lesson_progress(user_id: str = Path(...), lesson_id: str = Path(...)):
    normalized_id = normalize_user_id(user_id)
    pk = f"USER#{normalized_id}"
    sk = f"LESSON#{lesson_id}"

    try:
        result = table.get_item(Key={"PK": pk, "SK": sk})
        item = result.get("Item")
        if not item:
            raise HTTPException(status_code=404, detail="Progress not found")
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, HTTPException
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


def compute_score(days_completed: List[str], notes: List[dict]) -> Decimal:
    score = len(set(days_completed)) * 0.1 + len(notes) * 0.1
    return min(Decimal(str(score)), Decimal("1.0"))


@router.post("/progress")
def update_study_progress(payload: StudyProgressUpdate):
    pk = f"USER#{payload.user_id}"
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

        if payload.note:
            existing_note = next(
                (
                    n
                    for n in item["notes"]
                    if n["day"] == payload.day
                    and n.get("question_id") == payload.question_id
                ),
                None,
            )
            if existing_note:
                existing_note["note"] = payload.note
            else:
                item["notes"].append(
                    {
                        "day": payload.day,
                        "note": payload.note,
                        "question_id": payload.question_id,
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )

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
    pk = f"USER#{user_id}"
    sk = f"LESSON#{lesson_id}"

    try:
        result = table.get_item(Key={"PK": pk, "SK": sk})
        item = result.get("Item")
        if not item:
            raise HTTPException(status_code=404, detail="Progress not found")
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

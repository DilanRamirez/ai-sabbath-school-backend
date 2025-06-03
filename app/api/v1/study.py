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
    content: Optional[str] = None


def normalize_user_id(user_id: str) -> str:
    return user_id.replace("@", "-at-").replace(".", "-dot-")


def compute_score(days_completed: List[str], notes: List[dict]) -> Decimal:
    score = len(set(days_completed)) * 0.1 + len(notes) * 0.1
    return min(Decimal(str(score)), Decimal("1.0"))


@router.post("/progress")
def update_study_progress(payload: StudyProgressUpdate):
    normalized_id = normalize_user_id(payload.user_id)
    print(
        f"Updating progress for user: {normalized_id}, lesson: {payload.lesson_id}, day: {payload.day}"
    )
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
            print(f"Existing note found: {existing_note}")
            print(f"content: {payload.content}")
            if existing_note:
                existing_note["note"] = payload.note
            else:
                item["notes"].append(
                    {
                        "day": payload.day,
                        "note": payload.note,
                        "question_id": payload.question_id,
                        "content": payload.content,
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
    normalized_id = normalize_user_id(user_id)
    print(f"Retrieving progress for user: {normalized_id}, lesson: {lesson_id}")
    pk = f"USER#{normalized_id}"
    sk = f"LESSON#{lesson_id}"

    try:
        result = table.get_item(Key={"PK": pk, "SK": sk})
        print(f"Result from DynamoDB: {result}")
        item = result.get("Item")
        print(f"Retrieved item: {item}")
        if not item:
            raise HTTPException(status_code=404, detail="Progress not found")
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to get all study progress records for a user
@router.get("/progress/{user_id}")
def get_all_study_progress_for_user(user_id: str):
    normalized_id = normalize_user_id(user_id)
    print(f"Retrieving all progress for user: {normalized_id}")
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

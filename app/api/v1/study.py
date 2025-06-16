import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.core.config import dynamodb
from app.core.config import BUCKET, s3


router = APIRouter()
table = dynamodb.Table("SabbathSchoolApp")


class StudyProgressUpdate(BaseModel):
    user_id: str
    lesson_id: str
    day: str
    quarter: str
    year: str
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
            "year": payload.year,
        }
        item["last_accessed"] = datetime.utcnow().isoformat()
        item["cohort_id"] = payload.cohort_id or item.get("cohort_id")
        item["score"] = compute_score(item["days_completed"], item["notes"])

        table.put_item(Item=item)
        return {"status": "updated", "score": item["score"]}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong on the server. Please try again. ({str(e)})",
        )


# Endpoint to get a full lesson report for a user
@router.get("/report/{year}/{quarter}/{lesson_id}/{user_id}")
def get_full_lesson_report(year: str, quarter: str, lesson_id: str, user_id: str):
    """
    Retrieves a comprehensive report for a specific lesson and user,
    including lesson metadata, AI-generated summaries, and the user's notes and progress.
    """
    # Validate inputs
    if not user_id.strip():
        raise HTTPException(status_code=400, detail="Missing user ID.")
    if not all([year, quarter, lesson_id]):
        raise HTTPException(status_code=400, detail="Missing report path parameters.")

    # Normalize and build keys
    normalized_user = normalize_user_id(user_id)
    pk = f"USER#{normalized_user}"
    sk = f"LESSON#{lesson_id}"

    # Fetch user progress data
    try:
        db_result = table.get_item(Key={"PK": pk, "SK": sk})
        item = db_result.get("Item", {"days_completed": [], "notes": []})
    except Exception as db_err:
        raise HTTPException(
            status_code=500, detail=f"Error fetching user progress: {str(db_err)}"
        )

    # Fetch lesson metadata and AI summaries from S3
    metadata_key = f"{year}/{quarter}/{lesson_id}/metadata.json"
    summary_key = f"{year}/{quarter}/{lesson_id}/lesson.json"
    try:
        metadata_obj = s3.get_object(Bucket=BUCKET, Key=metadata_key)
        summary_obj = s3.get_object(Bucket=BUCKET, Key=summary_key)
        metadata = json.loads(metadata_obj["Body"].read())
        lesson_summary = json.loads(summary_obj["Body"].read())
    except Exception as s3_err:
        raise HTTPException(
            status_code=500, detail=f"Error loading lesson files from S3: {str(s3_err)}"
        )

    # Assemble report payload
    report = {
        "metadata": metadata,
        "aiSummaries": lesson_summary.get("days", []),
        "userProgress": {
            "daysCompleted": item.get("days_completed", []),
            "notes": item.get("notes", []),
            "lastPosition": item.get("last_position", {}),
            "score": item.get("score"),
        },
    }

    return report


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
            raise HTTPException(
                status_code=404,
                detail="No progress found for this lesson. Start studying to see your progress here!",
            )
        return item
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong on the server. Please try again. ({str(e)})",
        )


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
                status_code=404,
                detail="No study progress records were found for this user. Start your journey by selecting a lesson!",
            )
        return items
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong on the server. Please try again. ({str(e)})",
        )


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

        # Guard clause: prevent processing logic on empty response
        if not items:
            return {
                "daysCompletedThisWeek": 0,
                "notesWrittenThisWeek": 0,
                "lessonsCompleted": 0,
                "totalLessonsInQuarter": 13,
            }

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
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong on the server. Please try again. ({str(e)})",
        )


# Endpoint to get the last viewed position of the user


@router.get("/last-position/{user_id}")
def get_last_viewed_position(user_id: str):
    """
    Retrieves the user's last viewed position along with associated metadata and AI summary.
    """
    # Validate input
    if not user_id.strip():
        raise HTTPException(
            status_code=400, detail="Missing user ID. Please log in again."
        )

    normalized_user_id = normalize_user_id(user_id)
    primary_key = f"USER#{normalized_user_id}"

    try:
        # Query progress records for the user.
        progress_query = table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": primary_key},
        )
        progress_records = progress_query.get("Items", [])
        if not progress_records:
            return None

        # Select the record with the latest 'last_accessed' timestamp.
        last_progress_record = max(
            progress_records, key=lambda rec: rec.get("last_accessed") or ""
        )
        last_position = last_progress_record.get("last_position", {})
        if not last_position:
            raise HTTPException(
                status_code=404,
                detail="We couldn't find the last position. Try opening a lesson to get started.",
            )

        # Validate that essential fields are present.
        year = last_position.get("year")
        lesson_id = last_position.get("lesson_id")
        quarter = last_position.get("quarter")
        current_day = last_position.get("day")
        if not all([year, lesson_id, quarter, current_day]):
            raise HTTPException(
                status_code=400,
                detail="Lesson navigation data is incomplete. Try reopening the lesson.",
            )

        # Construct S3 keys to fetch metadata and lesson summary.
        metadata_key = f"{year}/{quarter}/{lesson_id}/metadata.json"
        lesson_summary_key = f"{year}/{quarter}/{lesson_id}/lesson.json"

        # Attempt to load metadata and lesson summary from S3.
        try:
            metadata_object = s3.get_object(Bucket=BUCKET, Key=metadata_key)
            lesson_summary_object = s3.get_object(Bucket=BUCKET, Key=lesson_summary_key)
            metadata = json.loads(metadata_object["Body"].read())
            lesson_summary = json.loads(lesson_summary_object["Body"].read())
        except Exception as s3_error:
            raise HTTPException(
                status_code=500,
                detail=f"Error loading metadata files from S3: {str(s3_error)}",
            )

        # Extract today's AI summary from lesson summary
        days_summary = lesson_summary.get("days")
        if not days_summary or not isinstance(days_summary, list):
            raise HTTPException(
                status_code=404,
                detail="We couldn't load the lesson summary. Please try again later.",
            )

        day_summary = next(
            (day for day in days_summary if day.get("day") == current_day), None
        )
        if day_summary is None:
            raise HTTPException(
                status_code=404,
                detail=f"No summary found for {current_day}. Start studying to generate insights!",
            )

        return {
            "position": last_position,
            "metadata": metadata,
            "aiSummaryDay": day_summary.get("daySummary", ""),
        }

    except HTTPException as http_err:
        raise http_err
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong on the server. Please try again. ({str(error)})",
        )


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
            raise HTTPException(
                status_code=404,
                detail="No progress found for this lesson. Start studying to see your progress here!",
            )
        return item
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong on the server. Please try again. ({str(e)})",
        )

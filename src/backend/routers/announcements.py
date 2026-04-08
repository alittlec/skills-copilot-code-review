"""
Announcement endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_announcements(active_only: bool = True) -> List[Dict[str, Any]]:
    """Get all announcements, optionally filtering to only active ones"""
    now = datetime.utcnow().isoformat()

    if active_only:
        query = {
            "expiration_date": {"$gte": now},
            "$or": [
                {"start_date": {"$exists": False}},
                {"start_date": None},
                {"start_date": ""},
                {"start_date": {"$lte": now}}
            ]
        }
    else:
        query = {}

    announcements = []
    for doc in announcements_collection.find(query).sort("created_at", -1):
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        announcements.append(doc)

    return announcements


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: str = Query(...)) -> List[Dict[str, Any]]:
    """Get all announcements (including expired) - requires authentication"""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    announcements = []
    for doc in announcements_collection.find().sort("created_at", -1):
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        announcements.append(doc)

    return announcements


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    title: str = Query(..., min_length=1, max_length=200),
    message: str = Query(..., min_length=1, max_length=1000),
    expiration_date: str = Query(...),
    start_date: Optional[str] = Query(None),
    teacher_username: str = Query(...)
) -> Dict[str, Any]:
    """Create a new announcement - requires teacher authentication"""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate expiration date
    try:
        exp_date = datetime.fromisoformat(expiration_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expiration date format")

    if exp_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Expiration date must be in the future")

    # Validate start date if provided
    if start_date:
        try:
            datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start date format")

    announcement = {
        "title": title,
        "message": message,
        "start_date": start_date or "",
        "expiration_date": expiration_date,
        "created_by": teacher_username,
        "created_at": datetime.utcnow().isoformat()
    }

    result = announcements_collection.insert_one(announcement)
    announcement["id"] = str(result.inserted_id)
    del announcement["_id"]

    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    title: str = Query(..., min_length=1, max_length=200),
    message: str = Query(..., min_length=1, max_length=1000),
    expiration_date: str = Query(...),
    start_date: Optional[str] = Query(None),
    teacher_username: str = Query(...)
) -> Dict[str, Any]:
    """Update an existing announcement - requires teacher authentication"""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate the announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    existing = announcements_collection.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Validate expiration date
    try:
        datetime.fromisoformat(expiration_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expiration date format")

    # Validate start date if provided
    if start_date:
        try:
            datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start date format")

    update_data = {
        "title": title,
        "message": message,
        "start_date": start_date or "",
        "expiration_date": expiration_date,
    }

    announcements_collection.update_one({"_id": obj_id}, {"$set": update_data})

    updated = announcements_collection.find_one({"_id": obj_id})
    updated["id"] = str(updated["_id"])
    del updated["_id"]

    return updated


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: str = Query(...)
) -> Dict[str, str]:
    """Delete an announcement - requires teacher authentication"""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    result = announcements_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted successfully"}

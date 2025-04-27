from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
from app.services.liveness import liveness_service
from app.models.liveness import LivenessCheck
from app.core.security import get_current_user
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()

class LivenessCheckResponse(BaseModel):
    id: int
    status: str
    confidence_score: Optional[float]
    verification_type: str
    media_url: Optional[str]
    error_message: Optional[str]
    timestamp: str

    class Config:
        from_attributes = True

@router.post("/verify", response_model=LivenessCheckResponse)
async def verify_liveness(
    verification_type: str,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Verify liveness of a user through various methods (blink, smile, etc.)
    """
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        image_data = await image.read()
        liveness_check = await liveness_service.create_liveness_check(
            user_id=current_user.id,
            verification_type=verification_type,
            image_data=image_data
        )
        return liveness_check
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing liveness check")

@router.get("/checks", response_model=List[LivenessCheckResponse])
async def get_liveness_checks(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get all liveness checks for the current user
    """
    checks = await liveness_service.get_user_liveness_checks(
        user_id=current_user.id,
        status=status
    )
    return checks

@router.get("/checks/{check_id}", response_model=LivenessCheckResponse)
async def get_liveness_check(
    check_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific liveness check by ID
    """
    check = await liveness_service.get_liveness_check(check_id)
    if not check:
        raise HTTPException(status_code=404, detail="Liveness check not found")
    if check.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this check")
    return check 
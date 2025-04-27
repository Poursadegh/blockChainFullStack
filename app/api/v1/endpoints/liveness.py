from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import List, Optional
from app.services.liveness import liveness_service
from app.models.liveness import LivenessCheck
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.liveness import (
    LivenessCheckResponse,
    LivenessCheckList,
    LivenessVerificationRequest,
    LivenessVerificationResponse
)
from app.schemas.base import ResponseSchema

router = APIRouter()

@router.post("/verify", response_model=LivenessVerificationResponse)
async def verify_liveness(
    request: LivenessVerificationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Verify liveness of a user through various methods (blink, smile, etc.)
    """
    try:
        # Convert base64 to bytes
        import base64
        image_data = base64.b64decode(request.image_data)
        
        liveness_check = await liveness_service.create_liveness_check(
            user_id=current_user.id,
            verification_type=request.verification_type,
            image_data=image_data
        )
        
        return LivenessVerificationResponse(
            success=liveness_check.status == "completed",
            confidence_score=liveness_check.confidence_score,
            message="Verification successful" if liveness_check.status == "completed" else liveness_check.error_message,
            check_id=liveness_check.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing liveness check")

@router.get("/checks", response_model=LivenessCheckList)
async def get_liveness_checks(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    Get all liveness checks for the current user with pagination
    """
    checks = await liveness_service.get_user_liveness_checks(
        user_id=current_user.id,
        status=status
    )
    
    # Implement pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_checks = checks[start:end]
    
    return LivenessCheckList(
        items=paginated_checks,
        total=len(checks),
        page=page,
        per_page=per_page
    )

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

@router.delete("/checks/{check_id}", response_model=ResponseSchema)
async def delete_liveness_check(
    check_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific liveness check
    """
    check = await liveness_service.get_liveness_check(check_id)
    if not check:
        raise HTTPException(status_code=404, detail="Liveness check not found")
    if check.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this check")
    
    await check.delete()
    return ResponseSchema(message="Liveness check deleted successfully") 
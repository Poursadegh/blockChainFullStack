from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from .base import BaseSchema, TimestampSchema

class LivenessCheckBase(BaseSchema):
    verification_type: str = Field(..., description="Type of verification (blink, smile, etc.)")
    status: str = Field(..., description="Status of the check (pending, completed, failed)")
    confidence_score: Optional[float] = Field(None, description="Confidence score of the verification")
    result: Optional[Dict[str, Any]] = Field(None, description="Detailed verification results")
    media_url: Optional[str] = Field(None, description="URL to the stored media")
    error_message: Optional[str] = Field(None, description="Error message if verification failed")

class LivenessCheckCreate(BaseSchema):
    verification_type: str = Field(..., description="Type of verification to perform")
    image_data: bytes = Field(..., description="Base64 encoded image data")

class LivenessCheckResponse(LivenessCheckBase, TimestampSchema):
    id: int
    user_id: int
    attempts: int = Field(..., description="Number of verification attempts")
    max_attempts: int = Field(..., description="Maximum allowed attempts")

class LivenessCheckList(BaseSchema):
    items: list[LivenessCheckResponse]
    total: int
    page: int
    per_page: int

class LivenessVerificationRequest(BaseSchema):
    verification_type: str = Field(..., description="Type of verification to perform")
    image_data: str = Field(..., description="Base64 encoded image data")

class LivenessVerificationResponse(BaseSchema):
    success: bool
    confidence_score: Optional[float]
    message: str
    check_id: Optional[int] = None 
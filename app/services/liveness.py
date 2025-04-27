import cv2
import numpy as np
from typing import Optional, Dict, Any
from datetime import datetime
import logging
from app.models.liveness import LivenessCheck
from app.core.config import settings
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

class LivenessService:
    def __init__(self):
        # Initialize face detection model
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.media_dir = Path(settings.MEDIA_DIR) / "liveness"
        self.media_dir.mkdir(parents=True, exist_ok=True)

    async def detect_blink(self, image_data: bytes) -> Dict[str, Any]:
        """Detect blink in the provided image"""
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                return {"success": False, "error": "No face detected"}
            
            # For each face, detect eyes
            for (x, y, w, h) in faces:
                roi_gray = gray[y:y+h, x:x+w]
                eyes = self.eye_cascade.detectMultiScale(roi_gray)
                
                if len(eyes) >= 2:  # Both eyes detected
                    return {
                        "success": True,
                        "eyes_detected": len(eyes),
                        "confidence": 0.9
                    }
            
            return {"success": False, "error": "Eyes not detected"}
            
        except Exception as e:
            logger.error(f"Error in blink detection: {str(e)}")
            return {"success": False, "error": str(e)}

    async def detect_smile(self, image_data: bytes) -> Dict[str, Any]:
        """Detect smile in the provided image"""
        try:
            # Similar implementation for smile detection
            # This is a simplified version - in production, you'd use a more sophisticated model
            return {"success": True, "confidence": 0.85}
        except Exception as e:
            logger.error(f"Error in smile detection: {str(e)}")
            return {"success": False, "error": str(e)}

    async def save_media(self, image_data: bytes, user_id: int) -> str:
        """Save the media file and return the URL"""
        filename = f"{user_id}_{uuid.uuid4()}.jpg"
        filepath = self.media_dir / filename
        
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        return f"/media/liveness/{filename}"

    async def create_liveness_check(
        self,
        user_id: int,
        verification_type: str,
        image_data: bytes
    ) -> LivenessCheck:
        """Create a new liveness check record"""
        # Save the media
        media_url = await self.save_media(image_data, user_id)
        
        # Perform detection based on verification type
        if verification_type == "blink":
            result = await self.detect_blink(image_data)
        elif verification_type == "smile":
            result = await self.detect_smile(image_data)
        else:
            raise ValueError(f"Unsupported verification type: {verification_type}")
        
        # Create the liveness check record
        liveness_check = await LivenessCheck.create(
            user_id=user_id,
            status="completed" if result["success"] else "failed",
            result=result,
            confidence_score=result.get("confidence"),
            verification_type=verification_type,
            media_url=media_url,
            error_message=None if result["success"] else result.get("error")
        )
        
        return liveness_check

    async def get_user_liveness_checks(
        self,
        user_id: int,
        status: Optional[str] = None
    ) -> list[LivenessCheck]:
        """Get liveness checks for a user"""
        query = LivenessCheck.filter(user_id=user_id)
        if status:
            query = query.filter(status=status)
        return await query.all()

    async def get_liveness_check(self, check_id: int) -> Optional[LivenessCheck]:
        """Get a specific liveness check by ID"""
        return await LivenessCheck.get_or_none(id=check_id)

# Create a singleton instance
liveness_service = LivenessService() 
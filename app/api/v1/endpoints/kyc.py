from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime
from ...models.kyc import KYCDocument, KYCVerification, KYCAuditLog, DocumentType, KYCStatus
from ...models.user import User
from ...services.kyc import kyc_service
from ...core.security import get_current_user, get_current_admin
from pydantic import BaseModel
from starlette.responses import FileResponse

router = APIRouter()

class KYCDocumentCreate(BaseModel):
    document_type: DocumentType
    document_number: str
    issue_date: datetime
    expiry_date: datetime
    country: str

class KYCVerificationCreate(BaseModel):
    verification_type: str
    verification_data: dict

class KYCDocumentResponse(BaseModel):
    id: int
    document_type: DocumentType
    document_number: str
    document_front_url: str
    document_back_url: Optional[str]
    issue_date: datetime
    expiry_date: datetime
    country: str
    status: KYCStatus
    rejection_reason: Optional[str]
    verified_at: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True

@router.post("/documents", response_model=KYCDocumentResponse)
async def upload_document(
    front_image: UploadFile = File(...),
    back_image: Optional[UploadFile] = File(None),
    document_data: KYCDocumentCreate = Form(...),
    current_user: User = Depends(get_current_user)
):
    try:
        # Read image files
        front_image_bytes = await front_image.read()
        back_image_bytes = await back_image.read() if back_image else None

        document = await kyc_service.upload_document(
            user=current_user,
            document_type=document_data.document_type,
            document_number=document_data.document_number,
            front_image=front_image_bytes,
            back_image=back_image_bytes,
            issue_date=document_data.issue_date,
            expiry_date=document_data.expiry_date,
            country=document_data.country
        )

        return document
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/documents", response_model=List[KYCDocumentResponse])
async def get_user_documents(current_user: User = Depends(get_current_user)):
    documents = await kyc_service.get_user_documents(current_user)
    return documents

@router.get("/documents/{document_id}", response_model=KYCDocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user)
):
    document = await KYCDocument.get_or_none(id=document_id, user=current_user)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.get("/documents/{document_id}/image/{side}")
async def get_document_image(
    document_id: int,
    side: str,
    current_user: User = Depends(get_current_user)
):
    document = await KYCDocument.get_or_none(id=document_id, user=current_user)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    image_path = document.document_front_url if side == "front" else document.document_back_url
    if not image_path:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(image_path)

@router.post("/documents/{document_id}/verify")
async def verify_document(
    document_id: int,
    status: KYCStatus,
    rejection_reason: Optional[str] = None,
    current_admin: User = Depends(get_current_admin)
):
    document = await KYCDocument.get_or_none(id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    document = await kyc_service.verify_document(
        document=document,
        verified_by=current_admin,
        status=status,
        rejection_reason=rejection_reason
    )
    
    return {"status": "success", "message": "Document verified successfully"}

@router.post("/verifications", response_model=KYCVerification)
async def create_verification(
    verification_data: KYCVerificationCreate,
    current_user: User = Depends(get_current_user)
):
    # Get the latest document for the user
    document = await KYCDocument.filter(
        user=current_user,
        status=KYCStatus.PENDING
    ).order_by("-created_at").first()
    
    if not document:
        raise HTTPException(status_code=404, detail="No pending document found")
    
    verification = await kyc_service.perform_verification(
        user=current_user,
        document=document,
        verification_type=verification_data.verification_type,
        verification_data=verification_data.verification_data
    )
    
    return verification

@router.get("/verifications", response_model=List[KYCVerification])
async def get_user_verifications(current_user: User = Depends(get_current_user)):
    verifications = await kyc_service.get_user_verifications(current_user)
    return verifications

@router.get("/status")
async def get_kyc_status(current_user: User = Depends(get_current_user)):
    status = await kyc_service.check_kyc_status(current_user)
    return status

@router.get("/audit-logs")
async def get_audit_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user)
):
    logs = await kyc_service.get_audit_logs(
        user=current_user,
        start_date=start_date,
        end_date=end_date
    )
    return logs 
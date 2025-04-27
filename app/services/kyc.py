from typing import List, Optional, Dict
from datetime import datetime, timedelta
from ..models.kyc import (
    KYCDocument, KYCVerification, KYCAuditLog,
    KYCStatus, DocumentType
)
from ..models.user import User
from .cache import cache_service
import json
import logging
from pathlib import Path
import aiofiles
import os

logger = logging.getLogger(__name__)

class KYCService:
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes
        self.upload_dir = Path("uploads/kyc")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload_document(
        self,
        user: User,
        document_type: DocumentType,
        document_number: str,
        front_image: bytes,
        back_image: Optional[bytes] = None,
        issue_date: datetime,
        expiry_date: datetime,
        country: str
    ) -> KYCDocument:
        # Generate unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        front_filename = f"{user.id}_{document_type}_{timestamp}_front.jpg"
        back_filename = f"{user.id}_{document_type}_{timestamp}_back.jpg" if back_image else None

        # Save front image
        front_path = self.upload_dir / front_filename
        async with aiofiles.open(front_path, 'wb') as f:
            await f.write(front_image)

        # Save back image if provided
        back_path = None
        if back_image and back_filename:
            back_path = self.upload_dir / back_filename
            async with aiofiles.open(back_path, 'wb') as f:
                await f.write(back_image)

        # Create document record
        document = await KYCDocument.create(
            user=user,
            document_type=document_type,
            document_number=document_number,
            document_front_url=str(front_path),
            document_back_url=str(back_path) if back_path else None,
            issue_date=issue_date,
            expiry_date=expiry_date,
            country=country
        )

        # Create audit log
        await KYCAuditLog.create(
            user=user,
            document=document,
            action="document_upload",
            status=KYCStatus.PENDING,
            details={
                "document_type": document_type,
                "document_number": document_number,
                "country": country
            }
        )

        return document

    async def verify_document(
        self,
        document: KYCDocument,
        verified_by: User,
        status: KYCStatus,
        rejection_reason: Optional[str] = None
    ) -> KYCDocument:
        document.status = status
        document.verified_by = verified_by
        document.verified_at = datetime.now()
        document.rejection_reason = rejection_reason
        await document.save()

        # Create audit log
        await KYCAuditLog.create(
            user=document.user,
            document=document,
            action="document_verification",
            status=status,
            performed_by=verified_by,
            details={
                "rejection_reason": rejection_reason
            }
        )

        return document

    async def perform_verification(
        self,
        user: User,
        document: KYCDocument,
        verification_type: str,
        verification_data: Dict
    ) -> KYCVerification:
        verification = await KYCVerification.create(
            user=user,
            document=document,
            verification_type=verification_type,
            verification_result=verification_data
        )

        # Create audit log
        await KYCAuditLog.create(
            user=user,
            verification=verification,
            action=f"{verification_type}_verification",
            status=KYCStatus.PENDING,
            details=verification_data
        )

        return verification

    async def get_user_documents(self, user: User) -> List[KYCDocument]:
        cache_key = f"kyc_documents:{user.id}"
        cached_documents = await cache_service.get(cache_key)
        
        if cached_documents:
            return [KYCDocument.from_dict(doc) for doc in json.loads(cached_documents)]
        
        documents = await KYCDocument.filter(user=user)
        await cache_service.set(cache_key, json.dumps([doc.to_dict() for doc in documents]), expire=self.cache_ttl)
        return documents

    async def get_document_verifications(self, document: KYCDocument) -> List[KYCVerification]:
        return await KYCVerification.filter(document=document)

    async def get_user_verifications(self, user: User) -> List[KYCVerification]:
        return await KYCVerification.filter(user=user)

    async def get_audit_logs(
        self,
        user: User,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[KYCAuditLog]:
        query = KYCAuditLog.filter(user=user)
        
        if start_date:
            query = query.filter(created_at__gte=start_date)
        if end_date:
            query = query.filter(created_at__lte=end_date)
        
        return await query.order_by("-created_at")

    async def check_kyc_status(self, user: User) -> Dict:
        documents = await self.get_user_documents(user)
        verifications = await self.get_user_verifications(user)
        
        # Check if any document is approved
        has_approved_document = any(doc.status == KYCStatus.APPROVED for doc in documents)
        
        # Check if any document is expired
        has_expired_document = any(
            doc.status == KYCStatus.APPROVED and doc.expiry_date < datetime.now().date()
            for doc in documents
        )
        
        return {
            "has_approved_document": has_approved_document,
            "has_expired_document": has_expired_document,
            "document_count": len(documents),
            "verification_count": len(verifications),
            "documents": [doc.to_dict() for doc in documents],
            "verifications": [ver.to_dict() for ver in verifications]
        }

    async def cleanup_expired_documents(self):
        """Clean up expired documents and update their status"""
        expired_documents = await KYCDocument.filter(
            status=KYCStatus.APPROVED,
            expiry_date__lt=datetime.now().date()
        )
        
        for doc in expired_documents:
            doc.status = KYCStatus.EXPIRED
            await doc.save()
            
            await KYCAuditLog.create(
                user=doc.user,
                document=doc,
                action="document_expiry",
                status=KYCStatus.EXPIRED,
                details={
                    "expiry_date": doc.expiry_date.isoformat()
                }
            )

kyc_service = KYCService() 
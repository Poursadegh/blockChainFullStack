from tortoise import fields
from tortoise.models import Model
from enum import Enum
from typing import Optional
from datetime import datetime

class KYCStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class DocumentType(str, Enum):
    PASSPORT = "passport"
    NATIONAL_ID = "national_id"
    DRIVERS_LICENSE = "drivers_license"
    RESIDENCE_PERMIT = "residence_permit"

class KYCDocument(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='kyc_documents')
    document_type = fields.CharEnumField(DocumentType)
    document_number = fields.CharField(max_length=100)
    document_front_url = fields.CharField(max_length=255)
    document_back_url = fields.CharField(max_length=255, null=True)
    issue_date = fields.DateField()
    expiry_date = fields.DateField()
    country = fields.CharField(max_length=100)
    status = fields.CharEnumField(KYCStatus, default=KYCStatus.PENDING)
    rejection_reason = fields.TextField(null=True)
    verified_by = fields.ForeignKeyField('models.User', related_name='verified_documents', null=True)
    verified_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "kyc_documents"
        indexes = [("user_id", "document_type")]

class KYCVerification(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='kyc_verifications')
    document = fields.ForeignKeyField('models.KYCDocument', related_name='verifications')
    status = fields.CharEnumField(KYCStatus, default=KYCStatus.PENDING)
    verification_type = fields.CharField(max_length=50)  # face_match, liveness, etc.
    verification_result = fields.JSONField()  # Store detailed verification results
    verified_by = fields.ForeignKeyField('models.User', related_name='performed_verifications', null=True)
    verified_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "kyc_verifications"
        indexes = [("user_id", "status")]

class KYCAuditLog(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='kyc_audit_logs')
    document = fields.ForeignKeyField('models.KYCDocument', related_name='audit_logs', null=True)
    verification = fields.ForeignKeyField('models.KYCVerification', related_name='audit_logs', null=True)
    action = fields.CharField(max_length=100)  # document_upload, verification_start, etc.
    status = fields.CharEnumField(KYCStatus)
    details = fields.JSONField()  # Store additional audit information
    performed_by = fields.ForeignKeyField('models.User', related_name='performed_audit_logs', null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "kyc_audit_logs"
        indexes = [("user_id", "created_at")] 
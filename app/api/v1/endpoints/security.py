from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel
from ...models.security import UserRole, UserPermission, TwoFactorAuth, SecuritySettings
from ...services.security import security_service
from ...core.security import get_current_user
from ...models.user import User

router = APIRouter()

class RoleCreate(BaseModel):
    name: str
    description: str
    permissions: List[str]

class RoleResponse(BaseModel):
    id: int
    name: str
    description: str
    permissions: List[str]

class TwoFactorSetup(BaseModel):
    method: str  # app, sms, email
    contact: str  # phone number or email

class TwoFactorVerify(BaseModel):
    code: str

class SecuritySettingsUpdate(BaseModel):
    max_login_attempts: Optional[int] = None
    lockout_duration: Optional[int] = None
    session_timeout: Optional[int] = None
    require_2fa: Optional[bool] = None
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None

@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_user)
):
    if not await security_service.check_permission(current_user, "create_role"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    role = await security_service.create_role(
        name=role_data.name,
        description=role_data.description,
        permissions=role_data.permissions
    )
    return role

@router.post("/roles/{role_id}/assign/{user_id}")
async def assign_role(
    role_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    if not await security_service.check_permission(current_user, "assign_role"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    role = await UserRole.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await security_service.assign_role(user, role, current_user)
    return {"message": "Role assigned successfully"}

@router.post("/2fa/setup")
async def setup_2fa(
    setup_data: TwoFactorSetup,
    current_user: User = Depends(get_current_user)
):
    result = await security_service.setup_2fa(
        user=current_user,
        method=setup_data.method,
        contact=setup_data.contact
    )
    return result

@router.post("/2fa/verify")
async def verify_2fa(
    verify_data: TwoFactorVerify,
    current_user: User = Depends(get_current_user)
):
    is_valid = await security_service.verify_2fa(
        user=current_user,
        code=verify_data.code
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    return {"message": "2FA verification successful"}

@router.get("/settings", response_model=SecuritySettings)
async def get_security_settings(
    current_user: User = Depends(get_current_user)
):
    return await security_service.get_security_settings(current_user)

@router.put("/settings")
async def update_security_settings(
    settings_data: SecuritySettingsUpdate,
    current_user: User = Depends(get_current_user)
):
    settings = await security_service.update_security_settings(
        user=current_user,
        max_login_attempts=settings_data.max_login_attempts,
        lockout_duration=settings_data.lockout_duration,
        session_timeout=settings_data.session_timeout,
        require_2fa=settings_data.require_2fa,
        email_notifications=settings_data.email_notifications,
        sms_notifications=settings_data.sms_notifications
    )
    return settings

@router.post("/encrypt")
async def encrypt_data(
    data_type: str,
    data: str,
    current_user: User = Depends(get_current_user)
):
    encrypted = await security_service.encrypt_data(
        user=current_user,
        data_type=data_type,
        data=data
    )
    return {"id": encrypted.id}

@router.get("/decrypt/{encrypted_id}")
async def decrypt_data(
    encrypted_id: int,
    current_user: User = Depends(get_current_user)
):
    encrypted = await EncryptedData.get_or_none(id=encrypted_id, user=current_user)
    if not encrypted:
        raise HTTPException(status_code=404, detail="Encrypted data not found")
    
    decrypted = await security_service.decrypt_data(encrypted)
    return {"data": decrypted}

@router.get("/logs")
async def get_security_logs(
    event_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    if not await security_service.check_permission(current_user, "view_security_logs"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    query = SecurityLog.filter(user=current_user)
    if event_type:
        query = query.filter(event_type=event_type)
    
    logs = await query.order_by("-created_at").limit(limit)
    return logs 
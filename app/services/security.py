from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pyotp
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from ..models.security import (
    UserRole, UserPermission, TwoFactorAuth,
    SecurityLog, EncryptedData, SecuritySettings
)
from ..models.user import User
from .cache import cache_service
import json
import logging

logger = logging.getLogger(__name__)

class SecurityService:
    def __init__(self):
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.salt = os.urandom(16)

    def _generate_key(self, password: str) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    async def create_role(self, name: str, description: str, permissions: List[str]) -> UserRole:
        return await UserRole.create(
            name=name,
            description=description,
            permissions=permissions
        )

    async def assign_role(self, user: User, role: UserRole, granted_by: User) -> UserPermission:
        return await UserPermission.create(
            user=user,
            role=role,
            granted_by=granted_by
        )

    async def check_permission(self, user: User, permission: str) -> bool:
        cache_key = f"user_permissions:{user.id}"
        cached_permissions = await cache_service.get(cache_key)
        
        if cached_permissions:
            permissions = json.loads(cached_permissions)
        else:
            user_permissions = await UserPermission.filter(
                user=user,
                expires_at__gt=datetime.now()
            ).prefetch_related('role')
            
            permissions = []
            for up in user_permissions:
                permissions.extend(up.role.permissions)
            
            await cache_service.set(cache_key, json.dumps(permissions), expire=300)
        
        return permission in permissions

    async def setup_2fa(self, user: User, method: str, contact: str) -> Dict:
        secret = pyotp.random_base32()
        two_factor = await TwoFactorAuth.create(
            user=user,
            secret_key=secret,
            method=method,
            phone_number=contact if method == "sms" else None,
            email=contact if method == "email" else None
        )
        
        qr_code = two_factor.generate_qr_code()
        return {
            "secret": secret,
            "qr_code": qr_code,
            "method": method
        }

    async def verify_2fa(self, user: User, code: str) -> bool:
        two_factor = await TwoFactorAuth.get_or_none(user=user, is_enabled=True)
        if not two_factor:
            return False
        
        is_valid = two_factor.verify_code(code)
        if is_valid:
            two_factor.last_used = datetime.now()
            await two_factor.save()
        
        await self.log_security_event(
            user=user,
            event_type="2fa_verification",
            status="success" if is_valid else "failed"
        )
        
        return is_valid

    async def log_security_event(
        self,
        user: User,
        event_type: str,
        status: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        await SecurityLog.create(
            user=user,
            event_type=event_type,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )

    async def encrypt_data(self, user: User, data_type: str, data: str) -> EncryptedData:
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return await EncryptedData.create(
            user=user,
            data_type=data_type,
            encrypted_data=encrypted_data.decode(),
            iv=base64.b64encode(os.urandom(16)).decode()
        )

    async def decrypt_data(self, encrypted_data: EncryptedData) -> str:
        try:
            decrypted_data = self.cipher_suite.decrypt(encrypted_data.encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            raise

    async def get_security_settings(self, user: User) -> SecuritySettings:
        settings = await SecuritySettings.get_or_none(user=user)
        if not settings:
            settings = await SecuritySettings.create(user=user)
        return settings

    async def update_security_settings(
        self,
        user: User,
        max_login_attempts: Optional[int] = None,
        lockout_duration: Optional[int] = None,
        session_timeout: Optional[int] = None,
        require_2fa: Optional[bool] = None,
        email_notifications: Optional[bool] = None,
        sms_notifications: Optional[bool] = None
    ) -> SecuritySettings:
        settings = await self.get_security_settings(user)
        
        if max_login_attempts is not None:
            settings.max_login_attempts = max_login_attempts
        if lockout_duration is not None:
            settings.lockout_duration = lockout_duration
        if session_timeout is not None:
            settings.session_timeout = session_timeout
        if require_2fa is not None:
            settings.require_2fa = require_2fa
        if email_notifications is not None:
            settings.email_notifications = email_notifications
        if sms_notifications is not None:
            settings.sms_notifications = sms_notifications
        
        await settings.save()
        return settings

    async def check_login_attempts(self, user: User) -> bool:
        settings = await self.get_security_settings(user)
        recent_failed_attempts = await SecurityLog.filter(
            user=user,
            event_type="login",
            status="failed",
            created_at__gte=datetime.now() - timedelta(minutes=settings.lockout_duration)
        ).count()
        
        return recent_failed_attempts < settings.max_login_attempts

security_service = SecurityService() 
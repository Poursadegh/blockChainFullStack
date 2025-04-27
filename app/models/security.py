from tortoise import fields
from tortoise.models import Model
from datetime import datetime, timedelta
import pyotp
import qrcode
import base64
from io import BytesIO

class UserRole(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=50, unique=True)
    description = fields.TextField()
    permissions = fields.JSONField()  # List of permission codes
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_roles"

class UserPermission(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='permissions')
    role = fields.ForeignKeyField('models.UserRole', related_name='users')
    granted_at = fields.DatetimeField(auto_now_add=True)
    granted_by = fields.ForeignKeyField('models.User', related_name='granted_permissions')
    expires_at = fields.DatetimeField(null=True)

    class Meta:
        table = "user_permissions"
        indexes = [("user_id", "role_id")]

class TwoFactorAuth(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='two_factor_auth')
    secret_key = fields.CharField(max_length=32)  # Base32 encoded secret
    method = fields.CharField(max_length=20)  # app, sms, email
    phone_number = fields.CharField(max_length=20, null=True)
    email = fields.CharField(max_length=255, null=True)
    is_enabled = fields.BooleanField(default=False)
    last_used = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "two_factor_auth"

    def generate_qr_code(self):
        totp = pyotp.TOTP(self.secret_key)
        provisioning_uri = totp.provisioning_uri(
            name=self.user.email,
            issuer_name="CryptoExchange"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def verify_code(self, code: str) -> bool:
        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(code)

class SecurityLog(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='security_logs')
    event_type = fields.CharField(max_length=50)  # login, logout, 2fa, password_change, etc.
    ip_address = fields.CharField(max_length=45)
    user_agent = fields.TextField()
    status = fields.CharField(max_length=20)  # success, failed
    details = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "security_logs"
        indexes = [("user_id", "event_type", "created_at")]

class EncryptedData(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='encrypted_data')
    data_type = fields.CharField(max_length=50)  # private_key, api_key, etc.
    encrypted_data = fields.TextField()
    iv = fields.CharField(max_length=32)  # Initialization vector
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "encrypted_data"
        indexes = [("user_id", "data_type")]

class SecuritySettings(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='security_settings')
    max_login_attempts = fields.IntField(default=5)
    lockout_duration = fields.IntField(default=15)  # minutes
    session_timeout = fields.IntField(default=30)  # minutes
    require_2fa = fields.BooleanField(default=False)
    email_notifications = fields.BooleanField(default=True)
    sms_notifications = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "security_settings" 
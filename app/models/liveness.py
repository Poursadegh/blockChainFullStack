from tortoise import fields
from tortoise.models import Model
from datetime import datetime

class LivenessCheck(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='liveness_checks')
    status = fields.CharField(max_length=20)  # pending, completed, failed
    result = fields.JSONField(null=True)  # Store detection results
    confidence_score = fields.FloatField(null=True)
    timestamp = fields.DatetimeField(auto_now_add=True)
    attempts = fields.IntField(default=0)
    max_attempts = fields.IntField(default=3)
    verification_type = fields.CharField(max_length=50)  # blink, smile, head_movement, etc.
    media_url = fields.CharField(max_length=255, null=True)  # URL to stored media
    error_message = fields.TextField(null=True)

    class Meta:
        table = "liveness_checks"
        indexes = [("user_id", "status")]

    def __str__(self):
        return f"LivenessCheck {self.id} for User {self.user_id}" 
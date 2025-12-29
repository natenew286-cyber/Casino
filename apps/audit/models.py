from django.db import models
from django.conf import settings
import uuid


class AuditLog(models.Model):
    """
    Model for storing audit logs of user actions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=50, null=True, blank=True)
    resource_id = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    request_data = models.JSONField(null=True, blank=True)
    response_status = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} - {self.user or 'Anonymous'} - {self.created_at}"

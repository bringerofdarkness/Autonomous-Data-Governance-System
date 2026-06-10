import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.name


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        user = self.create_user(email, password, **extra_fields)
        # We will associate the user with the "Admin" role if it exists
        admin_role, _ = Role.objects.get_or_create(name="Admin")
        user.roles.add(admin_role)
        return user


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    
    # Map Django's standard password field to the existing hashed_password column in database
    password = models.CharField(max_length=255, db_column="hashed_password")
    
    full_name = models.CharField(max_length=150, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    roles = models.ManyToManyField(Role, db_table="user_roles", related_name="users")

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    last_login = None  # We disable last_login to match FastAPI schema where last_login column is absent

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    @property
    def is_staff(self):
        # Anyone with 'Admin' role is staff
        try:
            return self.roles.filter(name="Admin").exists()
        except Exception:
            return False

    @property
    def is_superuser(self):
        try:
            return self.roles.filter(name="Admin").exists()
        except Exception:
            return False

    def check_password(self, raw_password):
        from app.core.security import verify_password
        return verify_password(raw_password, self.password)

    def set_password(self, raw_password):
        from app.core.security import hash_password
        self.password = hash_password(raw_password)

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser



class DocumentStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "Uploaded"
    PROCESSING = "PROCESSING", "Processing"
    PAUSED = "PAUSED", "Paused"
    WAITING_FOR_ADMIN = "WAITING_FOR_ADMIN", "Waiting for Admin"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    FAILED = "FAILED", "Failed"


class DocumentMetadata(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_filename = models.CharField(max_length=255)
    stored_filename = models.CharField(max_length=255)
    cleaned_text_filename = models.CharField(max_length=255, null=True, blank=True)
    qdrant_point_id = models.UUIDField(null=True, blank=True, db_index=True)
    indexed_at = models.DateTimeField(null=True, blank=True)
    content_type = models.CharField(max_length=100, null=True, blank=True)
    file_size_bytes = models.IntegerField()
    status = models.CharField(
        max_length=50,
        choices=DocumentStatus.choices,
        default=DocumentStatus.UPLOADED,
        db_index=True,
    )
    celery_task_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    document_category = models.CharField(max_length=100, null=True, blank=True)
    risk_score = models.IntegerField(null=True, blank=True)
    conflict_found = models.BooleanField(default=False, db_index=True)
    conflict_summary = models.TextField(null=True, blank=True)
    conflict_checked_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="uploaded_by_id",
        related_name="uploaded_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "document_metadata"

    def __str__(self):
        return self.original_filename


class DocumentAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        DocumentMetadata,
        on_delete=models.CASCADE,
        db_column="document_id",
        related_name="audit_logs",
    )
    actor_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="actor_user_id",
        related_name="actor_document_logs",
    )
    action = models.CharField(max_length=100, db_index=True)
    message = models.TextField(null=True, blank=True)
    extra_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "document_audit_logs"

    def __str__(self):
        return f"{self.action} on {self.document.original_filename}"


class RagSearchAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="actor_user_id",
        related_name="actor_rag_search_logs",
    )
    query = models.TextField()
    result_limit = models.IntegerField()
    min_score = models.FloatField()
    matches_count = models.IntegerField()
    matched_document_ids = models.JSONField(default=list)
    matched_point_ids = models.JSONField(default=list)
    extra_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rag_search_audit_logs"

    def __str__(self):
        return f"Search by {self.actor_user.email if self.actor_user else 'Anonymous'} - {self.query[:30]}"

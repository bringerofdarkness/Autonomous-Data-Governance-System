from rest_framework import serializers
from app.models import User, Role, DocumentMetadata, DocumentAuditLog, RagSearchAuditLog


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "description"]


class CurrentUserSerializer(serializers.ModelSerializer):
    roles = RoleSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "is_active", "roles", "created_at"]


class TokenSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField(default="bearer")


class DocumentUploadSerializer(serializers.ModelSerializer):
    uploaded_by_id = serializers.UUIDField(source="uploaded_by.id", read_only=True)

    class Meta:
        model = DocumentMetadata
        fields = [
            "id",
            "original_filename",
            "stored_filename",
            "content_type",
            "file_size_bytes",
            "status",
            "celery_task_id",
            "uploaded_by_id",
            "created_at",
        ]


class DocumentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentMetadata
        fields = [
            "id",
            "original_filename",
            "status",
            "document_category",
            "risk_score",
            "conflict_found",
            "conflict_summary",
            "conflict_checked_at",
            "celery_task_id",
            "error_message",
            "created_at",
            "updated_at",
        ]


class DocumentTaskStatusSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    original_filename = serializers.CharField()
    database_status = serializers.CharField()
    document_category = serializers.CharField(allow_null=True)
    risk_score = serializers.IntegerField(allow_null=True)
    celery_task_id = serializers.CharField(allow_null=True)
    celery_state = serializers.CharField(allow_null=True)
    celery_result = serializers.JSONField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)


class DocumentDecisionRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5, max_length=500)


class DocumentDecisionSerializer(serializers.ModelSerializer):
    decision_message = serializers.CharField()

    class Meta:
        model = DocumentMetadata
        fields = [
            "id",
            "original_filename",
            "status",
            "document_category",
            "risk_score",
            "decision_message",
        ]


class DocumentListItemSerializer(serializers.ModelSerializer):
    uploaded_by_id = serializers.UUIDField(source="uploaded_by.id", read_only=True)

    class Meta:
        model = DocumentMetadata
        fields = [
            "id",
            "original_filename",
            "stored_filename",
            "cleaned_text_filename",
            "content_type",
            "file_size_bytes",
            "status",
            "document_category",
            "risk_score",
            "conflict_found",
            "conflict_summary",
            "conflict_checked_at",
            "qdrant_point_id",
            "indexed_at",
            "celery_task_id",
            "uploaded_by_id",
            "created_at",
            "updated_at",
        ]


class DocumentSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    uploaded = serializers.IntegerField()
    processing = serializers.IntegerField()
    waiting_for_admin = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    failed = serializers.IntegerField()
    conflict_found_count = serializers.IntegerField()
    indexed_count = serializers.IntegerField()
    waiting_for_admin_with_conflict = serializers.IntegerField()


class DocumentReprocessSerializer(serializers.ModelSerializer):
    message = serializers.CharField()

    class Meta:
        model = DocumentMetadata
        fields = ["id", "original_filename", "status", "celery_task_id", "message"]


class DocumentIndexSerializer(serializers.ModelSerializer):
    chunks_indexed = serializers.IntegerField()
    points_indexed = serializers.IntegerField()
    message = serializers.CharField()

    class Meta:
        model = DocumentMetadata
        fields = [
            "id",
            "original_filename",
            "status",
            "document_category",
            "risk_score",
            "qdrant_point_id",
            "indexed_at",
            "chunks_indexed",
            "points_indexed",
            "message",
        ]


class DocumentQdrantPointSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    original_filename = serializers.CharField()
    indexed = serializers.BooleanField()
    qdrant_point_id = serializers.UUIDField(allow_null=True)
    collection_name = serializers.CharField(allow_null=True)
    payload = serializers.JSONField(allow_null=True)
    message = serializers.CharField()


class ConflictMatchSerializer(serializers.Serializer):
    point_id = serializers.CharField()
    score = serializers.FloatField()
    payload = serializers.JSONField(allow_null=True)


class DocumentConflictCheckSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    original_filename = serializers.CharField()
    conflict_found = serializers.BooleanField()
    similarity_threshold = serializers.FloatField()
    matches_checked = serializers.IntegerField()
    potential_conflicts = ConflictMatchSerializer(many=True)
    message = serializers.CharField()


class DocumentResumeRequestSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(min_length=10, max_length=1000)


class DocumentResumeSerializer(serializers.ModelSerializer):
    hitl_decision = serializers.CharField()
    hitl_reason = serializers.CharField()
    message = serializers.CharField()

    class Meta:
        model = DocumentMetadata
        fields = [
            "id",
            "original_filename",
            "status",
            "hitl_decision",
            "hitl_reason",
            "message",
        ]


class QdrantChunkSerializer(serializers.Serializer):
    point_id = serializers.CharField()
    chunk_index = serializers.IntegerField(allow_null=True)
    chunk_text = serializers.CharField(allow_null=True)
    char_count = serializers.IntegerField(allow_null=True)
    payload = serializers.JSONField(allow_null=True)


class DocumentQdrantChunksSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    original_filename = serializers.CharField()
    indexed = serializers.BooleanField()
    chunks_count = serializers.IntegerField()
    chunks = QdrantChunkSerializer(many=True)
    message = serializers.CharField()


class DocumentAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentAuditLog
        fields = [
            "id",
            "document_id",
            "actor_user_id",
            "action",
            "message",
            "extra_data",
            "created_at",
        ]


class RagSearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=3, max_length=1000)
    limit = serializers.IntegerField(default=5, min_value=1, max_value=20)
    min_score = serializers.FloatField(default=0.30, min_value=0.0, max_value=1.0)


class RagChunkMatchSerializer(serializers.Serializer):
    point_id = serializers.CharField()
    score = serializers.FloatField()
    document_id = serializers.CharField(allow_null=True)
    original_filename = serializers.CharField(allow_null=True)
    document_category = serializers.CharField(allow_null=True)
    risk_score = serializers.IntegerField(allow_null=True)
    chunk_index = serializers.IntegerField(allow_null=True)
    chunk_text = serializers.CharField(allow_null=True)
    source = serializers.CharField(allow_null=True)


class RagSearchSerializer(serializers.Serializer):
    query = serializers.CharField()
    min_score = serializers.FloatField()
    matches_count = serializers.IntegerField()
    matches = RagChunkMatchSerializer(many=True)
    synthesized_answer = serializers.CharField()


class RagSearchAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RagSearchAuditLog
        fields = [
            "id",
            "actor_user_id",
            "query",
            "result_limit",
            "min_score",
            "matches_count",
            "matched_document_ids",
            "matched_point_ids",
            "extra_data",
            "created_at",
        ]

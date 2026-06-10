from django.contrib import admin
from django.utils.html import format_html
from app.models import User, Role, DocumentMetadata, DocumentAuditLog, RagSearchAuditLog
from app.tasks import process_document_task
from app.services.audit_service import create_document_audit_log
from app.services.document_indexing_service import index_cleaned_document_in_qdrant
from app.services.conflict_service import check_document_conflicts
from app.services.qdrant_service import get_gold_collection_point, get_gold_collection_chunks_for_document
from django.utils import timezone


class DocumentAuditLogInline(admin.TabularInline):
    model = DocumentAuditLog
    extra = 0
    readonly_fields = ["action", "message", "actor_user", "extra_data", "created_at"]
    can_delete = False
    ordering = ["-created_at"]


@admin.register(DocumentMetadata)
class DocumentMetadataAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename",
        "status_badge",
        "document_category",
        "risk_score_badge",
        "conflict_found_badge",
        "uploaded_by",
        "created_at",
        "indexed_at",
    ]
    list_filter = ["status", "conflict_found", "document_category", "created_at"]
    search_fields = ["original_filename", "celery_task_id", "document_category"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [DocumentAuditLogInline]
    actions = ["reprocess_documents", "index_documents", "run_conflict_check", "repair_vector_integrity"]

    def status_badge(self, obj):
        colors = {
            "UPLOADED": "#17a2b8",
            "PROCESSING": "#ffc107",
            "PAUSED": "#6c757d",
            "WAITING_FOR_ADMIN": "#fd7e14",
            "APPROVED": "#28a745",
            "REJECTED": "#dc3545",
            "FAILED": "#343a40",
        }
        color = colors.get(obj.status, "#000")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold;">{}</span>',
            color,
            obj.status,
        )
    status_badge.short_description = "Status"

    def risk_score_badge(self, obj):
        if obj.risk_score is None:
            return "-"
        color = "#28a745" if obj.risk_score < 35 else "#ffc107" if obj.risk_score < 75 else "#dc3545"
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 14px;">{}</span>',
            color,
            obj.risk_score,
        )
    risk_score_badge.short_description = "Risk Score"

    def conflict_found_badge(self, obj):
        if obj.conflict_found:
            return format_html('<span style="color: #dc3545; font-weight: bold;">⚠️ Yes</span>')
        return format_html('<span style="color: #28a745; font-weight: bold;">✅ No</span>')
    conflict_found_badge.short_description = "Conflict?"

    # Custom Admin Actions
    def reprocess_documents(self, request, queryset):
        count = 0
        for doc in queryset:
            if doc.status in ["UPLOADED", "FAILED", "WAITING_FOR_ADMIN"]:
                task = process_document_task.delay(str(doc.id))
                doc.status = "UPLOADED"
                doc.celery_task_id = task.id
                doc.error_message = None
                doc.conflict_found = False
                doc.conflict_summary = None
                doc.conflict_checked_at = None
                doc.save()

                create_document_audit_log(
                    document_id=doc.id,
                    actor_user_id=request.user.id,
                    action="DOCUMENT_REPROCESS_REQUESTED",
                    message=f"Reprocessing triggered from Django Admin by {request.user.email}.",
                    extra_data={"celery_task_id": task.id},
                )
                count += 1
        self.message_user(request, f"{count} documents successfully queued for reprocessing.")
    reprocess_documents.short_description = "Reprocess selected documents"

    def index_documents(self, request, queryset):
        indexed_count = 0
        failed_count = 0
        for doc in queryset:
            if doc.status != "APPROVED":
                failed_count += 1
                continue
            if not doc.cleaned_text_filename:
                failed_count += 1
                continue

            try:
                res = index_cleaned_document_in_qdrant(
                    document_id=doc.id,
                    original_filename=doc.original_filename,
                    cleaned_text_filename=doc.cleaned_text_filename,
                    document_category=doc.document_category,
                    risk_score=doc.risk_score,
                )
                doc.qdrant_point_id = res["qdrant_point_id"]
                doc.indexed_at = timezone.now()
                doc.save()

                create_document_audit_log(
                    document_id=doc.id,
                    actor_user_id=request.user.id,
                    action="DOCUMENT_INDEXED_IN_QDRANT",
                    message=f"Indexed in Qdrant from Django Admin by {request.user.email}.",
                    extra_data={
                        "chunks_indexed": res["chunks_indexed"],
                        "points_indexed": res["points_indexed"],
                    },
                )
                indexed_count += 1
            except Exception:
                failed_count += 1

        self.message_user(
            request,
            f"Successfully indexed {indexed_count} documents. ({failed_count} skipped/failed)",
        )
    index_documents.short_description = "Index approved documents to Qdrant"

    def run_conflict_check(self, request, queryset):
        count = 0
        for doc in queryset:
            if not doc.cleaned_text_filename:
                continue

            res = check_document_conflicts(
                document_id=doc.id,
                cleaned_text_filename=doc.cleaned_text_filename,
                similarity_threshold=0.75,
                limit=5,
            )
            doc.conflict_found = res["conflict_found"]
            if res["conflict_found"]:
                doc.conflict_summary = f"Conflict detected with Qdrant point: {res['potential_conflicts'][0]['point_id']}"
            else:
                doc.conflict_summary = "No potential conflict found in Qdrant Gold collection."
            doc.conflict_checked_at = timezone.now()
            doc.save()

            create_document_audit_log(
                document_id=doc.id,
                actor_user_id=request.user.id,
                action="DOCUMENT_CONFLICT_CHECKED",
                message=doc.conflict_summary,
                extra_data={"conflict_found": doc.conflict_found},
            )
            count += 1
        self.message_user(request, f"Conflict check completed for {count} documents.")
    run_conflict_check.short_description = "Run manual conflict check"

    def repair_vector_integrity(self, request, queryset):
        repaired = 0
        for doc in queryset:
            if not doc.qdrant_point_id:
                continue

            qdrant_point_res = get_gold_collection_point(point_id=str(doc.qdrant_point_id))
            qdrant_chunks = get_gold_collection_chunks_for_document(document_id=str(doc.id), limit=200)

            point_found = qdrant_point_res["found"]
            chunks_count = len(qdrant_chunks)

            is_broken = not point_found or chunks_count == 0

            if is_broken:
                old_qdrant_point_id = doc.qdrant_point_id
                old_indexed_at = doc.indexed_at

                doc.qdrant_point_id = None
                doc.indexed_at = None
                doc.save()

                create_document_audit_log(
                    document_id=doc.id,
                    actor_user_id=request.user.id,
                    action="DOCUMENT_QDRANT_INTEGRITY_REPAIRED",
                    message=f"PostgreSQL indexing fields cleared due to stale or missing Qdrant points.",
                    extra_data={
                        "old_qdrant_point_id": str(old_qdrant_point_id),
                        "old_indexed_at": old_indexed_at.isoformat() if old_indexed_at else None,
                    },
                )
                repaired += 1

        self.message_user(request, f"Repaired vector integrity fields for {repaired} documents.")
    repair_vector_integrity.short_description = "Repair vector database integrity"


@admin.register(DocumentAuditLog)
class DocumentAuditLogAdmin(admin.ModelAdmin):
    list_display = ["document", "action", "actor_user", "created_at", "short_message"]
    list_filter = ["action", "created_at"]
    search_fields = ["document__original_filename", "action", "message"]
    readonly_fields = ["document", "actor_user", "action", "message", "extra_data", "created_at"]

    def short_message(self, obj):
        return obj.message[:80] + "..." if obj.message and len(obj.message) > 80 else obj.message
    short_message.short_description = "Message"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RagSearchAuditLog)
class RagSearchAuditLogAdmin(admin.ModelAdmin):
    list_display = ["query_truncated", "actor_user", "matches_count", "min_score", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["query", "actor_user__email"]
    readonly_fields = [
        "actor_user",
        "query",
        "result_limit",
        "min_score",
        "matches_count",
        "matched_document_ids",
        "matched_point_ids",
        "extra_data",
        "created_at",
    ]

    def query_truncated(self, obj):
        return obj.query[:60] + "..." if len(obj.query) > 60 else obj.query
    query_truncated.short_description = "Search Query"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Standard User and Role Registrations
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at"]
    search_fields = ["name"]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "full_name", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["email", "full_name"]
    filter_horizontal = ["roles"]
    readonly_fields = ["created_at", "updated_at"]

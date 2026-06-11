import os
import uuid
from datetime import datetime, timedelta, timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Count, Q
from django.utils import timezone as django_timezone

from app.models import (
    User,
    Role,
    DocumentMetadata,
    DocumentStatus,
    DocumentAuditLog,
    RagSearchAuditLog,
)
from app.serializers import (
    CurrentUserSerializer,
    TokenSerializer,
    DocumentUploadSerializer,
    DocumentStatusSerializer,
    DocumentTaskStatusSerializer,
    DocumentDecisionSerializer,
    DocumentListItemSerializer,
    DocumentSummarySerializer,
    DocumentReprocessSerializer,
    DocumentIndexSerializer,
    DocumentQdrantPointSerializer,
    ConflictMatchSerializer,
    DocumentConflictCheckSerializer,
    DocumentResumeSerializer,
    QdrantChunkSerializer,
    DocumentQdrantChunksSerializer,
    DocumentAuditLogSerializer,
    RagSearchRequestSerializer,
    RagSearchSerializer,
    RagSearchAuditLogSerializer,
)
from app.permissions import RequireAdmin, RequireEditor, RequireViewer
from app.services.auth_service import authenticate_user, create_user_access_token
from app.services.document_service import save_uploaded_document
from app.services.audit_service import create_document_audit_log
from app.services.qdrant_service import (
    check_qdrant_health,
    ensure_gold_collection,
    get_gold_collection_point,
    get_gold_collection_chunks_for_document,
)
from app.services.document_indexing_service import index_cleaned_document_in_qdrant
from app.services.conflict_service import check_document_conflicts
from app.services.rag_search_service import search_approved_gold_chunks
from app.services.llm_service import LLMGenerationService
from app.services.rag_audit_service import create_rag_search_audit_log

# Celery import
from django_project.celery import app as celery_app
from app.tasks import process_document_task

# LangGraph imports
from app.graph.workflow import build_adgs_graph
from langgraph.types import Command


# Deterministic synthesis engine
llm_service = LLMGenerationService()


def make_json_safe(value):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]
    return str(value)


class HealthCheckView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        return Response({"status": "healthy", "service": "ADGS API"})


class LoginView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        email = request.data.get("username") or request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "Username/email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate_user(email=email.strip(), password=password)
        access_token = create_user_access_token(user)

        serializer = TokenSerializer({"access_token": access_token})
        return Response(serializer.data)


class CurrentUserView(APIView):
    permission_classes = [RequireViewer]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)


class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [RequireViewer]
    queryset = DocumentMetadata.objects.all().order_by("-created_at")
    serializer_class = DocumentListItemSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Filters
        doc_status = request.query_params.get("status")
        doc_category = request.query_params.get("document_category")
        min_risk = request.query_params.get("min_risk_score")
        max_risk = request.query_params.get("max_risk_score")
        conflict_found = request.query_params.get("conflict_found")
        indexed = request.query_params.get("indexed")
        uploaded_by_id = request.query_params.get("uploaded_by_id")
        created_from = request.query_params.get("created_from")
        created_to = request.query_params.get("created_to")

        if doc_status:
            queryset = queryset.filter(status=doc_status)
        if doc_category:
            queryset = queryset.filter(document_category=doc_category.strip())
        if min_risk:
            queryset = queryset.filter(risk_score__gte=int(min_risk))
        if max_risk:
            queryset = queryset.filter(risk_score__lte=int(max_risk))
        if conflict_found is not None:
            queryset = queryset.filter(conflict_found=conflict_found.lower() == "true")
        if indexed is not None:
            if indexed.lower() == "true":
                queryset = queryset.filter(qdrant_point_id__isnull=False)
            else:
                queryset = queryset.filter(qdrant_point_id__isnull=True)
        if uploaded_by_id:
            queryset = queryset.filter(uploaded_by_id=uuid.UUID(uploaded_by_id))
        if created_from:
            queryset = queryset.filter(created_at__gte=created_from)
        if created_to:
            queryset = queryset.filter(created_at__lte=created_to)

        # Pagination
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))
        sliced_queryset = queryset[offset : offset + limit]

        serializer = self.get_serializer(sliced_queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[RequireViewer])
    def summary(self, request):
        status_counts = dict(
            DocumentMetadata.objects.values_list("status").annotate(count=Count("id"))
        )

        total = DocumentMetadata.objects.count()
        conflict_found_count = DocumentMetadata.objects.filter(conflict_found=True).count()
        indexed_count = DocumentMetadata.objects.filter(qdrant_point_id__isnull=False).count()
        waiting_for_admin_with_conflict = DocumentMetadata.objects.filter(
            status=DocumentStatus.WAITING_FOR_ADMIN, conflict_found=True
        ).count()

        summary_data = {
            "total": total,
            "uploaded": status_counts.get("UPLOADED", 0),
            "processing": status_counts.get("PROCESSING", 0),
            "waiting_for_admin": status_counts.get("WAITING_FOR_ADMIN", 0),
            "approved": status_counts.get("APPROVED", 0),
            "rejected": status_counts.get("REJECTED", 0),
            "failed": status_counts.get("FAILED", 0),
            "conflict_found_count": conflict_found_count,
            "indexed_count": indexed_count,
            "waiting_for_admin_with_conflict": waiting_for_admin_with_conflict,
        }

        serializer = DocumentSummarySerializer(summary_data)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser], permission_classes=[RequireEditor])
    def upload(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        document = save_uploaded_document(file=file_obj, uploaded_by=request.user)

        # Trigger Celery Task
        task = process_document_task.delay(str(document.id))

        document.celery_task_id = task.id
        document.save()

        create_document_audit_log(
            document_id=document.id,
            actor_user_id=request.user.id,
            action="DOCUMENT_UPLOADED",
            message=f"Document uploaded by {request.user.email}. Background processing started.",
            extra_data={
                "original_filename": document.original_filename,
                "stored_filename": document.stored_filename,
                "content_type": document.content_type,
                "file_size_bytes": document.file_size_bytes,
                "celery_task_id": task.id,
            },
        )

        serializer = DocumentUploadSerializer(document)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"], permission_classes=[RequireViewer])
    def status(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DocumentStatusSerializer(document)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="task-status", permission_classes=[RequireViewer])
    def task_status(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        celery_state = None
        celery_result = None

        if document.celery_task_id:
            task_result = celery_app.AsyncResult(document.celery_task_id)
            celery_state = task_result.state
            if task_result.ready():
                celery_result = make_json_safe(task_result.result)

        serializer = DocumentTaskStatusSerializer({
            "document_id": document.id,
            "original_filename": document.original_filename,
            "database_status": document.status,
            "document_category": document.document_category,
            "risk_score": document.risk_score,
            "celery_task_id": document.celery_task_id,
            "celery_state": celery_state,
            "celery_result": celery_result,
            "error_message": document.error_message,
        })
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[RequireEditor])
    def reprocess(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        allowed_statuses = {"UPLOADED", "FAILED"}
        is_legacy_conflict_waiting = (
            document.status == DocumentStatus.WAITING_FOR_ADMIN
            and document.conflict_found is True
        )

        if document.status not in allowed_statuses and not is_legacy_conflict_waiting:
            return Response(
                {"detail": "Only UPLOADED, FAILED, or legacy WAITING_FOR_ADMIN conflict documents can be reprocessed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_status = document.status

        # Trigger Reprocessing
        task = process_document_task.delay(str(document.id))

        document.celery_task_id = task.id
        document.status = DocumentStatus.UPLOADED
        document.error_message = None
        document.conflict_found = False
        document.conflict_summary = None
        document.conflict_checked_at = None
        document.save()

        create_document_audit_log(
            document_id=document.id,
            actor_user_id=request.user.id,
            action="DOCUMENT_REPROCESS_REQUESTED",
            message=f"Document reprocessing requested by {request.user.email}.",
            extra_data={
                "celery_task_id": task.id,
                "requested_by": request.user.email,
                "previous_status": previous_status,
            },
        )

        serializer = DocumentReprocessSerializer({
            "id": document.id,
            "original_filename": document.original_filename,
            "status": document.status,
            "celery_task_id": task.id,
            "message": "Document reprocessing started.",
        })
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[RequireAdmin])
    def index(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if document.status != DocumentStatus.APPROVED:
            return Response(
                {"detail": "Only APPROVED documents can be indexed into Qdrant."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not document.cleaned_text_filename:
            return Response(
                {"detail": "Document has no cleaned text file. Reprocess the document first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if document.conflict_found:
            has_hitl_approval = DocumentAuditLog.objects.filter(
                document_id=document.id, action="DOCUMENT_HITL_APPROVED"
            ).exists()
            if not has_hitl_approval:
                return Response(
                    {"detail": "This document has a detected conflict. It can only be indexed after HITL approval."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            indexing_result = index_cleaned_document_in_qdrant(
                document_id=document.id,
                original_filename=document.original_filename,
                cleaned_text_filename=document.cleaned_text_filename,
                document_category=document.document_category,
                risk_score=document.risk_score,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Qdrant indexing failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        document.qdrant_point_id = indexing_result["qdrant_point_id"]
        document.indexed_at = django_timezone.now()
        document.save()

        create_document_audit_log(
            document_id=document.id,
            actor_user_id=request.user.id,
            action="DOCUMENT_INDEXED_IN_QDRANT",
            message=f"Document indexed into Qdrant Gold collection by {request.user.email}.",
            extra_data={
                "qdrant_point_id": str(document.qdrant_point_id),
                "collection_name": indexing_result["collection_name"],
                "vector_size": indexing_result["vector_size"],
                "chunks_indexed": indexing_result["chunks_indexed"],
                "points_indexed": indexing_result["points_indexed"],
                "indexed_by": request.user.email,
            },
        )

        serializer = DocumentIndexSerializer({
            "id": document.id,
            "original_filename": document.original_filename,
            "status": document.status,
            "document_category": document.document_category,
            "risk_score": document.risk_score,
            "qdrant_point_id": document.qdrant_point_id,
            "indexed_at": document.indexed_at,
            "chunks_indexed": indexing_result["chunks_indexed"],
            "points_indexed": indexing_result["points_indexed"],
            "message": "Document indexed into Qdrant Gold collection successfully.",
        })
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="qdrant-point", permission_classes=[RequireAdmin])
    def qdrant_point(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if not document.qdrant_point_id:
            return Response({
                "document_id": document.id,
                "original_filename": document.original_filename,
                "indexed": False,
                "qdrant_point_id": None,
                "collection_name": None,
                "payload": None,
                "message": "Document has not been indexed into Qdrant yet.",
            })

        qdrant_result = get_gold_collection_point(point_id=str(document.qdrant_point_id))

        return Response({
            "document_id": document.id,
            "original_filename": document.original_filename,
            "indexed": qdrant_result["found"],
            "qdrant_point_id": document.qdrant_point_id,
            "collection_name": qdrant_result["collection_name"],
            "payload": qdrant_result["payload"],
            "message": (
                "Document point exists in Qdrant Gold collection."
                if qdrant_result["found"]
                else "Document has qdrant_point_id in PostgreSQL, but point was not found in Qdrant."
            ),
        })

    @action(detail=True, methods=["get"], url_path="qdrant-chunks", permission_classes=[RequireAdmin])
    def qdrant_chunks(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if not document.qdrant_point_id:
            return Response({
                "document_id": document.id,
                "original_filename": document.original_filename,
                "indexed": False,
                "chunks_count": 0,
                "chunks": [],
                "message": "Document has not been indexed into Qdrant yet.",
            })

        limit = int(request.query_params.get("limit", 50))
        qdrant_chunks = get_gold_collection_chunks_for_document(document_id=str(document.id), limit=limit)

        chunks_list = [
            {
                "point_id": chunk["point_id"],
                "chunk_index": chunk["payload"].get("chunk_index") if chunk.get("payload") else None,
                "chunk_text": chunk["payload"].get("chunk_text") if chunk.get("payload") else None,
                "char_count": chunk["payload"].get("char_count") if chunk.get("payload") else None,
                "payload": chunk["payload"],
            }
            for chunk in qdrant_chunks
        ]

        serializer = DocumentQdrantChunksSerializer({
            "document_id": document.id,
            "original_filename": document.original_filename,
            "indexed": True,
            "chunks_count": len(chunks_list),
            "chunks": chunks_list,
            "message": "Qdrant chunk points retrieved successfully.",
        })
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="conflict-check", permission_classes=[RequireEditor])
    def conflict_check(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if not document.cleaned_text_filename:
            return Response(
                {"detail": "Document has no cleaned text file. Reprocess the document first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        similarity_threshold = float(request.query_params.get("similarity_threshold", 0.75))
        limit = int(request.query_params.get("limit", 5))

        conflict_result = check_document_conflicts(
            document_id=document.id,
            cleaned_text_filename=document.cleaned_text_filename,
            similarity_threshold=similarity_threshold,
            limit=limit,
        )

        potential_conflicts = conflict_result["potential_conflicts"]

        if conflict_result["conflict_found"]:
            top_match = potential_conflicts[0]
            document.conflict_summary = (
                f"Potential conflict found with Qdrant point "
                f"{top_match['point_id']} at similarity score {top_match['score']:.4f}."
            )
        else:
            document.conflict_summary = "No potential conflict found in Qdrant Gold collection."

        document.conflict_found = conflict_result["conflict_found"]
        document.conflict_checked_at = django_timezone.now()
        document.save()

        create_document_audit_log(
            document_id=document.id,
            actor_user_id=request.user.id,
            action="DOCUMENT_CONFLICT_CHECKED",
            message=(
                "Potential conflict found in Qdrant Gold collection."
                if conflict_result["conflict_found"]
                else "No potential conflict found in Qdrant Gold collection."
            ),
            extra_data={
                "similarity_threshold": similarity_threshold,
                "matches_checked": conflict_result["matches_checked"],
                "conflict_found": conflict_result["conflict_found"],
                "conflict_summary": document.conflict_summary,
                "checked_by": request.user.email,
                "potential_conflicts": [
                    {
                        "point_id": match["point_id"],
                        "score": match["score"],
                        "original_filename": match["payload"].get("original_filename") if match.get("payload") else None,
                        "document_category": match["payload"].get("document_category") if match.get("payload") else None,
                    }
                    for match in potential_conflicts
                ],
            },
        )

        serializer = DocumentConflictCheckSerializer({
            "document_id": document.id,
            "original_filename": document.original_filename,
            "conflict_found": conflict_result["conflict_found"],
            "similarity_threshold": conflict_result["similarity_threshold"],
            "matches_checked": conflict_result["matches_checked"],
            "potential_conflicts": [
                {
                    "point_id": match["point_id"],
                    "score": match["score"],
                    "payload": match["payload"],
                }
                for match in potential_conflicts
            ],
            "message": "Potential conflict found." if conflict_result["conflict_found"] else "No potential conflict found.",
        })
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[RequireAdmin])
    def resume(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if document.status not in {"PAUSED", "WAITING_FOR_ADMIN"}:
            return Response(
                {"detail": "Only documents waiting for Admin review can be resumed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        decision = request.data.get("decision")
        reason = request.data.get("reason", "")

        if decision not in {"approve", "reject"}:
            return Response(
                {"detail": "Invalid decision. Must be 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resume LangGraph Workflow
        graph = build_adgs_graph()
        graph_config = {"configurable": {"thread_id": f"document:{document.id}"}}

        try:
            graph_result = graph.invoke(
                Command(resume={"decision": decision, "reason": reason}),
                config=graph_config,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Workflow resume failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if graph_result.get("current_step") == "FAILED":
            document.status = DocumentStatus.FAILED
            document.error_message = graph_result.get("error_message", "HITL resume failed.")
            document.save()

            create_document_audit_log(
                document_id=document.id,
                actor_user_id=request.user.id,
                action="DOCUMENT_HITL_RESUME_FAILED",
                message=document.error_message,
                extra_data={
                    "thread_id": f"document:{document.id}",
                    "resumed_by": request.user.email,
                    "decision": decision,
                },
            )

            return Response({"detail": document.error_message}, status=status.HTTP_400_BAD_REQUEST)

        hitl_decision = graph_result.get("hitl_decision") or decision
        hitl_reason = graph_result.get("hitl_reason") or reason

        if hitl_decision == "approve":
            document.status = DocumentStatus.APPROVED
            document.error_message = hitl_reason
            audit_action = "DOCUMENT_HITL_APPROVED"
            response_message = "Paused workflow resumed and document approved."
        else:
            document.status = DocumentStatus.REJECTED
            document.error_message = hitl_reason
            audit_action = "DOCUMENT_HITL_REJECTED"
            response_message = "Paused workflow resumed and document rejected."

        document.save()

        create_document_audit_log(
            document_id=document.id,
            actor_user_id=request.user.id,
            action=audit_action,
            message=hitl_reason,
            extra_data={
                "thread_id": f"document:{document.id}",
                "resumed_by": request.user.email,
                "hitl_decision": hitl_decision,
                "conflict_found": document.conflict_found,
                "conflict_summary": document.conflict_summary,
                "risk_score": document.risk_score,
                "document_category": document.document_category,
            },
        )

        if hitl_decision == "approve":
            if not document.cleaned_text_filename:
                document.status = DocumentStatus.FAILED
                document.error_message = "Document was approved, but indexing failed because cleaned text is missing."
                document.save()
                return Response({"detail": document.error_message}, status=status.HTTP_400_BAD_REQUEST)

            try:
                indexing_result = index_cleaned_document_in_qdrant(
                    document_id=document.id,
                    original_filename=document.original_filename,
                    cleaned_text_filename=document.cleaned_text_filename,
                    document_category=document.document_category,
                    risk_score=document.risk_score,
                )

                document.qdrant_point_id = indexing_result["qdrant_point_id"]
                document.indexed_at = django_timezone.now()
                document.save()

                create_document_audit_log(
                    document_id=document.id,
                    actor_user_id=request.user.id,
                    action="DOCUMENT_INDEXED_IN_QDRANT",
                    message=f"Document automatically indexed into Qdrant Gold collection after Admin approval by {request.user.email}.",
                    extra_data={
                        "qdrant_point_id": str(document.qdrant_point_id),
                        "collection_name": indexing_result["collection_name"],
                        "vector_size": indexing_result["vector_size"],
                        "chunks_indexed": indexing_result["chunks_indexed"],
                        "points_indexed": indexing_result["points_indexed"],
                        "indexed_by": request.user.email,
                        "indexing_trigger": "HITL_APPROVAL_RESUME",
                    },
                )
            except Exception as exc:
                document.status = DocumentStatus.FAILED
                document.error_message = f"Document was approved, but automatic Qdrant indexing failed: {str(exc)}"
                document.save()

                create_document_audit_log(
                    document_id=document.id,
                    actor_user_id=request.user.id,
                    action="DOCUMENT_INDEXING_FAILED",
                    message=document.error_message,
                    extra_data={
                        "reason": str(exc),
                        "approved_by": request.user.email,
                        "indexing_trigger": "HITL_APPROVAL_RESUME",
                    },
                )

        serializer = DocumentResumeSerializer({
            "id": document.id,
            "original_filename": document.original_filename,
            "status": document.status,
            "hitl_decision": hitl_decision,
            "hitl_reason": hitl_reason,
            "message": response_message,
        })
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[RequireAdmin])
    def approve(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if document.status != DocumentStatus.WAITING_FOR_ADMIN:
            return Response(
                {"detail": "Only documents waiting for admin approval can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if document.conflict_found:
            return Response(
                {"detail": "This document has a detected conflict. Use the HITL resume endpoint to approve or reject it."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = document.status
        reason = request.data.get("reason", f"Approved by admin: {request.user.email}")

        document.status = DocumentStatus.APPROVED
        document.error_message = reason
        document.save()

        create_document_audit_log(
            document_id=document.id,
            actor_user_id=request.user.id,
            action="DOCUMENT_APPROVED",
            message=reason,
            extra_data={
                "old_status": old_status,
                "new_status": DocumentStatus.APPROVED,
                "approved_by": request.user.email,
                "document_category": document.document_category,
                "risk_score": document.risk_score,
            },
        )

        serializer = DocumentDecisionSerializer({
            "id": document.id,
            "original_filename": document.original_filename,
            "status": document.status,
            "document_category": document.document_category,
            "risk_score": document.risk_score,
            "decision_message": reason,
        })
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[RequireAdmin])
    def reject(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if document.status != DocumentStatus.WAITING_FOR_ADMIN:
            return Response(
                {"detail": "Only documents waiting for admin approval can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = document.status
        reason = request.data.get("reason", f"Rejected by admin: {request.user.email}")

        document.status = DocumentStatus.REJECTED
        document.error_message = reason
        document.save()

        create_document_audit_log(
            document_id=document.id,
            actor_user_id=request.user.id,
            action="DOCUMENT_REJECTED",
            message=reason,
            extra_data={
                "old_status": old_status,
                "new_status": DocumentStatus.REJECTED,
                "rejected_by": request.user.email,
                "document_category": document.document_category,
                "risk_score": document.risk_score,
            },
        )

        serializer = DocumentDecisionSerializer({
            "id": document.id,
            "original_filename": document.original_filename,
            "status": document.status,
            "document_category": document.document_category,
            "risk_score": document.risk_score,
            "decision_message": reason,
        })
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="audit-logs", permission_classes=[RequireViewer])
    def audit_logs(self, request, pk=None):
        try:
            document = DocumentMetadata.objects.get(id=uuid.UUID(pk))
        except (DocumentMetadata.DoesNotExist, ValueError):
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        queryset = DocumentAuditLog.objects.filter(document_id=document.id).order_by("-created_at")

        # Filters
        log_action = request.query_params.get("action")
        actor_user_id = request.query_params.get("actor_user_id")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if log_action:
            queryset = queryset.filter(action=log_action.strip())
        if actor_user_id:
            queryset = queryset.filter(actor_user_id=uuid.UUID(actor_user_id))
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))
        sliced_queryset = queryset[offset : offset + limit]

        serializer = DocumentAuditLogSerializer(sliced_queryset, many=True)
        return Response(serializer.data)


class RagSearchView(APIView):
    permission_classes = [RequireViewer]

    def post(self, request):
        req_serializer = RagSearchRequestSerializer(data=request.data)
        if not req_serializer.is_valid():
            return Response(req_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = req_serializer.validated_data["query"]
        limit = req_serializer.validated_data["limit"]
        min_score = req_serializer.validated_data["min_score"]

        try:
            # 1. Fetch similarity matches from Qdrant
            search_result = search_approved_gold_chunks(
                query=query,
                limit=limit,
                min_score=min_score,
            )

            matches_list = search_result.get("matches", [])

            # 2. Extract context for synthesis
            formatted_chunks = [
                {
                    "text": m.get("chunk_text") or m.get("text", ""),
                    "point_id": m.get("point_id") or str(m.get("id", uuid.uuid4())),
                    "metadata": {
                        "document_id": m.get("document_id"),
                        "original_filename": m.get("original_filename"),
                        "document_category": m.get("document_category"),
                        "risk_score": m.get("risk_score"),
                    },
                }
                for m in matches_list
            ]

            # Deterministic LLM response synthesis
            synthesis_pack = llm_service.synthesize_answer(
                question=query, chunks=formatted_chunks
            )

            # 3. Save RAG Search audit log in Postgres using Django ORM
            create_rag_search_audit_log(
                current_user=request.user,
                query=query,
                result_limit=limit,
                min_score=min_score,
                search_result=search_result,
            )

            response_data = {
                "query": search_result["query"],
                "min_score": search_result["min_score"],
                "matches_count": search_result["matches_count"],
                "matches": [
                    {
                        "point_id": m.get("point_id"),
                        "score": m.get("score"),
                        "document_id": m.get("document_id"),
                        "original_filename": m.get("original_filename"),
                        "document_category": m.get("document_category"),
                        "risk_score": m.get("risk_score"),
                        "chunk_index": m.get("chunk_index"),
                        "chunk_text": m.get("chunk_text"),
                        "source": m.get("source"),
                        "text": m.get("chunk_text") or m.get("text"),
                        "metadata": {
                            "document_id": m.get("document_id"),
                            "original_filename": m.get("original_filename"),
                            "document_category": m.get("document_category"),
                            "risk_score": m.get("risk_score"),
                        },
                    }
                    for m in matches_list
                ],
                "synthesized_answer": synthesis_pack["answer"],
            }

            serializer = RagSearchSerializer(response_data)
            return Response(serializer.data)

        except Exception as exc:
            return Response(
                {"detail": f"Secure RAG processing encountered an error: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RagSearchAuditLogsView(APIView):
    permission_classes = [RequireAdmin]

    def get(self, request):
        queryset = RagSearchAuditLog.objects.all().order_by("-created_at")

        actor_user_id = request.query_params.get("actor_user_id")
        query_contains = request.query_params.get("query_contains")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if actor_user_id:
            queryset = queryset.filter(actor_user_id=uuid.UUID(actor_user_id))
        if query_contains:
            queryset = queryset.filter(query__icontains=query_contains.strip())
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))
        sliced_queryset = queryset[offset : offset + limit]

        serializer = RagSearchAuditLogSerializer(sliced_queryset, many=True)
        return Response(serializer.data)


class QdrantHealthView(APIView):
    permission_classes = [RequireAdmin]

    def get(self, request):
        try:
            health = check_qdrant_health()
            return Response(health)
        except Exception as exc:
            return Response(
                {"detail": f"Qdrant is not reachable: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class CreateGoldCollectionView(APIView):
    permission_classes = [RequireAdmin]

    def post(self, request):
        try:
            res = ensure_gold_collection()
            return Response(res)
        except Exception as exc:
            return Response(
                {"detail": f"Could not create Qdrant gold collection: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class SystemAuditSummaryView(APIView):
    permission_classes = [RequireAdmin]

    def get(self, request):
        now = django_timezone.now()
        last_24h = now - timedelta(hours=24)

        status_counts = dict(
            DocumentMetadata.objects.values_list("status").annotate(count=Count("id"))
        )

        total_documents = DocumentMetadata.objects.count()
        indexed_documents = DocumentMetadata.objects.filter(qdrant_point_id__isnull=False).count()
        conflict_found_count = DocumentMetadata.objects.filter(conflict_found=True).count()
        high_risk_documents = DocumentMetadata.objects.filter(risk_score__gte=75).count()
        recent_documents_24h = DocumentMetadata.objects.filter(created_at__gte=last_24h).count()

        total_rag_searches = RagSearchAuditLog.objects.count()
        recent_rag_searches_24h = RagSearchAuditLog.objects.filter(created_at__gte=last_24h).count()

        total_document_audit_logs = DocumentAuditLog.objects.count()
        recent_document_audit_logs_24h = DocumentAuditLog.objects.filter(created_at__gte=last_24h).count()

        return Response({
            "generated_at": now.isoformat(),
            "documents": {
                "total": total_documents,
                "uploaded": status_counts.get("UPLOADED", 0),
                "processing": status_counts.get("PROCESSING", 0),
                "paused": status_counts.get("PAUSED", 0),
                "waiting_for_admin": status_counts.get("WAITING_FOR_ADMIN", 0),
                "approved": status_counts.get("APPROVED", 0),
                "rejected": status_counts.get("REJECTED", 0),
                "failed": status_counts.get("FAILED", 0),
                "indexed": indexed_documents,
                "conflict_found": conflict_found_count,
                "high_risk": high_risk_documents,
                "created_last_24h": recent_documents_24h,
            },
            "rag": {
                "total_searches": total_rag_searches,
                "searches_last_24h": recent_rag_searches_24h,
            },
            "audit_logs": {
                "document_audit_logs_total": total_document_audit_logs,
                "document_audit_logs_last_24h": recent_document_audit_logs_24h,
            },
        })


class QdrantIntegrityView(APIView):
    permission_classes = [RequireAdmin]

    def get(self, request):
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        indexed_documents = DocumentMetadata.objects.filter(
            qdrant_point_id__isnull=False
        ).order_by("-indexed_at")[offset : offset + limit]

        integrity_items = []
        ok_count = 0
        broken_count = 0

        for doc in indexed_documents:
            qdrant_point_res = get_gold_collection_point(point_id=str(doc.qdrant_point_id))
            qdrant_chunks = get_gold_collection_chunks_for_document(document_id=str(doc.id), limit=200)

            point_found = qdrant_point_res["found"]
            chunks_count = len(qdrant_chunks)

            integrity_status = "OK" if point_found and chunks_count > 0 else "BROKEN"

            if integrity_status == "OK":
                ok_count += 1
            else:
                broken_count += 1

            integrity_items.append({
                "document_id": str(doc.id),
                "original_filename": doc.original_filename,
                "status": doc.status,
                "document_category": doc.document_category,
                "risk_score": doc.risk_score,
                "qdrant_point_id": str(doc.qdrant_point_id) if doc.qdrant_point_id else None,
                "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
                "document_point_found": point_found,
                "chunk_points_count": chunks_count,
                "integrity_status": integrity_status,
            })

        return Response({
            "checked_count": len(integrity_items),
            "ok_count": ok_count,
            "broken_count": broken_count,
            "items": integrity_items,
        })


class RepairQdrantIntegrityView(APIView):
    permission_classes = [RequireAdmin]

    def post(self, request):
        dry_run = request.query_params.get("dry_run", "true").lower() == "true"
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        indexed_documents = DocumentMetadata.objects.filter(
            qdrant_point_id__isnull=False
        ).order_by("-indexed_at")[offset : offset + limit]

        checked_count = 0
        broken_count = 0
        repaired_count = 0
        broken_items = []

        for doc in indexed_documents:
            checked_count += 1

            qdrant_point_res = get_gold_collection_point(point_id=str(doc.qdrant_point_id))
            qdrant_chunks = get_gold_collection_chunks_for_document(document_id=str(doc.id), limit=200)

            point_found = qdrant_point_res["found"]
            chunks_count = len(qdrant_chunks)

            is_broken = not point_found or chunks_count == 0

            if not is_broken:
                continue

            broken_count += 1

            broken_item = {
                "document_id": str(doc.id),
                "original_filename": doc.original_filename,
                "status": doc.status,
                "document_category": doc.document_category,
                "risk_score": doc.risk_score,
                "old_qdrant_point_id": str(doc.qdrant_point_id) if doc.qdrant_point_id else None,
                "old_indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
                "document_point_found": point_found,
                "chunk_points_count": chunks_count,
                "repair_action": "DRY_RUN_ONLY" if dry_run else "CLEARED_POSTGRES_QDRANT_INDEX_FIELDS",
            }

            broken_items.append(broken_item)

            if dry_run:
                continue

            old_qdrant_point_id = doc.qdrant_point_id
            old_indexed_at = doc.indexed_at

            # Clear PostgreSQL fields
            doc.qdrant_point_id = None
            doc.indexed_at = None
            doc.save()

            create_document_audit_log(
                document_id=doc.id,
                actor_user_id=request.user.id,
                action="DOCUMENT_QDRANT_INTEGRITY_REPAIRED",
                message=f"Stale PostgreSQL Qdrant indexing fields were cleared by {request.user.email} after integrity check.",
                extra_data={
                    "repaired_by": request.user.email,
                    "old_qdrant_point_id": str(old_qdrant_point_id) if old_qdrant_point_id else None,
                    "old_indexed_at": old_indexed_at.isoformat() if old_indexed_at else None,
                    "document_point_found": point_found,
                    "chunk_points_count": chunks_count,
                },
            )

            repaired_count += 1

        return Response({
            "dry_run": dry_run,
            "checked_count": checked_count,
            "broken_count": broken_count,
            "repaired_count": repaired_count,
            "items": broken_items,
        })

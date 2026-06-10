from django.urls import path, include
from rest_framework.routers import DefaultRouter

from app.views import (
    HealthCheckView,
    LoginView,
    CurrentUserView,
    DocumentViewSet,
    RagSearchView,
    RagSearchAuditLogsView,
    QdrantHealthView,
    CreateGoldCollectionView,
    SystemAuditSummaryView,
    QdrantIntegrityView,
    RepairQdrantIntegrityView,
)

router = DefaultRouter(trailing_slash=False)
router.register(r"documents", DocumentViewSet, basename="document")

urlpatterns = [
    # Health check
    path("health", HealthCheckView.as_view(), name="health"),
    
    # Auth endpoints
    path("auth/login", LoginView.as_view(), name="login"),
    
    # User profile
    path("users/me", CurrentUserView.as_view(), name="user_me"),
    
    # RAG endpoints
    path("rag/search", RagSearchView.as_view(), name="rag_search"),
    path("rag/audit-logs", RagSearchAuditLogsView.as_view(), name="rag_audit_logs"),
    
    # System endpoints
    path("system/qdrant-health", QdrantHealthView.as_view(), name="qdrant_health"),
    path("system/qdrant/gold-collection", CreateGoldCollectionView.as_view(), name="qdrant_gold_collection"),
    path("system/audit-summary", SystemAuditSummaryView.as_view(), name="system_audit_summary"),
    path("system/qdrant-integrity", QdrantIntegrityView.as_view(), name="qdrant_integrity"),
    path("system/qdrant-integrity/repair", RepairQdrantIntegrityView.as_view(), name="qdrant_integrity_repair"),
    
    # Include router URLs (like /documents, /documents/{id}, etc.)
    path("", include(router.urls)),
]

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.services.structured_profile_service import build_structured_profile
from app.db.worker_session import WorkerAsyncSessionLocal
from app.graph.workflow import build_adgs_graph
from app.models.document_metadata import DocumentMetadata, DocumentStatus
from app.services.audit_service import create_document_audit_log
from app.services.cleaned_text_service import save_cleaned_text
from app.workers.celery_app import celery_app


@celery_app.task(name="health_check_task")
def health_check_task() -> dict[str, str]:
    return {
        "status": "healthy",
        "worker": "ADGS Celery worker is running",
    }


def summarize_pii(detected_pii: list[dict[str, str]]) -> dict[str, Any]:
    pii_type_counts: dict[str, int] = {}

    for item in detected_pii:
        pii_type = item.get("type", "UNKNOWN")
        pii_type_counts[pii_type] = pii_type_counts.get(pii_type, 0) + 1

    return {
        "pii_count": len(detected_pii),
        "pii_types": pii_type_counts,
    }


async def _process_document(document_id: str) -> dict[str, str]:
    async with WorkerAsyncSessionLocal() as session:
        result = await session.execute(
            select(DocumentMetadata).where(
                DocumentMetadata.id == uuid.UUID(document_id)
            )
        )
        document = result.scalar_one_or_none()

        if document is None:
            return {
                "status": "failed",
                "reason": "Document not found",
            }

        try:
            document.status = DocumentStatus.PROCESSING
            document.error_message = None

            await create_document_audit_log(
                db=session,
                document_id=document.id,
                actor_user_id=None,
                action="DOCUMENT_PROCESSING_STARTED",
                message="Celery worker started AI governance processing.",
                extra_data={
                    "celery_task": "process_document_task",
                    "stored_filename": document.stored_filename,
                },
            )

            await session.commit()

            graph = build_adgs_graph()

            initial_state = {
                "document_id": str(document.id),
                "original_filename": document.original_filename,
                "stored_filename": document.stored_filename,
                "current_step": "STARTED",
            }

            graph_config = {
                "configurable": {
                    "thread_id": f"document:{document.id}",
                }
             }

            graph_result = graph.invoke(
                    initial_state,
                    config=graph_config,
            )

            if "__interrupt__" in graph_result:
                graph_snapshot = graph.get_state(graph_config)
                paused_state = graph_snapshot.values

                detected_pii = paused_state.get("detected_pii", [])
                pii_summary = summarize_pii(detected_pii)

                extraction_metadata = paused_state.get("extraction_metadata", {})
                extraction_method = paused_state.get("extraction_method")

                structured_profile = build_structured_profile(
                    extraction_method=extraction_method,
                    extraction_metadata=extraction_metadata,
                    extracted_text=paused_state.get("raw_text"),
                )

                cleaned_text = paused_state.get("cleaned_text")
                if cleaned_text and not document.cleaned_text_filename:
                    cleaned_text_filename = save_cleaned_text(
                        document_id=str(document.id),
                        cleaned_text=cleaned_text,
                    )
                    document.cleaned_text_filename = cleaned_text_filename

                document.document_category = paused_state.get("document_category")
                document.risk_score = min(len(detected_pii) * 25, 100)

                document.conflict_found = paused_state.get("conflict_found", False)
                document.conflict_summary = paused_state.get("conflict_summary")
                document.conflict_checked_at = datetime.now(timezone.utc)

                document.status = DocumentStatus.PAUSED
                document.error_message = "Workflow paused for Admin HITL review."

                interrupt_payload = graph_result["__interrupt__"]

                await create_document_audit_log(
                    db=session,
                    document_id=document.id,
                    actor_user_id=None,
                    action="DOCUMENT_PII_DETECTED",
                    message="PII scan completed before HITL pause. Actual PII values are not stored in audit logs.",
                    extra_data={
                        "document_category": document.document_category,
                        "risk_score": document.risk_score,
                        "pii_summary": pii_summary,
                        "cleaned_text_filename": document.cleaned_text_filename,
                        "extraction_method": extraction_method,
                        "extraction_metadata": extraction_metadata,
                        "structured_profile": structured_profile,
                    },
                )

                await create_document_audit_log(
                    db=session,
                    document_id=document.id,
                    actor_user_id=None,
                    action="DOCUMENT_CONFLICT_CHECKED",
                    message=(
                        document.conflict_summary
                        or "Conflict Agent completed before HITL pause."
                    ),
                    extra_data={
                        "conflict_found": document.conflict_found,
                        "conflict_summary": document.conflict_summary,
                        "conflict_checked_at": (
                            document.conflict_checked_at.isoformat()
                            if document.conflict_checked_at
                            else None
                        ),
                    },
                )

                await create_document_audit_log(
                    db=session,
                    document_id=document.id,
                    actor_user_id=None,
                    action="DOCUMENT_HITL_PAUSED",
                    message="LangGraph workflow paused for Admin review.",
                    extra_data={
                        "thread_id": f"document:{document.id}",
                        "interrupt": str(interrupt_payload),
                        "document_category": document.document_category,
                        "risk_score": document.risk_score,
                        "conflict_found": document.conflict_found,
                        "conflict_summary": document.conflict_summary,
                    },
                )

                await session.commit()

                return {
                    "status": "paused",
                    "document_id": document_id,
                    "thread_id": f"document:{document.id}",
                    "reason": "Workflow paused for Admin HITL review.",
                }

            if graph_result.get("current_step") == "FAILED":
                document.status = DocumentStatus.FAILED
                document.error_message = graph_result.get(
                    "error_message",
                    "LangGraph processing failed.",
                )

                await create_document_audit_log(
                    db=session,
                    document_id=document.id,
                    actor_user_id=None,
                    action="DOCUMENT_PROCESSING_FAILED",
                    message=document.error_message,
                    extra_data={
                        "failure_stage": graph_result.get("current_step"),
                    },
                )

                await session.commit()

                return {
                    "status": "failed",
                    "document_id": document_id,
                    "reason": document.error_message,
                }

            detected_pii = graph_result.get("detected_pii", [])
            pii_summary = summarize_pii(detected_pii)

            extraction_metadata = graph_result.get("extraction_metadata", {})
            extraction_method = graph_result.get("extraction_method")

            structured_profile = build_structured_profile(
                extraction_method=extraction_method,
                extraction_metadata=extraction_metadata,
                extracted_text=graph_result.get("raw_text"),
            )

            cleaned_text = graph_result.get("cleaned_text")
            if cleaned_text:
                cleaned_text_filename = save_cleaned_text(
                    document_id=str(document.id),
                    cleaned_text=cleaned_text,
                )
                document.cleaned_text_filename = cleaned_text_filename

            document.document_category = graph_result.get("document_category")
            document.risk_score = min(len(detected_pii) * 25, 100)

            document.conflict_found = graph_result.get("conflict_found", False)
            document.conflict_summary = graph_result.get("conflict_summary")
            document.conflict_checked_at = datetime.now(timezone.utc)

            document.error_message = graph_result.get("critic_feedback")

            await create_document_audit_log(
                db=session,
                document_id=document.id,
                actor_user_id=None,
                action="DOCUMENT_PII_DETECTED",
                message="PII scan completed. Actual PII values are not stored in audit logs.",
                extra_data={
                    "document_category": document.document_category,
                    "risk_score": document.risk_score,
                    "pii_summary": pii_summary,
                    "cleaned_text_filename": document.cleaned_text_filename,
                    "extraction_method": extraction_method,
                    "extraction_metadata": extraction_metadata,
                    "structured_profile": structured_profile,
                },
            )

            await create_document_audit_log(
                db=session,
                document_id=document.id,
                actor_user_id=None,
                action="DOCUMENT_CONFLICT_CHECKED",
                message=(
                    document.conflict_summary
                    or "Conflict Agent completed with no summary."
                ),
                extra_data={
                    "conflict_found": document.conflict_found,
                    "conflict_summary": document.conflict_summary,
                    "conflict_checked_at": (
                        document.conflict_checked_at.isoformat()
                        if document.conflict_checked_at
                        else None
                    ),
                },
            )

            if graph_result.get("requires_admin_approval"):
                document.status = DocumentStatus.WAITING_FOR_ADMIN

                await create_document_audit_log(
                    db=session,
                    document_id=document.id,
                    actor_user_id=None,
                    action="DOCUMENT_WAITING_FOR_ADMIN",
                    message=graph_result.get(
                        "critic_feedback",
                        "Document requires admin approval.",
                    ),
                    extra_data={
                        "risk_level": graph_result.get("risk_level", "HIGH"),
                        "risk_score": document.risk_score,
                        "document_category": document.document_category,
                        "conflict_found": document.conflict_found,
                        "conflict_summary": document.conflict_summary,
                    },
                )
            else:
                document.status = DocumentStatus.APPROVED

                await create_document_audit_log(
                    db=session,
                    document_id=document.id,
                    actor_user_id=None,
                    action="DOCUMENT_PROCESSING_COMPLETED",
                    message="Document passed AI governance checks and was auto-approved.",
                    extra_data={
                        "risk_level": graph_result.get("risk_level", "LOW"),
                        "risk_score": document.risk_score,
                        "document_category": document.document_category,
                        "conflict_found": document.conflict_found,
                        "conflict_summary": document.conflict_summary,
                    },
                )

            await session.commit()

            return {
                "status": "completed",
                "document_id": document_id,
                "document_category": document.document_category or "",
                "pii_items_detected": str(len(detected_pii)),
                "conflict_found": str(document.conflict_found),
                "requires_admin_approval": str(
                    graph_result.get("requires_admin_approval", False)
                ),
                "risk_level": graph_result.get("risk_level", "LOW"),
            }

        except Exception as exc:
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)

            await create_document_audit_log(
                db=session,
                document_id=document.id,
                actor_user_id=None,
                action="DOCUMENT_PROCESSING_FAILED",
                message=str(exc),
                extra_data={
                    "failure_source": "celery_worker",
                },
            )

            await session.commit()

            return {
                "status": "failed",
                "document_id": document_id,
                "reason": str(exc),
            }


@celery_app.task(name="process_document_task")
def process_document_task(document_id: str) -> dict[str, str]:
    return asyncio.run(_process_document(document_id))
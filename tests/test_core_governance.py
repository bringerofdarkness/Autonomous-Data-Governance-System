import pytest
from app.services.llm_service import LLMGenerationService
from app.core.config import get_settings

settings = get_settings()

def test_environment_integrity():
    assert settings.LLM_PROVIDER is not None
    assert settings.OLLAMA_URL.endswith("/api/chat")

def test_llm_service_initialization():
    service = LLMGenerationService()
    assert service.provider in ["gemini", "ollama"]
    if service.provider == "gemini":
        assert service.gemini_api_key is not None
    else:
        assert service.ollama_model is not None

def test_rag_empty_chunks_handler():
    service = LLMGenerationService()
    result = service.synthesize_answer("What is the data leak policy?", chunks=[])
    assert "no audited corporate records" in result["answer"]
    assert result["citations"] == []

def test_rag_structured_citation_mapping():
    service = LLMGenerationService()
    sample_chunks = [
        {
            "text": "Data Governance standard ADGS-1 requires isolation fields.",
            "point_id": "test-chunk-99",
            "metadata": {"document_id": "doc-audit-2026"}
        }
    ]
    result = service.synthesize_answer("Explain ADGS-1 requirements", sample_chunks)
    assert "citations" in result
    assert len(result["citations"]) == 1
    assert result["citations"][0]["document_id"] == "doc-audit-2026"
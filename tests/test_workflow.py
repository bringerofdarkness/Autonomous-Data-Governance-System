import pytest
import uuid
from app.graph.workflow import build_adgs_graph

def test_graph_interrupts_on_high_risk_document(mocker):
    """
    Simulate processing the compliance violation document and verify 
    the graph pauses via the interrupt() function.
    """
    # 1. Mock the extraction and PII services so we don't need real files/models during the unit test
    mocker.patch("app.graph.nodes.extract_document_text", return_value={
        "text": "Secret project details. John Doe's SSN is 000-12-3456.",
        "metadata": {"char_count": 55},
        "extraction_method": "utf8_text"
    })
    
    mocker.patch("app.graph.nodes.detect_and_redact_pii", return_value={
        "cleaned_text": "Secret project details. [REDACTED]'s [REDACTED] is [REDACTED].",
        "detected_pii": [{"type": "NAME"}, {"type": "SSN"}, {"type": "PHONE"}] # 3 PII items triggers HIGH risk
    })
    
    mocker.patch("app.graph.nodes.check_text_conflicts", return_value={
        "conflict_found": False,
        "potential_conflicts": []
    })

    # 2. Initialize the compiled graph
    graph = build_adgs_graph()
    
    doc_id = str(uuid.uuid4())
    initial_state = {
        "document_id": doc_id,
        "original_filename": "test_compliance_violation.txt",
        "stored_filename": "mock_stored.txt",
        "current_step": "STARTED",
    }
    
    config = {"configurable": {"thread_id": f"test_thread:{doc_id}"}}

    # 3. Invoke the graph
    result = graph.invoke(initial_state, config=config)

    # 4. Assertions: Verify the graph actually paused and yielded the payload
    assert "__interrupt__" in result, "Graph failed to interrupt/pause for Human-in-the-Loop review!"
    
    interrupt_payload = result["__interrupt__"][0].value
    assert interrupt_payload["type"] == "ADMIN_REVIEW_REQUIRED"
    assert interrupt_payload["detected_pii_count"] == 3
    
    # 5. Verify the state saved in the checkpoint correctly reflects the pause
    saved_state = graph.get_state(config).values
    assert saved_state["risk_level"] == "HIGH"
    assert saved_state["requires_admin_approval"] is True
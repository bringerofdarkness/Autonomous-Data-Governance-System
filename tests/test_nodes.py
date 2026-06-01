import pytest
from app.graph.nodes import critic_node, text_loader_node
from app.graph.state import ADGSGraphState

def test_text_loader_missing_file():
    """Test that the pipeline fails gracefully if the file is missing."""
    initial_state = ADGSGraphState(stored_filename=None)
    
    result = text_loader_node(initial_state)
    
    assert result["current_step"] == "FAILED"
    assert "missing" in result["error_message"]

def test_critic_node_low_risk_auto_approval():
    """Test that 0 PII and no conflicts allows the document to proceed."""
    state = ADGSGraphState(
        detected_pii=[],
        conflict_found=False
    )
    
    result = critic_node(state)
    
    assert result["risk_level"] == "LOW"
    assert result["requires_admin_approval"] is False
    assert result["current_step"] == "CRITIC_REVIEWED"

def test_critic_node_high_pii_triggers_hitl():
    """Test that 3 or more PII items force an admin approval pause."""
    # Simulating the exact scenario our test_compliance_violation.txt will create
    state = ADGSGraphState(
        detected_pii=[
            {"type": "SSN", "value": "REDACTED"}, 
            {"type": "PHONE", "value": "REDACTED"}, 
            {"type": "EMAIL", "value": "REDACTED"}
        ],
        conflict_found=False
    )
    
    result = critic_node(state)
    
    assert result["risk_level"] == "HIGH"
    assert result["requires_admin_approval"] is True
    assert result["current_step"] == "WAITING_FOR_ADMIN"
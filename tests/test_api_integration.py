import io
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.main import app

@pytest.fixture
def client():
    """Provides a FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(autouse=True)
def bypass_api_dependencies(mocker):
    """Bypasses Authentication and Database dependencies for the route."""
    mock_user = mocker.MagicMock(id=uuid.uuid4(), email="test@admin.com")
    mock_db = AsyncMock()

    async def mock_get_db():
        yield mock_db

    for route in app.routes:
        if hasattr(route, "path") and "/documents/upload" in route.path:
            for dep in getattr(route.dependant, "dependencies", []):
                if dep.name == "current_user":
                    app.dependency_overrides[dep.call] = lambda: mock_user
                elif dep.name == "db":
                    app.dependency_overrides[dep.call] = mock_get_db
    
    yield
    app.dependency_overrides.clear()

def test_document_upload_and_worker_handoff(client, mocker):
    # 1. Generate an in-memory file
    file_content = b"This is a standard corporate policy document. No sensitive data here."
    mock_file = io.BytesIO(file_content)
    mock_file.name = "test_corporate_policy.txt"

    # 2. Mock the Database saving function to satisfy Pydantic validations
    mock_document = mocker.MagicMock()
    mock_document.id = uuid.uuid4()
    mock_document.created_at = datetime.now(timezone.utc)
    mock_document.original_filename = "test_corporate_policy.txt"
    mock_document.stored_filename = "mock_stored.txt"
    mock_document.content_type = "text/plain"
    mock_document.uploaded_by_id = uuid.uuid4()
    mock_document.status = "UPLOADED"
    
    mocker.patch("app.api.documents.save_uploaded_document", return_value=mock_document)
    mocker.patch("app.api.documents.create_document_audit_log", return_value=None)

    # 3. Mock the Celery Task trigger
    mock_task = mocker.MagicMock()
    mock_task.id = "mock-celery-task-id"
    mock_delay = mocker.patch("app.api.documents.process_document_task.delay", return_value=mock_task)

    # 4. Execute the API Request
    response = client.post(
        "/documents/upload",
        files={"file": (mock_file.name, mock_file, "text/plain")}
    )

    # 5. Assertions
    assert response.status_code in [200, 202], f"API Upload failed: {response.text}"
    assert mock_delay.called, "Celery task handoff was not triggered!"
    
    response_data = response.json()
    
    # FIX: Changed "document_id" to "id" to match your Pydantic model
    assert "id" in response_data
    
    try:
        parsed_uuid = uuid.UUID(response_data["id"])
        assert parsed_uuid is not None
    except ValueError:
        pytest.fail("Returned id is not a valid UUID format")
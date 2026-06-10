import uuid
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from app.models import DocumentMetadata, Role

User = get_user_model()


class ADGSApiTests(APITestCase):
    def setUp(self):
        # Create a test role and user
        self.role_admin = Role.objects.create(name="Admin", description="Admin role")
        self.role_editor = Role.objects.create(name="Editor", description="Editor role")
        
        self.user = User.objects.create_user(
            email="test@admin.com",
            password="Admin@12345",
            full_name="Test Admin"
        )
        self.user.roles.add(self.role_admin)
        self.user.roles.add(self.role_editor)

    def test_health_check(self):
        url = reverse("health")
        # Health check is public
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")
        self.assertEqual(response.data["service"], "ADGS API")

    @patch("app.views.authenticate_user")
    @patch("app.views.create_user_access_token")
    def test_login(self, mock_create_token, mock_authenticate):
        mock_authenticate.return_value = self.user
        mock_create_token.return_value = "mocked-jwt-token"

        url = reverse("login")
        response = self.client.post(
            url,
            {"username": "test@admin.com", "password": "Admin@12345"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access_token"], "mocked-jwt-token")
        self.assertEqual(response.data["token_type"], "bearer")

    @patch("app.views.save_uploaded_document")
    @patch("app.tasks.process_document_task.delay")
    def test_document_upload_and_worker_handoff(self, mock_delay, mock_save_document):
        # Setup mock return values
        mock_doc_id = uuid.uuid4()
        mock_document = MagicMock(spec=DocumentMetadata)
        mock_document.id = mock_doc_id
        mock_document.original_filename = "test_corporate_policy.txt"
        mock_document.stored_filename = "mock_stored.txt"
        mock_document.content_type = "text/plain"
        mock_document.file_size_bytes = 100
        mock_document.status = "UPLOADED"
        mock_document.celery_task_id = "mock-celery-task-id"
        mock_document.uploaded_by = self.user
        mock_document.created_at = timezone.now()

        mock_save_document.return_value = mock_document
        
        mock_task = MagicMock()
        mock_task.id = "mock-celery-task-id"
        mock_delay.return_value = mock_task

        # Authenticate client
        self.client.force_authenticate(user=self.user)

        # Execute request
        url = reverse("document-upload")
        
        # Create in-memory test file
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile(
            "test_corporate_policy.txt",
            b"This is a standard corporate policy document. No sensitive data here.",
            content_type="text/plain"
        )

        response = self.client.post(url, {"file": test_file}, format="multipart")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["id"], str(mock_doc_id))
        self.assertEqual(response.data["status"], "UPLOADED")
        self.assertTrue(mock_delay.called)

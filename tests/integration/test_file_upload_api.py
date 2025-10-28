"""Integration tests for file upload API endpoint."""

import pytest
from io import BytesIO
from unittest.mock import Mock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from agcluster.container.api.main import app


@pytest.mark.integration
class TestFileUploadAPI:
    """Test file upload API endpoint."""

    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager."""
        import hashlib

        with patch("agcluster.container.api.files.session_manager") as mock_mgr:
            mock_container = Mock()
            mock_container.container_id = "test-container-123"

            # Add container_info with api_key_hash metadata
            mock_container.container_info = Mock()
            # Hash of "test-api-key"
            api_key_hash = hashlib.sha256("test-api-key".encode()).hexdigest()
            mock_container.container_info.metadata = {"api_key_hash": api_key_hash}

            mock_mgr.get_session = AsyncMock(return_value=mock_container)
            yield mock_mgr

    @pytest.fixture
    def mock_container_manager(self):
        """Mock container manager."""
        with patch("agcluster.container.api.files.container_manager") as mock_mgr:
            mock_provider = Mock()
            mock_provider.upload_files = AsyncMock(return_value=["test.txt"])
            mock_mgr.provider = mock_provider
            yield mock_mgr

    @pytest.mark.asyncio
    async def test_upload_single_file(self, mock_session_manager, mock_container_manager):
        """Test uploading a single file."""
        # Create a test file
        file_content = b"Hello World"
        files = {"files": ("test.txt", BytesIO(file_content), "text/plain")}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/test-session/upload",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session"
        assert data["total_files"] == 1
        assert "test.txt" in data["uploaded"]

    @pytest.mark.asyncio
    async def test_upload_multiple_files(self, mock_session_manager, mock_container_manager):
        """Test uploading multiple files."""
        mock_container_manager.provider.upload_files = AsyncMock(
            return_value=["test1.txt", "test2.txt"]
        )

        files = [
            ("files", ("test1.txt", BytesIO(b"File 1"), "text/plain")),
            ("files", ("test2.txt", BytesIO(b"File 2"), "text/plain")),
        ]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/test-session/upload",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 2
        assert "test1.txt" in data["uploaded"]
        assert "test2.txt" in data["uploaded"]

    @pytest.mark.asyncio
    async def test_upload_with_target_path(self, mock_session_manager, mock_container_manager):
        """Test uploading files to a specific path."""
        files = {"files": ("test.txt", BytesIO(b"Hello"), "text/plain")}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/test-session/upload?target_path=data",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        assert response.status_code == 200
        data = response.json()
        assert "/workspace/data" in data["target_path"]

    @pytest.mark.asyncio
    async def test_upload_with_overwrite(self, mock_session_manager, mock_container_manager):
        """Test uploading with overwrite=true."""
        files = {"files": ("test.txt", BytesIO(b"Hello"), "text/plain")}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/test-session/upload?overwrite=true",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, mock_session_manager, mock_container_manager):
        """Test rejection of files that are too large."""
        # Create a file larger than MAX_UPLOAD_SIZE (50MB)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        files = {"files": ("large.bin", BytesIO(large_content), "application/octet-stream")}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/test-session/upload",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        assert response.status_code == 413  # Payload Too Large
        assert "too large" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_too_many_files(self, mock_session_manager, mock_container_manager):
        """Test rejection when uploading too many files."""
        # Create 51 files (MAX_FILES_PER_UPLOAD is 50)
        files = [("files", (f"test{i}.txt", BytesIO(b"content"), "text/plain")) for i in range(51)]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/test-session/upload",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        assert response.status_code == 400
        assert "too many files" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_total_size_too_large(self, mock_session_manager, mock_container_manager):
        """Test rejection when total upload size exceeds limit."""
        # Create 5 files of 45MB each (total 225MB > 200MB limit)
        large_content = b"x" * (45 * 1024 * 1024)  # 45MB each
        files = [
            ("files", (f"file{i}.bin", BytesIO(large_content), "application/octet-stream"))
            for i in range(5)
        ]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/test-session/upload",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        assert response.status_code == 413
        assert "total upload size" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, mock_session_manager, mock_container_manager):
        """Test rejection of disallowed file types."""
        files = {"files": ("malware.exe", BytesIO(b"binary"), "application/x-executable")}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/test-session/upload",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_without_authorization(self, mock_session_manager, mock_container_manager):
        """Test upload fails without authorization header."""
        files = {"files": ("test.txt", BytesIO(b"Hello"), "text/plain")}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/files/test-session/upload", files=files)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_session_not_found(self, mock_session_manager, mock_container_manager):
        """Test upload fails when session not found."""
        from agcluster.container.core.session_manager import SessionNotFoundError

        mock_session_manager.get_session.side_effect = SessionNotFoundError("Session not found")

        files = {"files": ("test.txt", BytesIO(b"Hello"), "text/plain")}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/nonexistent-session/upload",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_with_path_traversal_attempt(
        self, mock_session_manager, mock_container_manager
    ):
        """Test upload rejects path traversal attempts."""
        files = {"files": ("test.txt", BytesIO(b"Hello"), "text/plain")}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/test-session/upload?target_path=../etc",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        assert response.status_code == 400
        assert "traversal" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_dangerous_filename(self, mock_session_manager, mock_container_manager):
        """Test upload sanitizes dangerous filenames."""
        files = {"files": ("test;rm -rf /.txt", BytesIO(b"Hello"), "text/plain")}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/files/test-session/upload",
                headers={"Authorization": "Bearer test-api-key"},
                files=files,
            )

        # Should succeed but with sanitized filename
        assert response.status_code == 200

        # Verify the provider was called with sanitized filename
        call_args = mock_container_manager.provider.upload_files.call_args
        uploaded_files = call_args[0][1]  # files argument
        assert uploaded_files[0]["safe_name"] != "test;rm -rf /.txt"
        assert ";" not in uploaded_files[0]["safe_name"]

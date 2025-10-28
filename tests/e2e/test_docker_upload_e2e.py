"""End-to-end tests for Docker provider file upload functionality.

These tests use real Docker containers to verify the complete upload flow.
They require Docker to be running and will be skipped if Docker is unavailable.
"""

import pytest
import docker

from agcluster.container.core.providers.docker_provider import DockerProvider


# Skip all tests in this module if Docker is not available
pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def docker_available():
    """Check if Docker is available."""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        pytest.skip("Docker is not available")


@pytest.fixture
def docker_provider(docker_available):
    """Create a real DockerProvider instance."""
    return DockerProvider()


@pytest.fixture
async def test_container(docker_provider):
    """
    Create a real test container for upload testing.

    Uses alpine image with sleep to keep container running.
    Creates /workspace directory for testing.
    """
    container = None
    try:
        # Use alpine for lightweight testing
        container = docker_provider.docker_client.containers.run(
            "alpine:latest",
            command="sh -c 'mkdir -p /workspace && sleep 3600'",
            detach=True,
            remove=False,
            mem_limit="256m",
        )

        # Wait for container to be ready
        container.reload()
        assert container.status == "running"

        yield container

    finally:
        # Cleanup
        if container:
            try:
                container.stop(timeout=1)
                container.remove()
            except Exception as e:
                print(f"Error cleaning up container: {e}")


@pytest.mark.asyncio
class TestDockerUploadE2E:
    """End-to-end tests for Docker provider file upload."""

    async def test_upload_single_file_to_workspace(self, docker_provider, test_container):
        """Test uploading a single file to /workspace."""
        # Prepare test file
        files = [
            {
                "original_name": "test.txt",
                "safe_name": "test.txt",
                "content": b"Hello from e2e test!",
                "size": 20,
            }
        ]

        # Upload file
        uploaded = await docker_provider.upload_files(
            container_id=test_container.id,
            files=files,
            target_path="/workspace",
            overwrite=False,
        )

        # Verify upload was reported as successful
        assert uploaded == ["test.txt"]

        # Verify file exists in container
        exit_code, output = test_container.exec_run("ls /workspace/test.txt")
        assert exit_code == 0, f"File not found: {output}"

        # Verify file contents
        exit_code, output = test_container.exec_run("cat /workspace/test.txt")
        assert exit_code == 0
        assert output.decode().strip() == "Hello from e2e test!"

        # Verify file permissions (should be 0644)
        exit_code, output = test_container.exec_run("stat -c '%a' /workspace/test.txt")
        assert exit_code == 0
        permissions = output.decode().strip()
        assert permissions == "644", f"Expected 644 permissions, got {permissions}"

    async def test_upload_multiple_files(self, docker_provider, test_container):
        """Test uploading multiple files at once."""
        files = [
            {
                "original_name": "file1.txt",
                "safe_name": "file1.txt",
                "content": b"Content of file 1",
                "size": 17,
            },
            {
                "original_name": "file2.py",
                "safe_name": "file2.py",
                "content": b"print('Hello from file 2')",
                "size": 26,
            },
            {
                "original_name": "data.json",
                "safe_name": "data.json",
                "content": b'{"key": "value", "number": 42}',
                "size": 31,
            },
        ]

        # Upload files
        uploaded = await docker_provider.upload_files(
            container_id=test_container.id,
            files=files,
            target_path="/workspace",
            overwrite=False,
        )

        # Verify all files reported as uploaded
        assert set(uploaded) == {"file1.txt", "file2.py", "data.json"}

        # Verify all files exist
        for file_info in files:
            exit_code, _ = test_container.exec_run(f"ls /workspace/{file_info['safe_name']}")
            assert exit_code == 0, f"File {file_info['safe_name']} not found"

            # Verify content
            exit_code, output = test_container.exec_run(f"cat /workspace/{file_info['safe_name']}")
            assert exit_code == 0
            assert output == file_info["content"]

    async def test_upload_to_subdirectory(self, docker_provider, test_container):
        """Test uploading files to a subdirectory."""
        # Create subdirectory first
        test_container.exec_run("mkdir -p /workspace/data")

        files = [
            {
                "original_name": "nested.txt",
                "safe_name": "nested.txt",
                "content": b"File in subdirectory",
                "size": 20,
            }
        ]

        # Upload to subdirectory
        uploaded = await docker_provider.upload_files(
            container_id=test_container.id,
            files=files,
            target_path="/workspace/data",
            overwrite=False,
        )

        assert uploaded == ["nested.txt"]

        # Verify file is in subdirectory
        exit_code, output = test_container.exec_run("cat /workspace/data/nested.txt")
        assert exit_code == 0
        assert output.decode().strip() == "File in subdirectory"

    async def test_upload_without_overwrite_fails_if_exists(self, docker_provider, test_container):
        """Test that upload fails when file exists and overwrite=False."""
        # Create a file first
        test_container.exec_run("sh -c 'echo existing > /workspace/existing.txt'")

        files = [
            {
                "original_name": "existing.txt",
                "safe_name": "existing.txt",
                "content": b"new content",
                "size": 11,
            }
        ]

        # Should raise HTTPException with 409 status
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await docker_provider.upload_files(
                container_id=test_container.id,
                files=files,
                target_path="/workspace",
                overwrite=False,
            )

        assert exc_info.value.status_code == 409
        assert "already exists" in str(exc_info.value.detail).lower()

        # Verify original file content unchanged
        exit_code, output = test_container.exec_run("cat /workspace/existing.txt")
        assert exit_code == 0
        assert output.decode().strip() == "existing"

    async def test_upload_with_overwrite_replaces_file(self, docker_provider, test_container):
        """Test that upload replaces file when overwrite=True."""
        # Create a file first
        test_container.exec_run("sh -c 'echo old > /workspace/replace.txt'")

        files = [
            {
                "original_name": "replace.txt",
                "safe_name": "replace.txt",
                "content": b"new content",
                "size": 11,
            }
        ]

        # Upload with overwrite
        uploaded = await docker_provider.upload_files(
            container_id=test_container.id,
            files=files,
            target_path="/workspace",
            overwrite=True,
        )

        assert uploaded == ["replace.txt"]

        # Verify file content was replaced
        exit_code, output = test_container.exec_run("cat /workspace/replace.txt")
        assert exit_code == 0
        assert output.decode().strip() == "new content"

    async def test_upload_binary_file(self, docker_provider, test_container):
        """Test uploading binary files (non-text content)."""
        # Create binary content (PNG header-like bytes)
        binary_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 100

        files = [
            {
                "original_name": "image.png",
                "safe_name": "image.png",
                "content": binary_content,
                "size": len(binary_content),
            }
        ]

        # Upload binary file
        uploaded = await docker_provider.upload_files(
            container_id=test_container.id,
            files=files,
            target_path="/workspace",
            overwrite=False,
        )

        assert uploaded == ["image.png"]

        # Verify file exists
        exit_code, _ = test_container.exec_run("ls /workspace/image.png")
        assert exit_code == 0

        # Verify file size matches
        exit_code, output = test_container.exec_run("stat -c '%s' /workspace/image.png")
        assert exit_code == 0
        file_size = int(output.decode().strip())
        assert file_size == len(binary_content)

    async def test_upload_large_file(self, docker_provider, test_container):
        """Test uploading a larger file (1MB)."""
        # Create 1MB of content
        large_content = b"x" * (1024 * 1024)  # 1MB

        files = [
            {
                "original_name": "large.bin",
                "safe_name": "large.bin",
                "content": large_content,
                "size": len(large_content),
            }
        ]

        # Upload large file
        uploaded = await docker_provider.upload_files(
            container_id=test_container.id,
            files=files,
            target_path="/workspace",
            overwrite=False,
        )

        assert uploaded == ["large.bin"]

        # Verify file size
        exit_code, output = test_container.exec_run("stat -c '%s' /workspace/large.bin")
        assert exit_code == 0
        file_size = int(output.decode().strip())
        assert file_size == len(large_content)

    async def test_upload_file_with_special_characters_sanitized(
        self, docker_provider, test_container
    ):
        """Test that filenames with special characters are sanitized."""
        files = [
            {
                "original_name": "test;rm -rf /.txt",  # Dangerous filename
                "safe_name": "test_rm -rf _.txt",  # Expected sanitized name
                "content": b"Safe content",
                "size": 12,
            }
        ]

        # Upload with dangerous filename (but safe_name is already sanitized)
        uploaded = await docker_provider.upload_files(
            container_id=test_container.id,
            files=files,
            target_path="/workspace",
            overwrite=False,
        )

        # Should upload with sanitized name
        assert uploaded == ["test_rm -rf _.txt"]

        # Verify file exists with sanitized name
        exit_code, _ = test_container.exec_run("ls '/workspace/test_rm -rf _.txt'")
        assert exit_code == 0

        # Verify dangerous filename doesn't exist
        exit_code, _ = test_container.exec_run("ls '/workspace/test;rm -rf /.txt'")
        assert exit_code != 0  # Should not exist

    async def test_upload_to_nonexistent_container_fails(self, docker_provider):
        """Test that upload to non-existent container fails gracefully."""
        from fastapi import HTTPException

        files = [
            {
                "original_name": "test.txt",
                "safe_name": "test.txt",
                "content": b"content",
                "size": 7,
            }
        ]

        with pytest.raises(HTTPException) as exc_info:
            await docker_provider.upload_files(
                container_id="nonexistent-container-id",
                files=files,
                target_path="/workspace",
                overwrite=False,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

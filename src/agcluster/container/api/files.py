"""
File management endpoints for accessing agent workspace files
Provides file listing, reading, and workspace download functionality
"""

import logging
import tempfile
import zipfile
import tarfile
import os
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Header, Depends, File, UploadFile, Query
from fastapi.responses import FileResponse

from agcluster.container.core.session_manager import session_manager, SessionNotFoundError
from agcluster.container.core.container_manager import container_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Zip bomb protection limits
MAX_WORKSPACE_SIZE = 1 * 1024 * 1024 * 1024  # 1GB
MAX_FILES = 10000

# File upload limits
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB per file
MAX_TOTAL_UPLOAD_SIZE = 200 * 1024 * 1024  # 200MB total per request
MAX_FILES_PER_UPLOAD = 50

# Allowed MIME types for uploads
ALLOWED_MIME_TYPES = {
    # Text files
    "text/plain",
    "text/csv",
    "text/markdown",
    "text/x-markdown",
    # Code files
    "text/x-python",
    "text/x-python-script",
    "application/x-python-code",
    "text/javascript",
    "application/javascript",
    "application/x-javascript",
    "text/typescript",
    "application/typescript",
    "application/json",
    "text/x-java-source",
    "text/x-c",
    "text/x-c++",
    "text/x-rust",
    "text/x-go",
    # Documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # Images
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    # Archives
    "application/zip",
    "application/x-zip-compressed",
    "application/x-tar",
    "application/gzip",
    "application/x-gzip",
    # Data files
    "application/x-sqlite3",
    "text/xml",
    "application/xml",
    # Generic
    "application/octet-stream",  # Allow generic binary with filename check
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent security issues.

    Removes path separators, dangerous characters, and prevents hidden files.

    Args:
        filename: Original filename from upload

    Returns:
        Sanitized safe filename

    Raises:
        HTTPException: If filename is empty or invalid after sanitization
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    # Get basename to remove any path components
    name = os.path.basename(filename)

    # Remove dangerous characters (keep alphanumeric, spaces, hyphens, dots, underscores)
    name = re.sub(r"[^\w\s\-\.]", "_", name)

    # Prevent hidden files and shell command injection
    if name.startswith(".") or name.startswith("-"):
        name = "_" + name[1:]

    # Limit length
    if len(name) > 255:
        # Preserve extension if possible
        parts = name.rsplit(".", 1)
        if len(parts) == 2:
            name = parts[0][:250] + "." + parts[1]
        else:
            name = name[:255]

    # Ensure we still have a valid filename
    if not name or name in [".", ".."]:
        raise HTTPException(status_code=400, detail="Invalid filename")

    return name


def validate_file_type(file: UploadFile):
    """
    Validate file MIME type.

    Args:
        file: Uploaded file

    Raises:
        HTTPException: If file type is not allowed
    """
    content_type = file.content_type or "application/octet-stream"

    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed. "
            f"Allowed types: text, code, documents, images, archives, data files",
        )


def validate_workspace_path(user_path: str) -> Path:
    """
    Validate and normalize a user-provided path to ensure it stays within /workspace.

    Prevents path traversal attacks using .. or absolute paths.

    Args:
        user_path: User-provided file path

    Returns:
        Validated absolute Path object within /workspace

    Raises:
        HTTPException: If path attempts traversal or is invalid
    """
    # Remove any leading/trailing whitespace and slashes
    user_path = user_path.strip().lstrip("/")

    # Reject obviously malicious patterns
    if ".." in user_path:
        raise HTTPException(status_code=400, detail="Invalid path: traversal detected")

    if user_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path: absolute paths not allowed")

    # Construct the full path
    workspace = Path("/workspace")
    requested_path = workspace / user_path

    # Resolve to absolute path (follows symlinks and normalizes)
    try:
        resolved_path = requested_path.resolve()
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

    # Verify the resolved path is within workspace
    try:
        resolved_path.relative_to(workspace)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path outside workspace")

    return resolved_path


async def verify_session_access(
    session_id: str, authorization: Optional[str] = Header(None)
) -> str:
    """
    Verify the request has valid API key and owns the session.

    Prevents unauthorized access to other users' session files.

    Args:
        session_id: Session ID from path parameter
        authorization: Authorization header with Bearer token

    Returns:
        Validated API key

    Raises:
        HTTPException: 401 if no auth, 403 if wrong session owner, 404 if session not found
    """
    # Extract API key from Authorization header
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header format. Expected: Bearer <token>"
        )

    api_key = parts[1]

    # Get session
    try:
        agent_container = await session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Check if this API key owns this session
    # Get api_key_hash from container metadata
    api_key_hash = agent_container.container_info.metadata.get("api_key_hash")

    if not api_key_hash:
        # Legacy session without api_key_hash - log warning but allow access
        # This maintains backward compatibility
        logger.warning(
            f"Session {session_id} has no api_key_hash metadata. "
            "This is a legacy session. Consider recreating it."
        )
        return api_key

    # Verify ownership
    provided_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    if api_key_hash != provided_key_hash:
        raise HTTPException(status_code=403, detail="Access denied: you do not own this session")

    return api_key


def build_file_tree(paths: List[str]) -> Dict[str, Any]:
    """Convert flat path list to nested tree structure (legacy, kept for compatibility)"""
    tree = {"name": "workspace", "type": "directory", "path": "/", "children": []}

    for path in paths:
        if not path or path == "/workspace":
            continue

        # Remove /workspace prefix and split into parts
        relative_path = path.replace("/workspace/", "").replace("/workspace", "")
        if not relative_path:
            continue

        parts = relative_path.split("/")
        current = tree

        for i, part in enumerate(parts):
            if not part:  # Skip empty parts
                continue

            # Find or create node
            existing = next((c for c in current.get("children", []) if c["name"] == part), None)

            if existing:
                current = existing
            else:
                # Build full path from root
                full_path = "/".join(parts[: i + 1])
                is_file = i == len(parts) - 1 and "." in part

                node = {"name": part, "type": "file" if is_file else "directory", "path": full_path}

                if not is_file:
                    node["children"] = []

                current.setdefault("children", []).append(node)
                current = node

    return tree


def build_file_tree_with_types(typed_paths: List[tuple]) -> Dict[str, Any]:
    """
    Convert flat path list with type information to nested tree structure.

    Args:
        typed_paths: List of (type_marker, path) tuples where type_marker is 'f' or 'd'

    Returns:
        Tree structure with accurate file/directory type information
    """
    tree = {"name": "workspace", "type": "directory", "path": "/", "children": []}

    # Create a map of paths to their types
    path_types = {path: type_marker for type_marker, path in typed_paths}

    for type_marker, path in typed_paths:
        if not path or path == "/workspace":
            continue

        # Remove /workspace prefix and split into parts
        relative_path = path.replace("/workspace/", "").replace("/workspace", "")
        if not relative_path:
            continue

        parts = relative_path.split("/")
        current = tree

        for i, part in enumerate(parts):
            if not part:  # Skip empty parts
                continue

            # Find or create node
            existing = next((c for c in current.get("children", []) if c["name"] == part), None)

            if existing:
                current = existing
            else:
                # Build full path from root
                full_path = "/".join(parts[: i + 1])

                # Determine if this is a file or directory based on actual type
                # Check if this exact path exists in our typed_paths
                full_abs_path = f"/workspace/{full_path}"
                is_file = path_types.get(full_abs_path) == "f"

                node = {"name": part, "type": "file" if is_file else "directory", "path": full_path}

                if not is_file:
                    node["children"] = []

                current.setdefault("children", []).append(node)
                current = node

    return tree


@router.get("/api/files/{session_id}")
async def list_workspace_files(session_id: str, api_key: str = Depends(verify_session_access)):
    """
    List all files in container's /workspace directory

    Requires valid Authorization header matching the session owner.

    Returns tree structure with file metadata
    """
    try:
        container = await session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        # Get Docker container
        docker_container = container_manager.provider.docker_client.containers.get(
            container.container_id
        )

        # Execute find command with explicit type markers
        # Output format: <type>:<path> where type is 'f' for file, 'd' for directory
        exec_result = docker_container.exec_run(
            "sh -c \"find /workspace -type f -exec echo 'f:{}' \\; -o -type d -exec echo 'd:{}' \\;\"",
            stdout=True,
            stderr=True,
        )

        if exec_result.exit_code != 0:
            error_msg = exec_result.output.decode() if exec_result.output else "Unknown error"
            logger.error(f"Failed to list files: {error_msg}")
            raise HTTPException(status_code=500, detail="Failed to list files")

        # Parse output with type information
        output = exec_result.output.decode().strip()
        lines = output.split("\n") if output else []

        # Parse lines into (type, path) tuples
        typed_paths = []
        for line in lines:
            if not line or ":" not in line:
                continue
            type_marker, path = line.split(":", 1)
            typed_paths.append((type_marker, path))

        # Build tree structure with correct type information
        tree = build_file_tree_with_types(typed_paths)

        # Count files (type_marker == 'f')
        file_count = len([t for t, p in typed_paths if t == "f"])

        return {
            "root": "/workspace",
            "tree": tree,
            "total_files": file_count,
            "total_items": len(typed_paths),
        }

    except Exception as e:
        logger.error(f"Error listing workspace files for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/api/files/{session_id}/{path:path}/download")
async def download_file(session_id: str, path: str, api_key: str = Depends(verify_session_access)):
    """
    Download a specific file from workspace (supports binary files)

    Requires valid Authorization header matching the session owner.
    Path is validated to prevent directory traversal attacks.
    """
    # Validate path to prevent traversal
    validated_path = validate_workspace_path(path)

    try:
        container = await session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        # Get Docker container
        docker_container = container_manager.provider.docker_client.containers.get(
            container.container_id
        )

        # Read file as raw bytes using validated path
        # Use array form to avoid shell injection
        exec_result = docker_container.exec_run(
            ["cat", str(validated_path)], stdout=True, stderr=True
        )

        if exec_result.exit_code != 0:
            error_msg = exec_result.output.decode() if exec_result.output else "File not found"
            raise HTTPException(status_code=404, detail=f"File not found: {error_msg}")

        # Return raw file content
        filename = Path(path).name
        from fastapi.responses import Response

        return Response(
            content=exec_result.output,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {path} for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.get("/api/files/{session_id}/{path:path}")
async def get_file_content(
    session_id: str, path: str, raw: bool = False, api_key: str = Depends(verify_session_access)
):
    """
    Get content of specific file from workspace

    Requires valid Authorization header matching the session owner.
    Path is validated to prevent directory traversal attacks.

    Args:
        session_id: Session identifier
        path: File path relative to /workspace
        raw: If True, return raw binary data (for images/binary files)
    """
    # Validate path to prevent traversal
    validated_path = validate_workspace_path(path)

    try:
        container = await session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        # Get Docker container
        docker_container = container_manager.provider.docker_client.containers.get(
            container.container_id
        )

        # Read file content using validated path
        # Use array form to prevent command injection
        exec_result = docker_container.exec_run(
            ["cat", str(validated_path)], stdout=True, stderr=True
        )

        if exec_result.exit_code != 0:
            error_msg = exec_result.output.decode() if exec_result.output else "File not found"
            raise HTTPException(status_code=404, detail=f"File not found: {error_msg}")

        # Auto-detect image files by extension and return raw data
        from fastapi.responses import Response
        import mimetypes
        from pathlib import Path

        file_path = Path(path)
        file_ext = file_path.suffix.lower()
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"}

        # Auto-return raw image data for image files (even without ?raw=true)
        if file_ext in image_extensions:
            content_type, _ = mimetypes.guess_type(path)
            if content_type is None:
                content_type = "application/octet-stream"
            return Response(content=exec_result.output, media_type=content_type)

        # If raw=true, return binary data directly (for other binary files)
        if raw:
            # Guess content type from extension
            content_type, _ = mimetypes.guess_type(path)
            if content_type is None:
                content_type = "application/octet-stream"

            return Response(content=exec_result.output, media_type=content_type)

        # Try to decode as UTF-8, detect binary files
        try:
            content = exec_result.output.decode("utf-8")
        except UnicodeDecodeError:
            # Binary file detected - return download info instead of error
            file_size = len(exec_result.output)
            content_type, _ = mimetypes.guess_type(path)

            return {
                "type": "binary",
                "name": Path(path).name,
                "path": path,
                "size": file_size,
                "content_type": content_type or "application/octet-stream",
                "message": "This is a binary file and cannot be previewed as text.",
                "download_url": f"/api/files/{session_id}/{path}?raw=true",
            }

        # Detect language from extension
        ext = Path(path).suffix.lstrip(".")
        language_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "tsx": "typescriptreact",
            "jsx": "javascriptreact",
            "json": "json",
            "md": "markdown",
            "yaml": "yaml",
            "yml": "yaml",
            "sh": "shell",
            "bash": "shell",
            "txt": "plaintext",
            "log": "plaintext",
            "env": "plaintext",
            "toml": "toml",
            "ini": "ini",
            "conf": "plaintext",
            "html": "html",
            "css": "css",
            "scss": "scss",
            "sql": "sql",
            "rs": "rust",
            "go": "go",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
            "h": "cpp",
            "hpp": "cpp",
        }

        return {
            "path": path,
            "content": content,
            "language": language_map.get(ext, "plaintext"),
            "size_bytes": len(content.encode()),
            "lines": content.count("\n") + 1,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file {path} for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.post("/api/files/{session_id}/download")
async def download_workspace(session_id: str, api_key: str = Depends(verify_session_access)):
    """
    Generate and download ZIP of entire workspace

    Requires valid Authorization header matching the session owner.
    Includes zip bomb protection with size and file count limits.
    """
    try:
        container = await session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        # Get Docker container
        docker_container = container_manager.provider.docker_client.containers.get(
            container.container_id
        )

        # Create temp file for ZIP (don't delete immediately)
        zip_fd, zip_path = tempfile.mkstemp(suffix=".zip", prefix=f"workspace_{session_id[:8]}_")

        try:
            # Create temp directory for extraction
            tmpdir = tempfile.mkdtemp()

            try:
                # Get tar archive from container
                bits, stat = docker_container.get_archive("/workspace")

                # Check workspace size (zip bomb protection)
                workspace_size = stat.get("size", 0)
                if workspace_size > MAX_WORKSPACE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Workspace too large ({workspace_size / 1e9:.2f}GB). "
                        f"Maximum allowed: {MAX_WORKSPACE_SIZE / 1e9:.0f}GB",
                    )

                # Save tar to disk
                tar_path = os.path.join(tmpdir, "workspace.tar")
                with open(tar_path, "wb") as f:
                    for chunk in bits:
                        f.write(chunk)

                # Extract tar and create ZIP with file count protection
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    # Extract tar contents
                    with tarfile.open(tar_path) as tar:
                        tar.extractall(tmpdir)

                    # Add all files to zip (excluding the workspace root folder itself)
                    workspace_dir = os.path.join(tmpdir, "workspace")
                    if os.path.exists(workspace_dir):
                        file_count = 0
                        for root, dirs, files in os.walk(workspace_dir):
                            for file in files:
                                # Check file count limit (zip bomb protection)
                                file_count += 1
                                if file_count > MAX_FILES:
                                    raise HTTPException(
                                        status_code=413,
                                        detail=f"Too many files in workspace ({file_count}). "
                                        f"Maximum allowed: {MAX_FILES}",
                                    )

                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, workspace_dir)
                                zipf.write(file_path, arcname)
            finally:
                # Clean up temp extraction directory
                import shutil

                shutil.rmtree(tmpdir, ignore_errors=True)
                os.close(zip_fd)

            # Return ZIP file (FastAPI will handle cleanup via background task)
            return FileResponse(
                zip_path,
                media_type="application/zip",
                filename=f"workspace_{session_id[:8]}.zip",
                headers={
                    "Content-Disposition": f"attachment; filename=workspace_{session_id[:8]}.zip"
                },
                background=lambda: os.unlink(zip_path),  # Clean up after sending
            )
        except Exception as e:
            # If error, clean up zip file
            try:
                os.close(zip_fd)
                os.unlink(zip_path)
            except Exception:
                pass
            raise e

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workspace ZIP for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create workspace archive: {str(e)}")


@router.post("/api/files/{session_id}/upload")
async def upload_files(
    session_id: str,
    files: List[UploadFile] = File(...),
    target_path: str = Query("", description="Target directory (relative to /workspace)"),
    overwrite: bool = Query(False, description="Overwrite existing files"),
    api_key: str = Depends(verify_session_access),
):
    """
    Upload files to container's /workspace directory.

    Requires valid Authorization header matching the session owner.
    Files are validated for type, size, and filename safety.

    Args:
        session_id: Session identifier
        files: List of files to upload
        target_path: Target directory relative to /workspace (default: root)
        overwrite: Whether to overwrite existing files (default: False)

    Returns:
        Dict with uploaded filenames and metadata

    Security:
        - File size limit: 50MB per file, 200MB total
        - MIME type validation
        - Filename sanitization
        - Path traversal protection
        - Session ownership validation
    """
    # Validate file count
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum: {MAX_FILES_PER_UPLOAD}, received: {len(files)}",
        )

    # Validate target path
    if target_path:
        validated_target = validate_workspace_path(target_path)
    else:
        validated_target = Path("/workspace")

    logger.info(
        f"Upload request for session {session_id}: {len(files)} files to {validated_target}"
    )

    try:
        container = await session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Validate files and prepare for upload
    total_size = 0
    files_to_upload = []

    for file in files:
        # Validate MIME type
        validate_file_type(file)

        # Sanitize filename
        safe_filename = sanitize_filename(file.filename)

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Validate individual file size
        if file_size > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File '{file.filename}' too large ({file_size / 1024 / 1024:.2f}MB). "
                f"Maximum: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB",
            )

        # Check total size
        total_size += file_size
        if total_size > MAX_TOTAL_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Total upload size too large ({total_size / 1024 / 1024:.2f}MB). "
                f"Maximum: {MAX_TOTAL_UPLOAD_SIZE / 1024 / 1024:.0f}MB",
            )

        files_to_upload.append(
            {
                "original_name": file.filename,
                "safe_name": safe_filename,
                "content": content,
                "size": file_size,
            }
        )

    # Use provider to upload files
    try:
        uploaded_files = await container_manager.provider.upload_files(
            container.container_id, files_to_upload, str(validated_target), overwrite
        )

        logger.info(f"Successfully uploaded {len(uploaded_files)} files to session {session_id}")

        return {
            "session_id": session_id,
            "target_path": str(validated_target),
            "uploaded": uploaded_files,
            "total_files": len(uploaded_files),
            "total_size_bytes": total_size,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading files to session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")

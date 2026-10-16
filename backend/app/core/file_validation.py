"""
File validation utilities for secure file uploads.
"""

import magic
import os
import re
from pathlib import Path
from typing import Optional, Tuple
from fastapi import HTTPException, status
import mimetypes


class FileValidator:
    """Validator for uploaded files."""

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        'txt', 'csv', 'json', 'xml', 'fasta', 'fastq', 'bed', 'gff', 'gtf',
        'bam', 'sam', 'vcf', 'xls', 'xlsx', 'pdf', 'doc', 'docx', 'jpg', 'jpeg',
        'png', 'gif', 'bmp', 'tiff', 'zip', 'tar', 'gz', 'bz2', '7z'
    }

    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        'text/plain', 'text/csv', 'application/json', 'application/xml',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel', 'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff',
        'application/zip', 'application/x-tar', 'application/gzip',
        'application/x-bzip2', 'application/x-7z-compressed'
    }

    # Max file size in bytes (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """Validate file extension."""
        if not filename:
            return False

        # Get extension
        ext = Path(filename).suffix.lower()[1:]  # Remove the dot
        return ext in FileValidator.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_file_size(file_content: bytes) -> bool:
        """Validate file size."""
        return len(file_content) <= FileValidator.MAX_FILE_SIZE

    @staticmethod
    def validate_mime_type(file_content: bytes, filename: str = "") -> Tuple[bool, str]:
        """Validate MIME type using magic library."""
        try:
            # Use magic to detect MIME type
            mime_type = magic.from_buffer(file_content, mime=True)

            # Validate against allowed MIME types
            if mime_type in FileValidator.ALLOWED_MIME_TYPES:
                return True, mime_type

            # Special handling for some cases
            if mime_type.startswith('text/') and not mime_type.startswith('text/html'):
                return True, mime_type

            # If we can't determine MIME type from content, check extension as fallback
            if filename:
                _, ext = os.path.splitext(filename)
                ext = ext.lower()[1:]  # Remove the dot
                mime_type_from_ext = mimetypes.types_map.get('.' + ext, '')
                if mime_type_from_ext in FileValidator.ALLOWED_MIME_TYPES:
                    return True, mime_type_from_ext

            return False, mime_type
        except Exception:
            # If magic fails, fall back to extension-based validation
            if filename:
                _, ext = os.path.splitext(filename)
                ext = ext.lower()[1:]  # Remove the dot
                mime_type_from_ext = mimetypes.types_map.get('.' + ext, '')
                if mime_type_from_ext in FileValidator.ALLOWED_MIME_TYPES:
                    return True, mime_type_from_ext
            return False, "unknown"

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal and other issues."""
        if not filename:
            return ""

        # Remove path components
        filename = os.path.basename(filename)

        # Remove dangerous characters
        filename = re.sub(r'[^\w\-\.]', '_', filename)

        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext

        return filename

    @staticmethod
    def validate_uploaded_file(file_content: bytes, filename: str = "") -> dict:
        """
        Validate uploaded file completely.

        Returns:
            dict: {
                'valid': bool,
                'filename': str,
                'mime_type': str,
                'size': int,
                'error': str (if invalid)
            }
        """
        result = {
            'valid': False,
            'filename': '',
            'mime_type': '',
            'size': len(file_content),
            'error': ''
        }

        # Validate file size
        if not FileValidator.validate_file_size(file_content):
            result['error'] = f"File size exceeds maximum limit of {FileValidator.MAX_FILE_SIZE} bytes"
            return result

        # Sanitize filename
        sanitized_filename = FileValidator.sanitize_filename(filename)
        result['filename'] = sanitized_filename

        # Validate file extension
        if filename and not FileValidator.validate_file_extension(filename):
            result['error'] = f"File extension not allowed. Allowed extensions: {FileValidator.ALLOWED_EXTENSIONS}"
            return result

        # Validate MIME type
        is_valid, mime_type = FileValidator.validate_mime_type(file_content, filename)
        result['mime_type'] = mime_type

        if not is_valid:
            result['error'] = f"File MIME type not allowed: {mime_type}"
            return result

        result['valid'] = True
        return result


# Usage example in a file upload endpoint
async def secure_file_upload(file_content: bytes, filename: str) -> dict:
    """
    Secure file upload validation.

    Args:
        file_content: bytes of the uploaded file
        filename: original filename from upload

    Returns:
        dict: validation result

    Raises:
        HTTPException: if validation fails
    """
    validation_result = FileValidator.validate_uploaded_file(file_content, filename)

    if not validation_result['valid']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File validation failed: {validation_result['error']}"
        )

    return validation_result
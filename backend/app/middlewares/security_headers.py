from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.settings.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Add CSP header (Content Security Policy) - can be customized
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "media-src 'self'",
            "object-src 'none'",
            "child-src 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'"
        ]

        if settings.DEBUG:
            # In debug mode, allow more relaxed CSP for development
            csp_directives = [
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob:",
                "font-src 'self' data:",
                "connect-src 'self' http://localhost:* ws://localhost:*",
                "media-src 'self'",
                "object-src 'none'",
                "child-src 'self'",
                "frame-ancestors 'self'",
                "form-action 'self'",
                "base-uri 'self'"
            ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Add Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Add Permissions Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


class FileUploadSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware to handle secure file uploads."""

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        'txt', 'csv', 'json', 'xml', 'fasta', 'fastq', 'bed', 'gff', 'gtf',
        'bam', 'sam', 'vcf', 'xls', 'xlsx', 'pdf', 'doc', 'docx', 'jpg', 'jpeg',
        'png', 'gif', 'bmp', 'tiff', 'zip', 'tar', 'gz'
    }

    # Max file size in bytes (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024

    async def dispatch(self, request: Request, call_next):
        # If this is a file upload request, validate it
        if request.method == "POST" and request.headers.get("content-type", "").startswith("multipart/form-data"):
            # In a real implementation, you would validate the uploaded files here
            # This is a simplified version - in practice you'd check:
            # - File size limits
            # - File type validation (magic numbers)
            # - Filename sanitization
            # - Storage isolation
            pass

        response = await call_next(request)
        return response
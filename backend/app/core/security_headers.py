from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
import re


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


class SQLInjectionProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware to protect against SQL injection attacks."""

    # Common SQL injection patterns
    sql_patterns = [
        r"(?i)\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b",
        r"(?i)--.*$",
        r"(?i)/\*.*?\*/",
        r"(?i)'(.*?)'",
        r"(?i)(?:OR|AND)\s+1=1",
        r"(?i)(?:OR|AND)\s+1=1--",
        r"(?i)(?:OR|AND)\s+1=1/\*.*?\*/",
    ]

    async def dispatch(self, request: Request, call_next):
        # Check query parameters for SQL injection patterns
        query_params = request.query_params
        for key, value in query_params.items():
            if self._contains_sql_injection(value):
                # Log potential SQL injection attempt
                print(f"Potential SQL injection detected in query param '{key}': {value}")
                # For production, you might want to block this request
                # For now, we'll let it pass but log it
                pass

        # Check request body for SQL injection patterns (if applicable)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8', errors='ignore')
                    if self._contains_sql_injection(body_str):
                        print(f"Potential SQL injection detected in request body: {body_str[:100]}...")
                        # Log and potentially block in production
                        pass
            except Exception:
                # If we can't read the body, continue normally
                pass

        response = await call_next(request)
        return response

    def _contains_sql_injection(self, text: str) -> bool:
        """Check if text contains SQL injection patterns."""
        if not text:
            return False

        text_lower = text.lower()
        for pattern in self.sql_patterns:
            if re.search(pattern, text_lower):
                return True
        return False


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
from typing import Any, Generic, List, Optional, TypeVar

from fastapi import Request
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """业务接口的统一成功体。"""

    code: int = 0
    message: str = "ok"
    request_id: Optional[str] = None
    data: Optional[T] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class ErrorResponse(BaseModel):
    """业务接口的统一错误体，与异常处理器返回的字段一致。"""

    code: int
    message: str
    request_id: str
    details: Any = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


COMMON_ERROR_RESPONSES: dict[int, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "未登录或令牌无效"},
    403: {"model": ErrorResponse, "description": "没有权限"},
    422: {"model": ErrorResponse, "description": "参数校验失败"},
}


def api_ok(
    request: Request,
    data: Optional[T] = None,
    message: str = "ok",
    code: int = 0,
) -> ApiResponse[T]:
    """组装成功响应，并带上当前请求 ID。"""
    request_id = getattr(request.state, "request_id", None)
    return ApiResponse(
        code=code,
        message=message,
        request_id=str(request_id) if request_id else None,
        data=data,
    )


class PageParams(BaseModel):
    """分页参数。page 从 1 开始，每页最多 100 条。"""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class PageResult(BaseModel, Generic[T]):
    """Pagination result model."""

    items: List[T]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
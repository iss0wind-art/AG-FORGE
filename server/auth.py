"""
인증 미들웨어 — auth.py
X-API-Key 헤더로 방부장 본인 여부를 확인한다.
환경변수 AG_FORGE_API_KEY가 설정되지 않으면 즉시 오류를 발생시킨다.
"""
from __future__ import annotations
import os
from fastapi import Header, HTTPException, status


def get_api_key() -> str:
    """환경변수에서 API 키를 가져온다. 미설정 시 즉시 오류."""
    key = os.environ.get("AG_FORGE_API_KEY", "")
    if not key:
        raise RuntimeError("AG_FORGE_API_KEY 환경변수가 설정되지 않았습니다.")
    return key


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """FastAPI dependency — API 키 검증."""
    expected = get_api_key()
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 API 키입니다.",
        )
    return x_api_key

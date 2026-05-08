"""
인페이스 출근 데이터 수집 — 기존 /api/reports/inface-auto 내부 호출 방식.
새 스크레이퍼를 중복 구현하지 않고, Next.js 서버에 이미 구축된 V5 엔진을 재사용한다.
"""
import os
import requests
from typing import Optional


NEXTJS_BASE = os.getenv("NEXTJS_BASE_URL", "http://localhost:3000")
INFACE_URL = os.getenv("INFACE_URL", "")  # 인페이스 엑셀 다운로드 URL (환경변수)


def fetch_today_attendance(date: str, inface_url: Optional[str] = None) -> list[dict]:
    """
    오늘 날짜 인페이스 출근 데이터를 반환한다.
    반환: [{ '성명': str, '공종': str, '팀명': str, ... }, ...]
    """
    url = inface_url or INFACE_URL
    if not url:
        raise ValueError("INFACE_URL 환경변수 또는 인수가 필요합니다.")

    response = requests.post(
        f"{NEXTJS_BASE}/api/reports/inface-auto",
        json={"url": url, "date": date},
        timeout=60,
    )
    response.raise_for_status()

    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"인페이스 수집 실패: {payload.get('error', '알 수 없는 오류')}")

    return payload.get("data", [])


def normalize_worker(raw: dict) -> dict:
    """인페이스 원본 행을 표준 형식으로 변환한다."""
    name = (raw.get("성명") or raw.get("이름") or raw.get("Name") or "").strip()
    trade = (raw.get("공종") or raw.get("직종") or raw.get("Trade") or "").strip()
    team = (raw.get("팀명") or raw.get("팀") or raw.get("소속") or trade).strip()

    return {
        "worker_name": name,
        "job_type": trade,
        "team": team,
        "manday": float(raw.get("공수") or raw.get("Manday") or 1.0),
        "source": "inface",
    }

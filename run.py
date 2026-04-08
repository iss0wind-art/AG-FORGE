"""
AG-Forge 기동 스크립트 — run.py
ngrok 터널 자동 개통 + FastAPI 서버 실행.

사용법:
  python run.py            # 로컬 실행 (http://localhost:8000)
  python run.py --tunnel   # ngrok 터널 개통 (외부 접속 가능)
  python run.py --port 9000
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from pyngrok import ngrok, conf

load_dotenv()

REQUIRED_ENV = ["AG_FORGE_API_KEY"]


def validate_env() -> list[str]:
    """필수 환경변수가 설정되었는지 확인한다. 누락된 변수 목록을 반환한다."""
    return [key for key in REQUIRED_ENV if not os.environ.get(key)]


def open_ngrok_tunnel(port: int) -> str:
    """ngrok 터널을 열고 공개 URL을 반환한다."""
    token = os.environ.get("NGROK_AUTHTOKEN", "")
    if token:
        conf.get_default().auth_token = token

    tunnel = ngrok.connect(port, "http")
    return tunnel.public_url


def print_access_info(url: str, port: int) -> None:
    """접속 정보를 출력한다."""
    print("\n" + "=" * 50)
    print("  AG-Forge Brain 서버가 시작되었습니다")
    print("=" * 50)
    print(f"  로컬:    http://localhost:{port}")
    if url != f"http://localhost:{port}":
        print(f"  외부:    {url}")
        print(f"  모바일:  {url}")
    print("=" * 50)
    print("  API 키를 입력하여 뇌에 접속하세요")
    print("  종료: Ctrl+C")
    print("=" * 50 + "\n")


def start_server(host: str, port: int) -> None:
    """uvicorn으로 FastAPI 서버를 시작한다."""
    import uvicorn
    uvicorn.run(
        "server.api:app",
        host=host,
        port=port,
        reload=False,
        log_level="warning",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="AG-Forge Brain Server")
    parser.add_argument("--tunnel", action="store_true", help="ngrok 터널 개통")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args = parser.parse_args()

    # 환경변수 검증
    missing = validate_env()
    if missing:
        print(f"오류: 필수 환경변수가 설정되지 않았습니다: {', '.join(missing)}")
        print("  .env.example을 복사하여 .env 파일을 생성하세요")
        return 1

    # 터널 개통
    public_url = f"http://localhost:{args.port}"
    if args.tunnel:
        try:
            public_url = open_ngrok_tunnel(args.port)
            print(f"터널 개통: {public_url}")
        except Exception as e:
            print(f"ngrok 터널 실패: {e}")
            print("로컬 모드로 계속합니다.")

    print_access_info(public_url, args.port)
    start_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())

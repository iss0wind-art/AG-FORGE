"""
Physis 기동 스크립트 — run.py
ZROK 터널 자동 개통 + FastAPI 서버 실행.

사용법:
  python run.py            # 로컬 실행 (http://localhost:8000)
  python run.py --zrok     # ZROK 터널 개통 (외부 접속 가능)
  python run.py --port 9000
  python run.py --zrok --port 9000

사전 요구:
  ZROK 설치: https://docs.zrok.io/
  ZROK 인증: zrok account create 또는 zrok account login
"""
from __future__ import annotations
import argparse
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV = ["AG_FORGE_API_KEY"]


def validate_env() -> list[str]:
    """필수 환경변수가 설정되었는지 확인한다. 누락된 변수 목록을 반환한다."""
    return [key for key in REQUIRED_ENV if not os.environ.get(key)]


def open_zrok_tunnel(port: int) -> str:
    """
    ZROK 터널을 열고 공개 URL을 반환한다.
    
    zrok이 설치되고 인증되어 있어야 함.
    """
    try:
        # ZROK 상태 확인
        status = subprocess.run(["zrok", "status"], capture_output=True, text=True, timeout=5)
        if status.returncode != 0:
            raise RuntimeError("ZROK 미인증: zrok account login 실행 필요")
        
        # ZROK 터널 개통
        result = subprocess.run(
            ["zrok", "share", "http", str(port)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"ZROK 터널 실패: {result.stderr}")
        
        # 출력에서 공개 URL 추출
        # 일반적으로 형식: "Access server at: https://xxxxx.share.zrok.io"
        for line in result.stdout.splitlines():
            if "https://" in line and "zrok.io" in line:
                # URL 추출 (예: "Access server at: https://xxxxx.share.zrok.io" → "https://xxxxx.share.zrok.io")
                url = line.split()[-1].strip()
                return url
        
        # URL을 못 찾으면 stderr도 확인
        raise RuntimeError(f"ZROK 공개 URL을 찾을 수 없음\n{result.stdout}\n{result.stderr}")
        
    except FileNotFoundError:
        raise RuntimeError("ZROK 명령어를 찾을 수 없습니다. https://docs.zrok.io/ 에서 설치하세요.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("ZROK 터널 타임아웃")
    except Exception as e:
        raise RuntimeError(f"ZROK 오류: {e}")


def print_access_info(url: str, port: int) -> None:
    """접속 정보를 출력한다."""
    print("\n" + "=" * 60)
    print("  🧠 Physis 독립 뇌 서버 시작됨")
    print("=" * 60)
    print(f"  로컬:    http://localhost:{port}")
    if url != f"http://localhost:{port}":
        print(f"  공개:    {url}")
        print(f"  상태:    ✅ ZROK 터널 활성화")
    else:
        print(f"  상태:    로컬 모드 (외부 접속 불가)")
    print("=" * 60)
    print("  API 키를 입력하여 Physis에 접속하세요")
    print("  또는 Claude Code에서 'Physis야 ...' 로 호출")
    print("  종료: Ctrl+C")
    print("=" * 60 + "\n")


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
    parser = argparse.ArgumentParser(description="Physis 독립 뇌 서버")
    parser.add_argument("--zrok", action="store_true", help="ZROK 터널 개통 (외부 접속 가능)")
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
    if args.zrok:
        try:
            public_url = open_zrok_tunnel(args.port)
            print(f"✅ ZROK 터널 개통: {public_url}")
        except Exception as e:
            print(f"❌ ZROK 터널 실패: {e}")
            print("   로컬 모드로 계속합니다.")
            print("   (ZROK 설치 & 인증: https://docs.zrok.io/)\n")

    print_access_info(public_url, args.port)
    start_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())

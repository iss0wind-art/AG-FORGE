"""
피지수(Physis) 기동 스크립트 — run.py
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
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV = ["AG_FORGE_API_KEY"]


def validate_env() -> list[str]:
    """필수 환경변수가 설정되었는지 확인한다. 누락된 변수 목록을 반환한다."""
    return [key for key in REQUIRED_ENV if not os.environ.get(key)]


def get_zrok_command() -> str:
    """zrok 명령의 경로를 반환한다. PATH에 없으면 사용자 문서 폴더를 확인한다."""
    import shutil
    cmd = shutil.which("zrok")
    if cmd:
        return cmd
    
    # 사용자 문서 및 전용 폴더 확인 (방부장님 환경 전용)
    fallbacks = [
        Path(os.environ.get("USERPROFILE", "C:/Users/USER")) / "Documents" / "zrok.exe",
        Path(os.environ.get("USERPROFILE", "C:/Users/USER")) / "zrok" / "bin" / "zrok2.exe"
    ]
    for fb in fallbacks:
        if fb.exists():
            return str(fb)
    
    return "zrok"  # 기본값으로 시도


def open_zrok_tunnel(port: int) -> subprocess.Popen:
    """
    ZROK 터널을 백그라운드에서 열고 프로세스 객체를 반환한다.
    """
    zrok_cmd = get_zrok_command()

    try:
        subprocess.run([zrok_cmd, "status"], capture_output=True, text=True, timeout=5, check=True)
    except FileNotFoundError:
        raise RuntimeError("ZROK 명령어를 찾을 수 없습니다")
    except subprocess.CalledProcessError:
        raise RuntimeError("ZROK 미인증")

    print(f"[Info] '{zrok_cmd}'를 통해 페이퍼 클립(터널) 가동 중...")

    process = subprocess.Popen(
        [zrok_cmd, "share", "public", f"http://localhost:{port}", "--headless"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    time.sleep(2)
    if process.poll() is not None:
        _, stderr = process.communicate()
        raise RuntimeError(f"ZROK 터널 실패: {stderr}")

    return process


def print_access_info(url: str, port: int, headless: bool = False) -> None:
    """접속 정보를 출력한다."""
    # Windows CP949 대응: 이모지 제거 또는 ASCII 문자로 대체
    mode_str = "Headless (API 전용)" if headless else "Full (UI 포함)"
    print("\n" + "=" * 60)
    print(f"  [Brain] 피지수(Physis) 독립 뇌 서버 시작됨 ({mode_str})")
    print("=" * 60)
    print(f"  로컬:    http://localhost:{port}")
    if url != f"http://localhost:{port}":
        print(f"  공개:    {url}")
        print(f"  상태:    [OK] ZROK 터널 활성화")
    else:
        print(f"  상태:    로컬 모드 (외부 접속 불가)")
    print("=" * 60)
    if headless:
        print("  UI가 비활성화되었습니다. API 엔드포인트를 사용하세요.")
    else:
        print("  API 키를 입력하여 피지수에 접속하세요")
        print("  또는 Claude Code에서 '피지수야 ...' 로 호출")
    print("  종료: Ctrl+C")
    print("=" * 60 + "\n")


def start_server(host: str, port: int) -> None:
    """uvicorn으로 FastAPI 서버를 시작한다."""
    import uvicorn
    # stdout 인코딩 강제 설정 시도 (Windows용)
    try:
        if sys.platform == "win32":
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

    uvicorn.run(
        "server.api:app",
        host=host,
        port=port,
        reload=False,
        log_level="warning",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="피지수(Physis) 독립 뇌 서버")
    parser.add_argument("--zrok", action="store_true", help="ZROK 터널 개통 (외부 접속 가능)")
    parser.add_argument("--headless", action="store_true", help="UI 없이 API 전용 모드로 실행")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args = parser.parse_args()

    if args.headless:
        os.environ["AG_FORGE_HEADLESS"] = "true"

    # 환경변수 검증
    missing = validate_env()
    if missing:
        print(f"오류: 필수 환경변수가 설정되지 않았습니다: {', '.join(missing)}")
        print("  .env.example을 복사하여 .env 파일을 생성하세요")
        return 1

    # 터널 가동 (비동기)
    tunnel_proc = None
    public_url = f"http://localhost:{args.port}"
    
    if args.zrok:
        try:
            tunnel_proc = open_zrok_tunnel(args.port)
            print(f"[OK] 페이퍼 클립(zrok) 백그라운드 가동 시작")
        except Exception as e:
            print(f"[Error] 페이퍼 클립 가동 실패: {e}")
            print("   로컬 모드로 계속합니다.\n")

    try:
        print_access_info(public_url, args.port, args.headless)
        start_server(args.host, args.port)
    finally:
        if tunnel_proc:
            print("[Info] 페이퍼 클립 종료 중...")
            tunnel_proc.terminate()
            
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[Exit] 사용자가 서버를 종료했습니다.")

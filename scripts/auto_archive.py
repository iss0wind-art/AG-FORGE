"""
자동 아카이빙 (Auto Archiving) — auto_archive.py
judgment.md의 방대한 로그를 정리하고 백업한다.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOG_PATH = ROOT / "judgment.md"
ARCHIVE_DIR = ROOT / "archive"

MAX_LOG_SIZE = 100 * 1024  # 100KB 초과 시 아카이빙 실행

def archive_logs():
    """로그 파일이 너무 크면 아카이빙을 수행한다."""
    if not LOG_PATH.exists():
        print("ℹ️ 아카이빙할 로그 파일이 없습니다.")
        return

    file_size = LOG_PATH.stat().st_size
    if file_size < MAX_LOG_SIZE:
        print(f"ℹ️ 로그 크기 적정 ({file_size/1024:.1f}KB). 아카이빙이 필요하지 않습니다.")
        return

    # 아카이브 디렉토리 생성
    ARCHIVE_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = ARCHIVE_DIR / f"judgment_backup_{timestamp}.md"
    
    # 현재 로그 백업 및 초기화
    print(f"🚀 로그 아카이빙 시작: {LOG_PATH.name} -> {archive_path.name}")
    shutil.copy(LOG_PATH, archive_path)
    
    # 헤더만 남기고 초기화
    header = "# Physis Judgment Log (판단 로그)\n\n_초기화됨._\n"
    LOG_PATH.write_text(header, encoding="utf-8")
    
    print("✅ 아카이빙 완료.")

if __name__ == "__main__":
    archive_logs()

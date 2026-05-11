import os
from pathlib import Path

def print_status():
    status_file = Path(__file__).parent.parent / "PHYSIS.md"
    if not status_file.exists():
        print("❌ PHYSIS.md 파일을 찾을 수 없습니다.")
        return

    print("\n" + "="*50)
    print("       📡 PHYSIS LIVE STATUS REPORT")
    print("="*50 + "\n")

    try:
        content = status_file.read_text(encoding="utf-8")
        print(content)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    print_status()

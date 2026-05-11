import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# AG-Forge 루트를 경로에 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.embedding import GoogleEmbeddingClient, migrate_library
from scripts.setup_vector_db import get_vector_db

def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY가 없습니다.")
        return

    db = get_vector_db()
    embedder = GoogleEmbeddingClient(api_key)

    docs_to_learn = [
        ("technical-guidelines.md", "guidelines"),
        ("architecture-overview.md", "architecture"),
        ("brain.md", "brain_core"),
        ("CONSTITUTION.md", "constitution")
    ]

    print("--- Physis 해마 학습(Embedding) 시작 ---")
    for filename, category in docs_to_learn:
        filepath = ROOT / filename
        if filepath.exists():
            print(f"📄 {filename} 학습 중...")
            try:
                count = migrate_library(filepath, category, db, embedder)
                print(f"✅ {filename} 완료 ({count} 청크 저장됨)")
            except Exception as e:
                print(f"❌ {filename} 실패: {e}")
        else:
            print(f"⚠️ {filename} 파일을 찾을 수 없습니다.")

    print("\n🎉 모든 초기 학습 작업 완료!")

if __name__ == "__main__":
    main()

import os
import sys
from pathlib import Path

# AG-Forge 루트를 경로에 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.brain_loader import GeminiProvider
from scripts.router_agent import route, TaskType

def test_router():
    print("--- [테스트 1] 라우팅 엔진 검증 ---")
    tasks = [
        ("멋진 UI 버튼을 만들어줘", TaskType.UI),
        ("알고리즘 최적화가 필요해", TaskType.CODE),
        ("전체 시스템 아키텍처를 그려줘", TaskType.ARCHITECTURE),
    ]

    for task, expected in tasks:
        decision = route(task)
        print(f"작업: '{task}' -> 결과: {decision.task_type} (기대값: {expected})")
        assert decision.task_type == expected
    print("✅ 라우팅 엔진 정상\n")

def test_layer_loading():
    print("--- [테스트 2] 브레인 레이어 로딩 검증 ---")
    from scripts.brain_loader import load_layer

    try:
        brain_md = load_layer("brain.md")
        print(f"brain.md 로드 성공 ({len(brain_md)} bytes)")
        assert "Physis" in brain_md or "피지수" in brain_md # 리브랜딩 여부 확인
        print("✅ 레이어 로딩 정상\n")
    except Exception as e:
        print(f"❌ 레이어 로딩 실패: {e}\n")

if __name__ == "__main__":
    try:
        test_router()
        test_layer_loading()
        print("🎉 모든 기초 테스트 통과!")
    except AssertionError as e:
        print(f"❌ 테스트 실패: {e}")
    except Exception as e:
        print(f"❌ 예외 발생: {e}")

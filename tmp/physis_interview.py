import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# AG-Forge 루트를 경로에 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.brain_loader import DeepSeekProvider, run

def interview():
    load_dotenv()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ DEEPSEEK_API_KEY가 없습니다.")
        return

    provider = DeepSeekProvider(api_key)
    # 딥시크 응답 안정성을 위해 컨텍스트 최적화 (가장 핵심적인 2개 레이어만 로드)
    from scripts.brain_loader import load_layer
    system_instruction = load_layer("brain.md")
    context_layers = [load_layer("technical-guidelines.md")]

    task = (
        "스케치업 객체 10,000개 전송 시 N+1 차단 및 0.1초 팝업을 위한 "
        "Zustand + Drizzle + JSON Chunking 결합 전략을 수립해줘."
    )

    print(f"🎤 [Physis 기술 면접 - DeepSeek 최적화 모드]")
    print(f"질문: {task}")
    print("-" * 50)
    
    try:
        # run() 내부의 전체 루프 대신, 직접 provider를 호출하여 결과 확인
        response = provider.generate(
            system_instruction=system_instruction,
            context_layers=context_layers,
            task=task,
            model="deepseek-chat",
            thinking_budget=1000
        )
        print(f"\n[Physis의 답변 - {response.model}]\n")
        print(response.text)
        print("-" * 50)
        print(f"토큰 사용량: {response.tokens_used}")
    except Exception as e:
        print(f"❌ 면접 진행 중 오류 발생: {e}")

if __name__ == "__main__":
    interview()

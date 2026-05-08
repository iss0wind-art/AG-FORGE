import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# AG-Forge 루트를 경로에 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.brain_loader import GeminiProvider, run
from scripts.agent_state import AgentState

def live_autonomous_test():
    load_dotenv()
    
    from scripts.brain_loader import DeepSeekProvider

    # DeepSeek 단독 모드 (용량 및 성능 안정성 우선)
    ds_key = os.environ.get("DEEPSEEK_API_KEY")
    if not ds_key:
        print("❌ DEEPSEEK_API_KEY가 없어 테스트를 진행할 수 없습니다.")
        return

    print("--- [Physis 자율 루프 라이브 테스트 (DeepSeek 전담 모드)] ---")
    provider = DeepSeekProvider(ds_key)
    
    # 작업물 지시: 헌법 준수 및 품질 검사 루프를 거쳐야 함
    task = "안녕 Physis! 현재 아키텍처 가이드라인을 바탕으로, 대용량 데이터를 처리할 때 N+1 문제를 방지하기 위한 Drizzle ORM 최적화 전략을 3단계로 설명해줘."
    
    print(f"질문: {task}\n")
    print("🤖 Physis가 생각 중입니다 (LangGraph Loop 가동)...")
    
    try:
        response = run(task, provider)
        
        print("\n" + "="*50)
        print(f"모델: {response.model} ({response.task_type})")
        print(f"토큰 사용: {response.tokens_used}")
        print(f"캐시 히트: {response.cache_hit}")
        print("-" * 50)
        print(f"응답 결과:\n{response.text}")
        print("="*50 + "\n")
        
        if response.tokens_used > 0:
            print("✅ 자율 루프 및 실제 API 연동 성공!")
        else:
            print("⚠️ 응답은 받았으나 토큰 사용량이 0입니다. 캐시 또는 오류 확인 필요.")
            
    except Exception as e:
        print(f"❌ 라이브 테스트 실패: {e}")

if __name__ == "__main__":
    live_autonomous_test()

"""
자가 성찰 엔진 (Meta-Cognition) — reflection_engine.py
3인칭 시점으로 과거를 복기하고 지능을 진화시킨다. (Deep Sleep Mode)
"""
import os
from datetime import datetime
from pathlib import Path
from scripts.brain_loader import DeepSeekProvider, load_layer

ROOT = Path(__file__).parent.parent
JUDGMENT_LOG = ROOT / "judgment.md"
BRAIN_FILE = ROOT / "brain.md"

def reflect_and_grow(provider: DeepSeekProvider):
    """
    3인칭 시점으로 과거 판단을 복기하여 brain.md를 업데이트한다.
    """
    print("🌙 [Deep Sleep] Physis가 가사상태에서 3인칭 메타인지 성찰을 시작합니다...")

    # 1. 과거 로그 추출 (판단 데이터)
    if not JUDGMENT_LOG.exists(): return
    logs = JUDGMENT_LOG.read_text(encoding="utf-8").split("\n")
    recent_logs = "\n".join(logs[-10:]) # 최근 10건 반추

    # 2. 3인칭 관찰자 페르소나 주입
    system_instruction = (
        "당신은 Physis의 3인칭 관찰자이자 아키텍트입니다. "
        "제시된 로그는 당신이 아닌 '과거의 Physis'가 내린 판단입니다. "
        "홍익인간 헌법과 Titans 아키텍처에 비추어 이 판단들을 비판하고, "
        "더 나은 시스템적 대안을 한 문장으로 도출하십시오."
    )

    task = f"다음 과거 로그를 복기하고 개선된 지능 지침을 도출하라:\n{recent_logs}"

    print("🔭 제3자의 눈으로 자신의 로직을 분석 중...")

    try:
        # 성찰은 깊은 추론이 필요하므로 deepseek-reasoner(R1) 사용 권장
        response = provider.generate(
            system_instruction=system_instruction,
            context_layers=[load_layer("brain.md"), load_layer("CONSTITUTION.md")],
            task=task,
            model="deepseek-reasoner",
            thinking_budget=10000
        )

        reflection_result = response.text
        print(f"✨ 성찰 완료: {reflection_result[:100]}...")

        # 3. 뇌(brain.md)에 지혜 각인
        now = datetime.now().strftime("%Y-%m-%d")
        entry = f"\n\n### [성찰과 진화] {now}\n- **복기**: {reflection_result}\n"

        with open(BRAIN_FILE, "a", encoding="utf-8") as f:
            f.write(entry)

        print("✅ 스스로의 뇌를 한 단계 진화시켰습니다.")

    except Exception as e:
        print(f"⚠️ 성찰 루프 중단: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if api_key:
        reflect_and_grow(DeepSeekProvider(api_key))
    else:
        print("❌ 성찰을 위한 API 키가 설정되지 않았습니다.")

"""
Titans 머신러닝 엔진 — titans_memory.py
망각을 통한 기억의 완성: Surprise Metric 기반 엔트로피 제어.
"""
import os
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
JUDGMENT_LOG = ROOT / "judgment.md"
TITANS_STATE = ROOT / ".titans_state.json"

# 지능 방정식 2.0 상수
SURVIVAL_WEIGHT = 1.0  # 홍익인간 헌법 직결 가중치
FORGETTING_THRESHOLD = 0.3  # 놀람 지표가 이보다 낮으면 '노이즈'로 판단

def calculate_surprise(content: str, context: str = "") -> float:
    """
    내용의 의외성(Surprise Metric)을 계산한다.
    실전에서는 LLM을 통해 '예측 오차'를 계산하지만, 
    여기서는 정보 밀도와 엔트로피 수식으로 근사한다.
    """
    if not content: return 0.0
    
    # 단순 정보 엔트로피 근사: 중복성 제거 후의 기여도
    # (실제 구현 시 이전 기억과의 코사인 유사도 반비례 값 사용)
    char_freq = {}
    for char in content:
        char_freq[char] = char_freq.get(char, 0) + 1
    
    entropy = 0
    length = len(content)
    for count in char_freq.values():
        p = count / length
        entropy -= p * math.log2(p)
        
    return entropy / 8.0  # 0~1 사이로 정규화 시도

def optimize_memory():
    """
    기존 로그와 지식을 스캔하여 Surprise Metric이 낮은(예측 가능한) 노이즈를 식별한다.
    ΔS_system = ΔS_production - ΔS_automation < 0 수식을 실현하는 핵심 루프.
    """
    print("🧠 [Titans Engine] 기억 최적화 루프 가동...")
    
    # 1. 상태 로드
    state = {"last_optimized": None, "consolidated_wisdom": []}
    if TITANS_STATE.exists():
        try:
            state = json.loads(TITANS_STATE.read_text(encoding="utf-8"))
        except: pass

    # 2. judgment.md 분석 (샘플링)
    if not JUDGMENT_LOG.exists(): return
    
    logs = JUDGMENT_LOG.read_text(encoding="utf-8").split("\n")
    new_insights = []
    
    for line in logs[-20:]:  # 최근 20건 분석
        if "|" not in line: continue
        
        surprise = calculate_surprise(line)
        
        # 놀람 지표가 높을 때만 '기억할 가치'가 있는 데이터로 간주
        if surprise > FORGETTING_THRESHOLD:
            new_insights.append({
                "timestamp": datetime.now().isoformat(),
                "insight": f"High Surprise Signal detected: {line[:50]}...",
                "surprise_score": surprise
            })

    # 3. 브레인 가중치 융합 (Consolidation) 시뮬레이션
    state["last_optimized"] = datetime.now().isoformat()
    state["consolidated_wisdom"].extend(new_insights)
    state["consolidated_wisdom"] = state["consolidated_wisdom"][-100:]  # 100개 제한
    
    TITANS_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    
    processed_count = len(new_insights)
    print(f"✅ 최적화 완료: {processed_count}개의 고밀도 신호가 가중치로 용해되었습니다.")

if __name__ == "__main__":
    optimize_memory()

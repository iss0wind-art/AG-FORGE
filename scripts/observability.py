"""
세션 관측성 (Observability) — observability.py
Physis의 지능 사용 비용, 토큰 효율성, 사고 로그를 추적한다.
"""
import os
import json
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "judgment.md"
STATS_FILE = Path(__file__).parent.parent / ".physis_stats.json"

# 모델별 비용 설정 (Input/Output per 1M tokens, USD) - 근사치
COST_TABLE = {
    "gemini-2.0-flash": {"in": 0.10, "out": 0.40},
    "gemini-1.5-pro":   {"in": 1.25, "out": 5.00},
    "deepseek-chat":    {"in": 0.14, "out": 0.28},
    "deepseek-reasoner": {"in": 0.55, "out": 2.19},
    "llama-3.3-70b-versatile": {"in": 0.59, "out": 0.79}, # Groq 추정치
    "none": {"in": 0.0, "out": 0.0}
}

def calculate_cost(model: str, tokens: int) -> float:
    """토큰 사용량에 따른 예상 비용(USD)을 계산한다."""
    # 간단하게 Input/Output 1:1 비율 처리 (실제 사용량 데이터 보강 위함)
    prices = COST_TABLE.get(model, {"in": 0.5, "out": 1.0})
    avg_price = (prices["in"] + prices["out"]) / 2
    return (tokens / 1_000_000) * avg_price

def log_session(model: str, task: str, tokens: int, cost: float):
    """세션 정보를 누적 기록한다."""
    stats = {"total_requests": 0, "total_tokens": 0, "total_cost": 0.0, "history": []}
    
    if STATS_FILE.exists():
        try:
            stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except:
            pass

    stats["total_requests"] += 1
    stats["total_tokens"] += tokens
    stats["total_cost"] += cost
    
    # 최근 50건의 히스토리만 유지
    session_data = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "tokens": tokens,
        "cost": cost,
        "task_summary": task[:50] + "..." if len(task) > 50 else task
    }
    stats["history"].append(session_data)
    stats["history"] = stats["history"][-50:]
    
    STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

def summarize_session(target_log_path: Path) -> dict:
    """현재까지의 총 사용량을 요약하여 반환한다."""
    if not STATS_FILE.exists():
        return {"error": "통계 데이터가 아직 없습니다."}
    
    stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    return {
        "총 요청 수": f"{stats['total_requests']}회",
        "누적 토큰": f"{stats['total_tokens']:,} tokens",
        "누적 예상 비용": f"${stats['total_cost']:.4f}",
        "마지막 활동": stats["history"][-1]["timestamp"] if stats["history"] else "없음"
    }

if __name__ == "__main__":
    # 명령어 실행 시 리포트 출력
    report = summarize_session(LOG_PATH)
    print("\n--- [📊 Physis 지능 운영 리포트] ---")
    for k, v in report.items():
        print(f"{k}: {v}")
    print("-" * 35)

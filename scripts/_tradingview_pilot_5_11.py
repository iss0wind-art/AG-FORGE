"""
TradingView 시범 가동 — 5/11 4지국 분석 4종목에 적용해 우리 EnsembleAgent 결정과 비교.
방부장 명: "도입해서 시범가동해라"

비교 대상:
  396500 TIGER 반도체TOP10   — 4지국: SELL 81% (방부장 승인)
  462330 KODEX 2차전지       — 4지국: BUY  74%
  018880 한온시스템          — 4지국: BUY  76%
  011000 진원생명과학        — 4지국: SELL 88%

기대: TradingView 기술 분석 신호와 4지국 EnsembleAgent 신호의 정합 여부.
"""
from __future__ import annotations
import json
from datetime import datetime
from tradingview_ta import TA_Handler, Interval, Exchange


# 4지국 5/11 결정
JIGUK_DECISIONS = {
    "396500": {"name": "TIGER 반도체TOP10",          "signal": "SELL", "conf": 0.81},
    "462330": {"name": "KODEX 2차전지산업레버리지",   "signal": "BUY",  "conf": 0.74},
    "018880": {"name": "한온시스템",                   "signal": "BUY",  "conf": 0.76},
    "011000": {"name": "진원생명과학",                 "signal": "SELL", "conf": 0.88},
}


def query_tv(stock_code: str, interval: Interval = Interval.INTERVAL_1_DAY) -> dict:
    """TradingView 종목 분석 신호 조회 (KRX 한국 종목)."""
    handler = TA_Handler(
        symbol=stock_code,
        screener="korea",
        exchange="KRX",
        interval=interval,
    )
    a = handler.get_analysis()
    return {
        "recommendation": a.summary["RECOMMENDATION"],   # STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL
        "buy_signals": a.summary["BUY"],
        "sell_signals": a.summary["SELL"],
        "neutral_signals": a.summary["NEUTRAL"],
        "oscillators": a.oscillators["RECOMMENDATION"],
        "moving_averages": a.moving_averages["RECOMMENDATION"],
        "indicators": {
            "RSI": round(a.indicators.get("RSI", 0), 2),
            "MACD": round(a.indicators.get("MACD.macd", 0), 4),
            "MACD_signal": round(a.indicators.get("MACD.signal", 0), 4),
            "ADX": round(a.indicators.get("ADX", 0), 2),
            "Stoch_K": round(a.indicators.get("Stoch.K", 0), 2),
            "Stoch_D": round(a.indicators.get("Stoch.D", 0), 2),
            "close": a.indicators.get("close", 0),
            "open": a.indicators.get("open", 0),
            "volume": a.indicators.get("volume", 0),
            "change": round(a.indicators.get("change", 0), 2),
        },
    }


def compare(tv_rec: str, jiguk_signal: str) -> str:
    """TradingView 신호 vs 4지국 신호 정합."""
    # TV: STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL
    # 4지국: BUY/SELL/HOLD
    tv_normalized = "BUY" if "BUY" in tv_rec else ("SELL" if "SELL" in tv_rec else "HOLD")
    if tv_normalized == jiguk_signal:
        return "✅ 정합"
    elif tv_normalized == "HOLD" or jiguk_signal == "HOLD":
        return "🟡 부분 정합 (한쪽 HOLD)"
    else:
        return "❌ 충돌"


def main():
    print(f"=== TradingView 시범 가동 — 5/11 4지국 4종목 (대조 검증) ===\n")
    results = []
    for code, info in JIGUK_DECISIONS.items():
        try:
            tv = query_tv(code, Interval.INTERVAL_1_DAY)
            match = compare(tv["recommendation"], info["signal"])
            results.append({"code": code, **info, "tv": tv, "match": match})

            print(f"📊 {info['name']} ({code})")
            print(f"   4지국:      {info['signal']:5s} 신뢰도 {info['conf']:.0%}")
            print(f"   TradingView: {tv['recommendation']:11s} "
                  f"(BUY {tv['buy_signals']} · SELL {tv['sell_signals']} · NEUTRAL {tv['neutral_signals']})")
            print(f"     - 오실레이터: {tv['oscillators']}")
            print(f"     - 이평선:    {tv['moving_averages']}")
            print(f"     - RSI {tv['indicators']['RSI']} / MACD {tv['indicators']['MACD']} / "
                  f"ADX {tv['indicators']['ADX']} / 종가 {tv['indicators']['close']:,} "
                  f"({tv['indicators']['change']:+}%)")
            print(f"   정합: {match}\n")
        except Exception as e:
            print(f"❌ {code} ({info['name']}) 조회 실패: {type(e).__name__}: {e}\n")
            results.append({"code": code, **info, "error": str(e)})

    # 결과 박제
    out_path = "/home/nas/AG-Forge/physis_memory/raw/outputs/tradingview_pilot_20260511.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": "2026-05-11",
            "purpose": "TradingView 시범 가동 — 4지국 EnsembleAgent 신호와 정합 비교",
            "results": results,
        }, f, ensure_ascii=False, indent=2, default=str)
    print(f"=== 박제 ===\n{out_path}")

    # 요약 통계
    matches = sum(1 for r in results if r.get("match") == "✅ 정합")
    partial = sum(1 for r in results if r.get("match") == "🟡 부분 정합 (한쪽 HOLD)")
    conflict = sum(1 for r in results if r.get("match") == "❌ 충돌")
    errors = sum(1 for r in results if r.get("error"))
    print(f"\n=== 요약 ===")
    print(f"  ✅ 정합:        {matches}건")
    print(f"  🟡 부분 정합:   {partial}건")
    print(f"  ❌ 충돌:        {conflict}건")
    print(f"  ❌ 조회 실패:   {errors}건")


if __name__ == "__main__":
    main()

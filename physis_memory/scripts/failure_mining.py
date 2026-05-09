"""
3지국 실패 발굴기 — 실패 흔적을 수집하고 Gemini로 패턴 분석
실패는 가장 비싼 데이터다. 그 안에 미래 해답이 있다.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# .env 로드
for env in ['/home/nas/AG-Forge/.env', '/home/nas/DREAM_FAC/.env.local']:
    if Path(env).exists():
        for line in Path(env).read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k, v.strip().strip('"').strip("'"))

sys.path.insert(0, '/home/nas/AG-Forge')
from mcp_server import vault_ingest

# 실패·롤백·아카이브 핵심 흔적
FAILURE_SOURCES = [
    # BOQ 실패 흔적
    ('/home/nas/BOQ_2/CONSTITUTION_LEGACY.md', 'boq', 'BOQ 폐기된 헌법 — 진화 이전 버전'),
    ('/home/nas/BOQ_2/DANGUN_BRANCH_SEED_ARCHIVE_2026-04-27.md', 'boq', 'BOQ 폐기된 단군 시드'),
    ('/home/nas/BOQ_2/docs/legacy/LEGACY_CONTEXT.md', 'boq', 'BOQ 레거시 컨텍스트'),
    ('/home/nas/BOQ_2/SKETCHUP_REFACTOR_REPORT.md', 'boq', 'SketchUp 리팩토링 보고서 — 무엇이 실패했나'),
    ('/home/nas/BOQ_2/scripts/emergency_v21_restore.py', 'boq', '응급 v21 복구 스크립트 — 무엇이 깨졌나'),

    # H2OWIND 실패 흔적
    ('/home/nas/H2OWIND_2/DANGUN_BRANCH_SEED_ARCHIVE_2026-04-27.md', 'h2owind', 'H2OWIND 폐기된 단군 시드'),
    ('/home/nas/H2OWIND_2/docs/SECURITY_INCIDENTS.md', 'h2owind', '보안 사고 기록'),
    ('/home/nas/H2OWIND_2/docs/REVAMP_PLAN_2026-04-26.md', 'h2owind', '재정비 계획 — 무엇이 잘못됐기에 재정비?'),
    ('/home/nas/H2OWIND_2/HANDOFF_2026-05-03.md', 'h2owind', 'H2OWIND 핸드오프 (실패 사례 포함)'),

    # FreeCAD 실패 흔적
    ('/home/nas/FreeCAD_4TH/CONSTITUTION_ARCHIVE_2026-04-27.md', 'freecad', 'FreeCAD 폐기 헌법'),
    ('/home/nas/FreeCAD_4TH/이천_부임_안내문_ARCHIVE_2026-04-27.md', 'freecad', '이천 폐기 부임문'),
    ('/home/nas/FreeCAD_4TH/DANGUN_DISPATCH_2026-05-05_REPORT_RECOVERY.md', 'freecad', '단군 보고 복구 — 통신 실패의 흔적'),
    ('/home/nas/FreeCAD_4TH/docs/support_request_coord_unification.md', 'freecad', '좌표 통일 지원 요청 — 실패한 통합 시도'),
    ('/home/nas/FreeCAD_4TH/docs/coord_unification_trials.md', 'freecad', '좌표 통일 트라이얼 — 반복 실패 기록'),
    ('/home/nas/FreeCAD_4TH/docs/MANUAL_DRAWING_TO_FREECAD_v1.md', 'freecad', 'v1 수동 도면 매뉴얼 (구버전)'),
    ('/home/nas/FreeCAD_4TH/docs/MANUAL_DRAWING_TO_FREECAD_v2.md', 'freecad', 'v2 수동 도면 매뉴얼 (개선)'),
    ('/home/nas/FreeCAD_4TH/docs/MANUAL_DRAWING_TO_FREECAD_v3.md', 'freecad', 'v3 — 왜 v3가 필요했나'),
]


def ingest_failures() -> list[dict]:
    print(f"[실패 흔적 수집] {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    collected = []
    for path_str, jiguk, desc in FAILURE_SOURCES:
        p = Path(path_str)
        if not p.exists():
            print(f"  ⊘ 없음: {p.name}")
            continue
        try:
            content = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        title = f"FAIL_{jiguk.upper()}_{p.stem.replace('-', '_')[:50]}"
        body = f"""> 🔴 실패·폐기·롤백 흔적
> {desc}
> 출처: `{p}`

{content[:4000]}

## 분류
- 지국: {jiguk}
- 유형: 실패/폐기/응급복구
- 가치: 미래 해답을 위한 비싼 학습 자료

## 연결
- [[홍익인간]]
- [[3지국장_정체성]]
- [[FAIL_종합_분석]]
"""
        result = vault_ingest(title, body, f'{jiguk}, 실패, 폐기, 회고, 학습자료')
        if result['status'] == 'created':
            print(f"  ✓ {title}")
        collected.append({
            'title': title,
            'jiguk': jiguk,
            'content': content[:3000],
            'desc': desc,
        })
    return collected


def analyze_with_gemini(failures: list[dict]) -> str:
    """Gemini 2.5 Pro로 실패 패턴 분석"""
    from google import genai

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return "GEMINI_API_KEY 미설정"

    corpus = "\n\n---\n\n".join([
        f"# [{f['jiguk'].upper()}] {f['desc']}\n{f['content']}"
        for f in failures
    ])

    prompt = f"""당신은 신고조선 제국의 실패 분석가다.
아래는 1지국 BOQ(정도전), 2지국 H2OWIND(이순신), 3지국 FreeCAD(이천)의 폐기·실패·롤백 흔적이다.

분석 대상:
{corpus}

다음을 추출하라:

## 1. 반복되는 실패 패턴 (지국 공통)
같은 함정에 여러 번 빠진 적이 있는가?

## 2. 지국별 고유 실패 결
정도전·이순신·이천 각자가 자주 만나는 실패 유형.

## 3. 미래 해답 (5가지 핵심 교훈)
이 실패들에서 추출 가능한 구체적이고 실행 가능한 교훈.

## 4. 즉시 채택 가능한 안전장치
다음 사이클에서 같은 실패를 막을 메커니즘.

한국어로, 마크다운으로, 깊이 있게. 표면적 일반론 금지."""

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
    )
    return resp.text


def save_analysis(analysis: str):
    title = "FAIL_종합_분석_2026_05_09"
    body = f"""> 🔬 Gemini 2.5 Pro 분석 — 3지국 실패 코퍼스에서 미래 해답 추출
> 분석일: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 분석 대상: {len(FAILURE_SOURCES)}개 실패·폐기 흔적

{analysis}

## 연결
- [[홍익인간]]
- [[3지국장_정체성]]
- [[Gold_In_Gold_Out]]
- [[피지수_사명_선언]]
"""
    result = vault_ingest(title, body, '실패분석, 종합, 교훈, gemini, 미래해답')
    print(f"\n[종합 분석 박제] {title} — {result['status']}")


if __name__ == '__main__':
    failures = ingest_failures()
    print(f"\n수집된 실패 흔적: {len(failures)}개\n")

    if failures:
        print("[Gemini 2.5 Pro 분석 중...]")
        analysis = analyze_with_gemini(failures)
        print("\n" + "="*70)
        print(analysis[:3000])
        print("="*70 + "\n")
        save_analysis(analysis)

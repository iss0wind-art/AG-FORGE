"""
3지국 구조화 데이터 흡수 — 스키마·매니페스트·핵심 출력물
JSON 파일을 요약된 마크다운으로 변환해 wiki에 추가.
"""

import json
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, '/home/nas/AG-Forge')
from mcp_server import vault_ingest

# 핵심 데이터 파일 화이트리스트
DATA_TARGETS = [
    # FreeCAD 핵심 출력
    ('/home/nas/FreeCAD_4TH/output/boq_unified.json', 'freecad', 'BOQ 통합 산출 (FreeCAD→BOQ 자동화 결과)'),
    ('/home/nas/FreeCAD_4TH/output/codex_columns_unified.json', 'freecad', 'CODEX 기둥 통합'),
    ('/home/nas/FreeCAD_4TH/output/members_boq.json', 'freecad', '부재별 BOQ'),
    ('/home/nas/FreeCAD_4TH/output/complex_master.json', 'freecad', '단지 전체 마스터 모델'),
    ('/home/nas/FreeCAD_4TH/output/v9_boq.json', 'freecad', 'v9 BOQ 산출'),
    ('/home/nas/FreeCAD_4TH/output/poc_v6_101.json', 'freecad', '101동 PoC v6'),
    # FreeCAD 스펙
    ('/home/nas/FreeCAD_4TH/spec/sample_project.boq.yaml', 'freecad', '샘플 프로젝트 BOQ 스펙'),
    ('/home/nas/FreeCAD_4TH/spec/db_schema.sql', 'freecad', 'DB 스키마'),
    # H2OWIND 데이터 플로우
    ('/home/nas/H2OWIND_2/db/schema.ts', 'h2owind', 'DB 스키마 (TypeScript)'),
]


def summarize_json(data, max_depth=2, _depth=0) -> str:
    """JSON을 마크다운 요약으로"""
    if _depth >= max_depth:
        if isinstance(data, list):
            return f"[배열, {len(data)}개]"
        elif isinstance(data, dict):
            return f"{{객체, 키 {len(data)}개: {', '.join(list(data.keys())[:5])}}}"
        else:
            return str(data)[:80]

    lines = []
    if isinstance(data, dict):
        for k, v in list(data.items())[:15]:
            if isinstance(v, (dict, list)):
                lines.append(f"- **{k}**: {summarize_json(v, max_depth, _depth+1)}")
            else:
                lines.append(f"- **{k}**: `{str(v)[:80]}`")
    elif isinstance(data, list) and data:
        lines.append(f"- 배열 길이: {len(data)}개")
        if isinstance(data[0], dict):
            lines.append(f"- 첫 항목 키: {', '.join(list(data[0].keys())[:8])}")
            lines.append(f"- 첫 항목 샘플:")
            for k, v in list(data[0].items())[:5]:
                lines.append(f"  - {k}: `{str(v)[:60]}`")
    return '\n'.join(lines)


def ingest_data_file(path_str: str, jiguk: str, description: str):
    path = Path(path_str)
    if not path.exists():
        print(f"  ⊘ 없음: {path}")
        return None

    try:
        if path.suffix == '.json':
            data = json.loads(path.read_text(encoding='utf-8'))
            summary = summarize_json(data, max_depth=3)
        else:
            text = path.read_text(encoding='utf-8', errors='ignore')
            summary = f"```\n{text[:3500]}\n```"
    except Exception as e:
        print(f"  ✗ 오류 {path.name}: {e}")
        return None

    title = f"{jiguk.upper()}_DATA_{path.stem}"
    body = f"""> {description}
> 출처: `{path}`
> 흡수일: {datetime.now().strftime('%Y-%m-%d')}

## 구조 요약

{summary}

## 연결
- [[홍익인간]]
- [[3지국장_정체성]]
- [[{jiguk.upper()}_CLAUDE]]
"""
    tag = f"{jiguk}, 데이터, 스키마, 산출물"
    result = vault_ingest(title, body, tag)
    print(f"  ✓ {title} ({path.stat().st_size // 1024}KB)")
    return result


if __name__ == '__main__':
    print(f"[3지국 데이터 흡수] {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    count = 0
    for path_str, jiguk, desc in DATA_TARGETS:
        r = ingest_data_file(path_str, jiguk, desc)
        if r:
            count += 1
    print(f"\n총 {count}개 데이터 노드 생성")

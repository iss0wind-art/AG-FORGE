"""
3지국 데이터 대량 흡수 — 핵심 도큐먼트를 피지수 wiki에 ingestion
선별적: 핵심 .md, 스키마, 도메인 문서만. 노이즈(node_modules, .next, archive) 제외.
"""

import re
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, '/home/nas/AG-Forge')
from mcp_server import vault_ingest

JIGUK = {
    'boq': {
        'root': Path('/home/nas/BOQ_2'),
        'tag': 'boq, 1지국, 정도전',
        'jangguk_name': '1지국 BOQ (정도전)',
    },
    'h2owind': {
        'root': Path('/home/nas/H2OWIND_2'),
        'tag': 'h2owind, 2지국, 이순신',
        'jangguk_name': '2지국 H2OWIND (이순신)',
    },
    'freecad': {
        'root': Path('/home/nas/FreeCAD_4TH'),
        'tag': 'freecad, 3지국, 이천',
        'jangguk_name': '3지국 FreeCAD (이천)',
    },
}

# 흡수 대상 패턴 (높은 가치)
INCLUDE_PATTERNS = [
    'CLAUDE.md',
    'CONSTITUTION.md',
    'README.md',
    'ARCHITECTURE.md',
    'DATA_FLOW.md',
    'TEAM_OPERATIONS.md',
    'DANGUN_BRANCH_SEED.md',
    '특허_기술명세서.md',
    'brain.md',
    'brain_architecture.md',
    'brain_status.md',
    'brain_patent.md',
    'brain_tasks.md',
    'brain_weekly_report.md',
    'core_stack.md',
    'logic_context.md',
    'data_flow*.md',
    'HANDOFF_*.md',
    'spec/*.md',
    'docs/*.md',
    'tools/README*.md',
]

# 제외 패턴
EXCLUDE_PATTERNS = [
    'node_modules', '.next', '.git', 'dist', 'build', 'coverage',
    'ARCHIVE', '_archive', 'backup', 'cache', '__pycache__',
    'tests/', 'test/', '.pytest_cache',
]

MAX_LEN = 4500  # 노드당 최대 글자


def is_excluded(path: Path) -> bool:
    s = str(path)
    return any(p in s for p in EXCLUDE_PATTERNS)


def collect_targets(root: Path) -> list[Path]:
    targets = []
    for path in root.rglob('*.md'):
        if is_excluded(path):
            continue
        # 깊이 3 이내로 제한
        try:
            depth = len(path.relative_to(root).parts)
            if depth > 4:
                continue
        except ValueError:
            continue
        # 빈 파일 제외
        try:
            if path.stat().st_size < 200 or path.stat().st_size > 100000:
                continue
        except OSError:
            continue
        # 패턴 매칭
        name = path.name
        rel = str(path.relative_to(root))
        for pattern in INCLUDE_PATTERNS:
            if '*' in pattern:
                # glob 매칭
                if path.match(pattern):
                    targets.append(path)
                    break
            elif name == pattern or rel.endswith('/' + pattern):
                targets.append(path)
                break
    return targets


def make_title(jiguk_key: str, path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    stem = '_'.join(rel.with_suffix('').parts)
    # 한글·영문·숫자만 허용, 공백→_
    clean = re.sub(r'[^\w가-힣\-]', '_', stem)
    return f"{jiguk_key.upper()}_{clean}"


def ingest_jiguk(key: str, info: dict) -> int:
    targets = collect_targets(info['root'])
    print(f"\n[{info['jangguk_name']}] {len(targets)}개 문서 발견")
    count = 0
    for path in targets:
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        if len(content) > MAX_LEN:
            content = content[:MAX_LEN] + f"\n\n... (잘림 — 원본: `{path}`)"

        title = make_title(key, path, info['root'])
        rel = path.relative_to(info['root'])

        body = f"""> 출처: `{info['root'].name}/{rel}` — {info['jangguk_name']} 자동 흡수
> 흡수일: {datetime.now().strftime('%Y-%m-%d')}

{content}

## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]
"""
        result = vault_ingest(title, body, info['tag'])
        if result['status'] == 'created':
            count += 1
            print(f"  ✓ {title}")
        elif result['status'] == 'updated':
            print(f"  ↻ {title}")
    return count


if __name__ == '__main__':
    total = 0
    for key, info in JIGUK.items():
        total += ingest_jiguk(key, info)
    print(f"\n전체 ingestion: {total}개 새 노드 생성")

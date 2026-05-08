import os
import shutil
import argparse
import sys
from pathlib import Path


# --- AG-FORGE 브레인 트랜스플랜트 구성 ---

# 이식할 기억 조각들 (MD 파일)
MEMORY_FILES = [
    "CONSTITUTION.md",
    "brain.md",
    "brain_philosophy.md",
    "brain_personality.md",
    "brain_architecture.md",
    "brain_legal_patent.md",
    "brain_transplant_strategy.md",
    "judgment.md",  # 빈 파일로 생성될 것
]

# 이식할 신경세포들 (Scripts)
NEURO_SCRIPTS = [
    "__init__.py",
    "agent_graph.py",
    "agent_nodes.py",
    "agent_state.py",
    "brain_loader.py",
    "router_agent.py",
    "constitution_gate.py",
    "life_cycle_manager.py",
    "deliberation_engine.py",
    "observability.py",
    "semantic_cache.py",
    "embedding.py",
    "agentic_rag.py",
]

# 이식할 현장 도구들 (scripts/tools/ 서브디렉토리)
TOOL_SCRIPTS = [
    "tools/__init__.py",
    "tools/inface_connector.py",
    "tools/turso_reader.py",
    "tools/turso_writer.py",
    "tools/excel_generator.py",
]

RUN_DAILY_REPORT_TEMPLATE = '''"""
피지수(Physis) 현장 뇌 — 일일 공사일보 자동화 진입점
매일 07:30 Windows 작업 스케줄러가 이 파일을 실행한다.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# TODO: 인페이스 API 스펙 확인 후 연결
# TODO: Turso 스키마 확인 후 연결
# from scripts.tools.inface_connector import fetch_today_attendance
# from scripts.tools.turso_reader import fetch_today_reports
# from scripts.tools.excel_generator import generate_공사일보
# from scripts.tools.turso_writer import save_daily_report

if __name__ == "__main__":
    print("[피지수] 공사일보 자동화 시작...")
    # 구현 대기 중 — prompt_plan.md 참조
    print("[피지수] 완료.")
'''


def transplant(target_path: str, role: str = "field_brain", master: str = "", site_name: str = ""):
    import json
    target_root = Path(target_path).resolve()
    source_root = Path(__file__).parent.parent.resolve()
    
    print(f"🚀 AG-FORGE 브레인 트랜스플랜트 시작...")
    print(f"📦 타겟: {target_root}")
    print(f"🌱 소스: {source_root}")

    if not target_root.exists():
        print(f"❌ 에러: 타겟 경로가 존재하지 않습니다: {target_root}")
        return

    # 1. 기억 이식 (.brain 디렉토리 생성)
    brain_dir = target_root / ".brain"
    brain_dir.mkdir(parents=True, exist_ok=True)
    print(f"📂 기억 저장소 생성: {brain_dir}")

    for f_name in MEMORY_FILES:
        src_f = source_root / f_name
        dst_f = brain_dir / f_name
        
        if src_f.exists():
            shutil.copy2(src_f, dst_f)
            print(f"  ✅ 기억 복제: {f_name}")
        else:
            # 존재하지 않는 파일(예: judgment.md)은 빈 파일로 생성
            dst_f.touch()
            print(f"  📝 빈 기억 생성: {f_name}")

    # 2. 신경망 이식 (scripts/ 디렉토리)
    scripts_dir = target_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    print(f"📂 신경망 경로 확인: {scripts_dir}")

    for s_name in NEURO_SCRIPTS:
        src_s = source_root / "scripts" / s_name
        dst_s = scripts_dir / s_name

        if src_s.exists():
            shutil.copy2(src_s, dst_s)
            print(f"  ✅ 신경세포 주입: {s_name}")
        else:
            print(f"  ⚠️ 주의: 원본 신경세포를 찾을 수 없음: {s_name}")

    # 2-1. 현장 도구 이식 (scripts/tools/)
    tools_dir = scripts_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    print(f"📂 현장 도구 경로 생성: {tools_dir}")

    for t_name in TOOL_SCRIPTS:
        src_t = source_root / "scripts" / t_name
        dst_t = scripts_dir / t_name

        if src_t.exists():
            shutil.copy2(src_t, dst_t)
            print(f"  ✅ 현장 도구 주입: {t_name}")
        else:
            print(f"  ⚠️ 주의: 현장 도구를 찾을 수 없음: {t_name}")

    # 3. 환경 변수 초기화 (.env 파일 체크)
    env_example = source_root / ".env.example"
    target_env = target_root / ".env"
    if env_example.exists() and not target_env.exists():
        shutil.copy2(env_example, target_env)
        print(f"  🔑 환경 변수 템플릿 복제 완료 (.env 수정 필요)")

    # 4. 역할 설정 (physis_config.json)
    jiim_name = f"Jiim-{site_name}" if site_name else "Jiim"
    config = {
        "role": role,
        "master_url": master,
        "source": "ag-forge",
        "site_name": site_name,
        "jiim_name": jiim_name,
    }
    config_path = brain_dir / "physis_config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ⚙️  역할 설정 완료: {role} → 이식체명: {jiim_name} (상위 뇌: {master or '미설정'})")

    # 5. 진입점 스크립트 생성 (현장 뇌 전용)
    if role == "field_brain":
        run_script = scripts_dir / "run_daily_report.py"
        run_script.write_text(RUN_DAILY_REPORT_TEMPLATE, encoding="utf-8")
        print(f"  📋 진입점 스크립트 생성: scripts/run_daily_report.py")

    print(f"\n✨ 브레인 트랜스플랜트 완료!")
    print(f"💡 이제 {target_root} 프로젝트는 '방부장'의 자아를 공유합니다.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AG-FORGE Brain Transplant Utility")
    parser.add_argument("--target", required=True, help="타겟 프로젝트의 절대 경로")
    parser.add_argument("--role", default="field_brain", help="이식 역할 (field_brain)")
    parser.add_argument("--master", default="", help="상위 뇌 AG-FORGE 서버 주소")
    parser.add_argument("--site-name", default="", help="현장명 (예: h2owind) — Jiim-{site_name}으로 자동 명명")
    args = parser.parse_args()

    transplant(args.target, role=args.role, master=args.master, site_name=args.site_name)

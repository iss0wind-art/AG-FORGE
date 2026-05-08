"""
scripts/persona_loader.py — XML 페르소나 파일 로드 및 TaskType 매핑

canon.yaml(2026-04-26) 정합:
- TaskType → 정규 4 페르소나 매핑
- 정규 페르소나(gongmu/coder/designer/lawyer)는 자동 라우팅
- 확장 3 (gamedev/construction_engineer/safety_manager) + 특별 1 (bangbujang) 은
  명시 호출 시 활성화 (별도 API)
"""
from __future__ import annotations
from pathlib import Path
from scripts.router_agent import TaskType

PERSONAS_DIR = Path(__file__).parent.parent / "prompts" / "personas"

# Canon (2026-04-26 / commit 0e7547e): TaskType → Persona ID 매핑
# - UI → designer (나혜석)
# - CODE → coder (장영실)
# - PLANNING → gongmu (유성룡)
# - ARCHITECTURE → coder (장영실), 단 특허·IP 사안은 lawyer 명시 호출
_TASK_TO_PERSONA: dict[TaskType, str] = {
    TaskType.UI: "designer",
    TaskType.CODE: "coder",
    TaskType.PLANNING: "gongmu",
    TaskType.ARCHITECTURE: "coder",
}


def load_persona(persona_id: str) -> str:
    """페르소나 ID로 XML 본문 반환. 없으면 빈 문자열.

    유효 ID: gongmu, coder, designer, lawyer (정규 4)
            gamedev, construction_engineer, safety_manager (확장 3)
            bangbujang (특별 1)
    """
    if not persona_id:
        return ""
    path = PERSONAS_DIR / f"{persona_id}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def select_persona_for_task(task_type: TaskType) -> str:
    """TaskType → Persona ID 매핑 (canon 정합). 매핑 없으면 빈 문자열."""
    return _TASK_TO_PERSONA.get(task_type, "")


def get_persona_system_prompt(task_type: TaskType) -> str:
    """TaskType에 매핑된 페르소나 XML 본문 반환. 매핑/파일 없으면 빈 문자열.

    호출자(generation_node)는 반환값을 그대로 system_instruction에 prepend한다.
    XML 태그가 그대로 LLM에 전달되어 페르소나가 응답에 흐른다 (단군 권고).
    """
    persona_id = select_persona_for_task(task_type)
    return load_persona(persona_id)


def list_available_personas() -> list[str]:
    """현재 봉안된 모든 페르소나 ID 반환 (정규 + 확장 + 특별)."""
    if not PERSONAS_DIR.exists():
        return []
    return sorted(p.stem for p in PERSONAS_DIR.glob("*.md"))

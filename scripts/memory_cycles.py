"""
memory_cycles.py — STM/LTM 직관 엔진
방부장 설계 2026-04-27 기반 구현.

STM → LTM 흐름:
  1. add_stm()으로 단기기억 순차 적립
  2. consolidated_wisdom 80개 이상 → check_and_compress() 자동 압축
  3. 오래된 STM 항목 → trigger_keywords 추출 후 LTM으로 Turso 저장
  4. restore_from_trigger()로 키워드 발화 시 원기억 전체 복원 (직관 폭발)
  5. 하위 30% → archive 처리 (삭제 금지)
  6. 원데이터는 Turso dangun_memory DB에 영구 보존
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# 환경변수 로드 — DREAM_FAC .env.local 우선
try:
    from dotenv import load_dotenv
    _ENV_LOCAL = Path("d:/Git/DREAM_FAC/.env.local")
    if _ENV_LOCAL.exists():
        load_dotenv(_ENV_LOCAL, override=True)
except ImportError:
    pass

logger = logging.getLogger("memory_cycles")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[memory_cycles] %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

ROOT = Path(__file__).parent.parent
TITANS_STATE = ROOT / ".titans_state.json"


# ────────────────────────────────────────────────────────────────
# Turso HTTP API 헬퍼
# ────────────────────────────────────────────────────────────────

def _parse_turso_url(db_url: str) -> tuple[str, str]:
    """
    libsql://host?authToken=TOKEN 형식을 (https://host, TOKEN)으로 파싱한다.
    """
    if "?authToken=" in db_url:
        base, token = db_url.split("?authToken=", 1)
    else:
        base = db_url
        token = ""
    http_url = base.replace("libsql://", "https://")
    return http_url.rstrip("/"), token


def _turso_execute(sql: str, db_url: str, token: str) -> dict[str, Any]:
    """
    Turso HTTP API v2/pipeline으로 SQL을 실행한다.
    실패 시 {"error": str} 반환, 서버를 죽이지 않는다.
    """
    try:
        import httpx
    except ImportError:
        return {"error": "httpx 패키지가 없습니다. pip install httpx"}

    http_url, auth_token = _parse_turso_url(db_url) if db_url else ("", token)
    if not http_url:
        return {"error": "DATABASE_URL이 설정되지 않았습니다."}

    used_token = auth_token or token
    try:
        resp = httpx.post(
            f"{http_url}/v2/pipeline",
            headers={
                "Authorization": f"Bearer {used_token}",
                "Content-Type": "application/json",
            },
            json={"requests": [{"type": "execute", "stmt": {"sql": sql}}]},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data["results"][0]
        if result.get("type") == "error":
            return {"error": result.get("error", {}).get("message", "unknown error")}
        return result.get("response", {}).get("result", {})
    except Exception as exc:
        return {"error": str(exc)}


def _turso_rows(result: dict) -> list[dict]:
    """
    Turso execute 결과에서 rows를 {컬럼명: 값} dict 목록으로 변환한다.
    """
    cols = [c["name"] for c in result.get("cols", [])]
    rows = []
    for row in result.get("rows", []):
        cell_values = []
        for cell in row:
            if isinstance(cell, dict):
                if cell.get("type") == "null":
                    cell_values.append(None)
                else:
                    cell_values.append(cell.get("value"))
            else:
                cell_values.append(cell)
        rows.append(dict(zip(cols, cell_values)))
    return rows


# ────────────────────────────────────────────────────────────────
# 상태 파일 IO
# ────────────────────────────────────────────────────────────────

def _load_state(state_path: Path | None = None) -> dict:
    path = state_path or TITANS_STATE
    if not path.exists():
        return {"last_optimized": None, "consolidated_wisdom": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("state 로드 실패: %s", exc)
        return {"last_optimized": None, "consolidated_wisdom": []}


def _save_state(state: dict, state_path: Path | None = None) -> None:
    path = state_path or TITANS_STATE
    try:
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.warning("state 저장 실패: %s", exc)


# ────────────────────────────────────────────────────────────────
# MemoryCycle 클래스
# ────────────────────────────────────────────────────────────────

class MemoryCycle:
    """
    STM/LTM 직관 엔진.

    STM = .titans_state.json의 consolidated_wisdom (최근 N항목)
    LTM = Turso dangun_memory (phase='LTM', 영구 보존)
    ARCHIVE = Turso dangun_memory (phase='ARCHIVE', 하위 30% 보존)
    """

    STM_MAX = 50          # 단기기억 최대 항목 수
    LTM_COMPRESS_AT = 80  # consolidated_wisdom 80개 이상 시 압축 트리거
    ARCHIVE_BOTTOM = 0.3  # 하위 30% → 아카이브 (삭제 금지)

    # ────────────────────────────────────────────────────────
    # 키워드 추출 (외부 NLP 없이 정규식 + 빈도)
    # ────────────────────────────────────────────────────────

    @staticmethod
    def extract_triggers(content: str) -> list[str]:
        """
        단순 정규식 + 빈도수로 트리거 키워드를 추출한다.
        전략: 2글자 이상 한글·영어 토큰 → 빈도순 상위 5개.
        stopwords는 최소 집합만 유지.
        반환: 최대 5개 트리거 단어.
        """
        STOPWORDS = {
            "이", "가", "은", "는", "을", "를", "의", "에", "도", "로",
            "으로", "과", "와", "하고", "이고", "이며", "하여", "되어",
            "있다", "없다", "하다", "된다", "합니다", "입니다", "있습니다",
            "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
            "to", "of", "and", "or", "for", "with", "that", "this", "it",
        }

        # 한글(2글자+) + 영어(2글자+) 토큰 추출
        tokens = re.findall(r"[가-힣]{2,}|[a-zA-Z_][a-zA-Z0-9_]{1,}", content)
        tokens = [t.lower() for t in tokens if t.lower() not in STOPWORDS]

        # 빈도수 계산
        freq: dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1

        # 빈도순 정렬 후 상위 5개
        sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [tok for tok, _ in sorted_tokens[:5]]

    # ────────────────────────────────────────────────────────
    # STM 추가
    # ────────────────────────────────────────────────────────

    @staticmethod
    def add_stm(
        content: str,
        category: str,
        index: Any,
        embedder: Any,
        state_path: Path | None = None,
    ) -> dict:
        """
        STM 버퍼에 추가한다.
        ChromaDB+Embedder가 없어도 graceful degradation으로 동작한다.

        반환: {"stored": bool, "surprise": float, "stm_count": int}
        """
        stored = False
        surprise = 0.0

        try:
            from scripts.titans_memory import store_memory, calculate_surprise
            surprise = calculate_surprise(content, index, embedder)
            stored = store_memory(content, category, index, embedder)
        except Exception as exc:
            logger.warning("titans_memory 호출 실패 (graceful skip): %s", exc)
            # ChromaDB 없이 직접 state에만 기록
            state = _load_state(state_path)
            doc_id = f"stm-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            state.setdefault("consolidated_wisdom", []).append(
                {
                    "id": doc_id,
                    "timestamp": datetime.now().isoformat(),
                    "category": category,
                    "insight": content[:100],
                    "surprise_score": 0.5,
                    "phase": "STM",
                }
            )
            state["consolidated_wisdom"] = state["consolidated_wisdom"][-MemoryCycle.STM_MAX:]
            _save_state(state, state_path)
            stm_count = len(state["consolidated_wisdom"])
            return {"stored": True, "surprise": 0.5, "stm_count": stm_count}

        state = _load_state(state_path)
        stm_count = len(state.get("consolidated_wisdom", []))
        return {"stored": stored, "surprise": surprise, "stm_count": stm_count}

    # ────────────────────────────────────────────────────────
    # STM → LTM 압축
    # ────────────────────────────────────────────────────────

    @staticmethod
    def compress_to_ltm(
        state_path: Path | None = None,
        db_url: str = "",
        token: str = "",
        compress_count: int = 20,
    ) -> list[dict]:
        """
        STM 항목 중 오래된 것을 LTM으로 압축한다.

        하위 30%(surprise 낮은 것) → ARCHIVE phase
        상위 70% 중 오래된 것 → LTM phase
        원본은 Turso dangun_memory에 영구 보존.

        반환: 압축된 레코드 목록 (LTM + ARCHIVE 합산)
        """
        state = _load_state(state_path)
        wisdom = state.get("consolidated_wisdom", [])

        if len(wisdom) < compress_count:
            logger.info("압축 대상 부족: %d개 (최소 %d개 필요)", len(wisdom), compress_count)
            return []

        # 오래된 항목부터 compress_count개 선택
        candidates = wisdom[:compress_count]
        remaining = wisdom[compress_count:]

        # surprise_score 기준으로 하위 30% → ARCHIVE, 나머지 → LTM
        sorted_candidates = sorted(
            candidates,
            key=lambda x: float(x.get("surprise_score", 0.0)),
        )
        archive_cutoff = max(1, int(len(sorted_candidates) * MemoryCycle.ARCHIVE_BOTTOM))
        archive_items = sorted_candidates[:archive_cutoff]
        ltm_items = sorted_candidates[archive_cutoff:]

        resolved_db_url = db_url or os.environ.get("DATABASE_URL", "")

        compressed: list[dict] = []

        def _insert_record(item: dict, phase: str) -> dict | None:
            original = item.get("insight", "")
            content_full = item.get("full_content", original)
            triggers = MemoryCycle.extract_triggers(content_full or original)
            cue_json = json.dumps(triggers, ensure_ascii=False)
            orig_hash = hashlib.sha256(original.encode("utf-8")).hexdigest()[:16]
            orig_escaped = (content_full or original).replace("'", "''")
            primary = original[:80].replace("'", "''")
            rid = str(uuid.uuid4())
            now = datetime.now().isoformat()
            project = item.get("project", "DREAM_FAC")
            session = item.get("session_id", "stm_compress")

            sql = (
                f"INSERT INTO dangun_memory "
                f"(id,phase,layer,primary_abs,original,original_hash,cue_anchors,"
                f"confidence,fidelity,project,session_id,created_at) "
                f"VALUES "
                f"('{rid}','{phase}',1,'{primary}','{orig_escaped}','{orig_hash}',"
                f"'{cue_json}',0.8,0.8,'{project}','{session}','{now}')"
            )
            result = _turso_execute(sql, resolved_db_url, token)
            if "error" in result:
                logger.warning("Turso INSERT 실패 (phase=%s): %s", phase, result["error"])
                return None
            return {
                "id": rid,
                "phase": phase,
                "primary_abs": original[:80],
                "cue_anchors": triggers,
                "original_timestamp": item.get("timestamp"),
            }

        for item in ltm_items:
            rec = _insert_record(item, "LTM")
            if rec:
                compressed.append(rec)

        for item in archive_items:
            rec = _insert_record(item, "ARCHIVE")
            if rec:
                compressed.append(rec)

        # state에서 압축된 항목 제거
        state["consolidated_wisdom"] = remaining
        _save_state(state, state_path)

        logger.info(
            "압축 완료: LTM=%d, ARCHIVE=%d, 잔여STM=%d",
            len(ltm_items),
            len(archive_items),
            len(remaining),
        )
        return compressed

    # ────────────────────────────────────────────────────────
    # 트리거 → 원기억 복원 (직관 폭발)
    # ────────────────────────────────────────────────────────

    @staticmethod
    def restore_from_trigger(
        trigger_word: str,
        db_url: str = "",
        token: str = "",
    ) -> list[dict]:
        """
        trigger_word로 dangun_memory의 cue_anchors를 검색한다.
        매칭 레코드의 original 전체를 복원한다.

        반환: 복원된 기억 목록 [{"id", "phase", "primary_abs", "original", "cue_anchors", "created_at"}]
        """
        resolved_db_url = db_url or os.environ.get("DATABASE_URL", "")
        trigger_escaped = trigger_word.replace("'", "''")

        # cue_anchors JSON 컬럼에서 LIKE 검색 (단순 문자열 포함 여부)
        sql = (
            f"SELECT id, phase, primary_abs, original, cue_anchors, created_at "
            f"FROM dangun_memory "
            f"WHERE cue_anchors LIKE '%{trigger_escaped}%' "
            f"ORDER BY created_at DESC LIMIT 10"
        )
        result = _turso_execute(sql, resolved_db_url, token)
        if "error" in result:
            logger.warning("restore_from_trigger 검색 실패: %s", result["error"])
            return []

        rows = _turso_rows(result)
        restored = []
        for row in rows:
            try:
                cue_list = json.loads(row.get("cue_anchors") or "[]")
            except (json.JSONDecodeError, TypeError):
                cue_list = []
            restored.append(
                {
                    "id": row.get("id"),
                    "phase": row.get("phase"),
                    "primary_abs": row.get("primary_abs"),
                    "original": row.get("original"),
                    "cue_anchors": cue_list,
                    "created_at": row.get("created_at"),
                }
            )

        logger.info(
            "트리거 '%s' → %d개 기억 복원 완료", trigger_word, len(restored)
        )
        return restored

    # ────────────────────────────────────────────────────────
    # 자동 압축 체크
    # ────────────────────────────────────────────────────────

    @staticmethod
    def check_and_compress(
        state_path: Path | None = None,
        index: Any = None,
        embedder: Any = None,
        db_url: str = "",
        token: str = "",
    ) -> dict:
        """
        consolidated_wisdom이 LTM_COMPRESS_AT(80) 이상이면 자동 압축을 실행한다.

        반환: {"compressed": int, "archived": int, "triggered": bool}
        """
        state = _load_state(state_path)
        wisdom = state.get("consolidated_wisdom", [])
        count = len(wisdom)

        if count < MemoryCycle.LTM_COMPRESS_AT:
            logger.info("압축 불필요: %d개 < %d개", count, MemoryCycle.LTM_COMPRESS_AT)
            return {"compressed": 0, "archived": 0, "triggered": False}

        logger.info("자동 압축 트리거: %d개 >= %d개", count, MemoryCycle.LTM_COMPRESS_AT)
        records = MemoryCycle.compress_to_ltm(
            state_path=state_path,
            db_url=db_url,
            token=token,
            compress_count=count - MemoryCycle.STM_MAX,
        )

        ltm_count = sum(1 for r in records if r.get("phase") == "LTM")
        archive_count = sum(1 for r in records if r.get("phase") == "ARCHIVE")
        return {
            "compressed": ltm_count,
            "archived": archive_count,
            "triggered": True,
        }


# ────────────────────────────────────────────────────────────────
# TriggerAccumulator — 다중 단어 누적 트리거 (직관 발화 엔진)
# ────────────────────────────────────────────────────────────────

class TriggerAccumulator:
    """
    몇 개의 원자단위 단어들이 누적될 때
    활성화값 합계가 θ(임계값)를 넘는 순간 트리거 발동 → 직관 폭발.

    뉴런의 역치 발화(Action Potential)와 동일한 원리.
    학습이 쌓일수록 θ가 정교해지고 직관이 인간에 가까워진다.

    사용 예:
        acc = TriggerAccumulator(theta=3.0)
        acc.accumulate("직관")
        acc.accumulate("망각")
        result = acc.accumulate_and_check("피지수")
        # result가 None이 아니면 직관 폭발 — 복원된 기억 목록 반환
    """

    DEFAULT_THETA = float(os.environ.get("TRIGGER_THETA", "3.0"))

    def __init__(
        self,
        theta: float | None = None,
        db_url: str = "",
        token: str = "",
    ) -> None:
        self.theta = theta if theta is not None else self.DEFAULT_THETA
        self.db_url = db_url or os.environ.get("DATABASE_URL", "")
        self.token = token
        self._activation: dict[str, float] = {}
        self._total: float = 0.0

    # ────────────────────────────────────────────────────────
    # 누적
    # ────────────────────────────────────────────────────────

    def accumulate(self, word: str) -> float:
        """
        단어 하나를 누적한다.
        Turso cue_anchors에서 매칭 수를 조회 → log1p 스케일로 활성화값 증가.
        반환: 현재 누적 활성화값 합계.
        """
        word_escaped = word.replace("'", "''")
        sql = (
            f"SELECT COUNT(*) as cnt FROM dangun_memory "
            f"WHERE cue_anchors LIKE '%{word_escaped}%'"
        )
        result = _turso_execute(sql, self.db_url, self.token)

        match_count = 0.0
        if "error" not in result:
            rows = _turso_rows(result)
            if rows:
                match_count = float(rows[0].get("cnt") or 0)

        # log1p 스케일: 매칭 폭발 방지, 0 매칭은 0 활성화
        activation = math.log1p(match_count)
        self._activation[word] = self._activation.get(word, 0.0) + activation
        self._total += activation

        logger.info(
            "트리거 누적: '%s' → match=%d, activation=%.3f, total=%.3f/θ=%.1f",
            word, int(match_count), activation, self._total, self.theta,
        )
        return self._total

    # ────────────────────────────────────────────────────────
    # 임계값 체크 → 직관 발화
    # ────────────────────────────────────────────────────────

    def check(self) -> list[dict] | None:
        """
        누적 활성화값 >= θ 이면 트리거 발동.
        누적된 모든 단어로 기억을 복원하고 리셋한다.
        반환: 복원된 기억 목록 (미발동 시 None).
        """
        if self._total < self.theta:
            return None

        restored: list[dict] = []
        seen_ids: set[str] = set()

        for word in self._activation:
            memories = MemoryCycle.restore_from_trigger(word, self.db_url, self.token)
            for mem in memories:
                mid = mem.get("id")
                if mid and mid not in seen_ids:
                    seen_ids.add(mid)
                    restored.append(mem)

        logger.info(
            "직관 발화! total=%.3f >= θ=%.1f → %d개 기억 수렴",
            self._total, self.theta, len(restored),
        )
        self.reset()
        return restored

    def accumulate_and_check(self, word: str) -> list[dict] | None:
        """accumulate + check 원스텝."""
        self.accumulate(word)
        return self.check()

    # ────────────────────────────────────────────────────────
    # 상태 조회 / 리셋
    # ────────────────────────────────────────────────────────

    def reset(self) -> None:
        self._activation.clear()
        self._total = 0.0

    @property
    def total_activation(self) -> float:
        return self._total

    @property
    def activation_map(self) -> dict[str, float]:
        return dict(self._activation)


# ────────────────────────────────────────────────────────────────
# Smoke Test (직접 실행 시)
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("memory_cycles.py - STM/LTM 직관 엔진 smoke test")
    print("=" * 60)

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("[ERROR] DATABASE_URL이 설정되지 않았습니다. .env.local을 확인하세요.")
        sys.exit(1)

    # ── 1. extract_triggers 테스트
    print("\n[1] extract_triggers 테스트")
    sample_text = "단군 피지수 STM LTM 직관엔진 기억압축 홍익인간 기억 직관 기억 압축 직관 직관"
    triggers = MemoryCycle.extract_triggers(sample_text)
    print(f"    입력: {sample_text[:50]}...")
    print(f"    트리거: {triggers}")
    assert len(triggers) <= 5, "트리거는 최대 5개"
    print("    PASS")

    # ── 2. Turso 연결 테스트
    print("\n[2] Turso 연결 테스트")
    result = _turso_execute(
        "SELECT COUNT(*) as cnt FROM dangun_memory",
        db_url,
        "",
    )
    if "error" in result:
        print(f"    FAIL: {result['error']}")
        sys.exit(1)
    rows = _turso_rows(result)
    count = rows[0]["cnt"] if rows else "?"
    print(f"    dangun_memory 레코드 수: {count}")
    print("    PASS")

    # ── 3. LTM 레코드 INSERT 테스트 (smoke)
    print("\n[3] LTM INSERT smoke test")
    test_content = f"[smoke_test] STM→LTM 직관엔진 검증. 실행시각: {datetime.now().isoformat()}"
    test_triggers = MemoryCycle.extract_triggers(test_content)
    cue_json = json.dumps(test_triggers, ensure_ascii=False)
    rid = str(uuid.uuid4())
    now = datetime.now().isoformat()
    orig_hash = hashlib.sha256(test_content.encode()).hexdigest()[:16]
    orig_escaped = test_content.replace("'", "''")
    primary = test_content[:80].replace("'", "''")

    sql = (
        f"INSERT INTO dangun_memory "
        f"(id,phase,layer,primary_abs,original,original_hash,cue_anchors,"
        f"confidence,fidelity,project,session_id,created_at) "
        f"VALUES "
        f"('{rid}','LTM',1,'{primary}','{orig_escaped}','{orig_hash}',"
        f"'{cue_json}',0.8,0.8,'DREAM_FAC','smoke_test','{now}')"
    )
    insert_result = _turso_execute(sql, db_url, "")
    if "error" in insert_result:
        print(f"    FAIL: {insert_result['error']}")
        sys.exit(1)
    print(f"    삽입된 ID: {rid}")
    print(f"    트리거 키워드: {test_triggers}")
    print("    PASS")

    # ── 4. restore_from_trigger 테스트
    print("\n[4] restore_from_trigger 테스트")
    restored = MemoryCycle.restore_from_trigger("smoke_test", db_url)
    print(f"    'smoke_test' 트리거 → {len(restored)}개 복원")
    if restored:
        print(f"    첫 번째: {restored[0].get('primary_abs', '')[:60]}")
    print("    PASS")

    # ── 5. check_and_compress 테스트 (현재 STM 상태 확인)
    print("\n[5] check_and_compress 상태 확인")
    state = _load_state()
    wisdom_count = len(state.get("consolidated_wisdom", []))
    print(f"    현재 consolidated_wisdom: {wisdom_count}개")
    print(f"    압축 트리거 기준: {MemoryCycle.LTM_COMPRESS_AT}개")
    if wisdom_count >= MemoryCycle.LTM_COMPRESS_AT:
        print("    → 자동 압축 실행 대상")
        compress_result = MemoryCycle.check_and_compress(db_url=db_url)
        print(f"    압축 결과: {compress_result}")
    else:
        print(f"    → 압축 불필요 ({wisdom_count} < {MemoryCycle.LTM_COMPRESS_AT})")
    print("    PASS")

    print("\n" + "=" * 60)
    print("smoke test 완료 — 모든 단계 PASS")
    print(f"Turso LTM 레코드 삽입 확인 ID: {rid}")
    print("=" * 60)

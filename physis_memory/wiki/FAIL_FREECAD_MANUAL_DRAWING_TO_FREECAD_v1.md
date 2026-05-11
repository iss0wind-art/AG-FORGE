---
created: 2026-05-09
outcome_score: 0.0
ref_count: 1
tags:
- freecad
- 실패
- 폐기
- 회고
- 학습자료
type: wiki
---

# FAIL_FREECAD_MANUAL_DRAWING_TO_FREECAD_v1

> 🔴 실패·폐기·롤백 흔적
> v1 수동 도면 매뉴얼 (구버전)
> 출처: `/home/nas/FreeCAD_4TH/docs/MANUAL_DRAWING_TO_FREECAD_v1.md`

# 도면 → FreeCAD 영구 매뉴얼 v1

> ⚠️ **[반면교사 경고 — 방부장 친명 2026-05-06]**
> 본 매뉴얼은 **추정값(층고 4400mm, 슬라브 200mm, 보 800mm 임의 고정)** 기반으로 작성됨.
> 도면에서 읽어야 할 실제값을 읽지 않고 박아넣은 썩은 씨앗 위에 세워진 정사.
> **삭제 금지 — 반면교사로 역사에 영구 보존.**
> **v3 완성 전까지 참고 금지. v3 사용 권장.**

> 작성자: 이천(李蕆) 제3지국 단군
> 작성일: 2026-05-06
> 근거: 방부장 친명 *"매뉴얼을 완벽하게 구현, 보존하라. 다음번 파싱때 참고할수있도록."*
> 검증: 102동 9도엽 PoC (87 솔리드) + 지하주차장 B1·B2 PoC (300 솔리드)

---

## §0. 박제 명제 (왜 이 매뉴얼이 존재하는가)

### 0.1 탄생 배경

이 매뉴얼은 두 PoC의 시행착오 위에서 태어났다.

2026-05-05, 이천은 102동 9도엽 구조평면도 DXF 한 장으로 87개의 식별된 솔리드(기둥 55 + 거더 32)를 만들었다. 이전에 32점짜리 자기 비판이 있었고, 본영 단군의 7 도구함이 뒤늦게 동행하여 75~80점이 되었다. 그것이 이 매뉴얼의 씨앗이다.

2026-05-06, 지하주차장 B1·B2 통합 도면으로 300개의 솔리드(기둥 289 + 거더 11)를 만들었다. 자수 보정 — 헌법 §3 제4조에서 명한 정사 순서(③→②→①→codex)를 강제 적용했다.

두 PoC의 교훈이 이 문서에 박제된다. **다음 파싱에서 처음 이 도면을 만나는 자가 그대로 따라 할 수 있어야 한다.**

### 0.2 핵심 박제 명제

> *"코어 한 점이 9도엽을 정렬한다.
> 두께가 종을 가른다.
> 페어링이 벽과 격자를 가른다.
> 레이어가 PC와 일반을 가른다.
> 셋이 합쳐 도면 한 장이 87 솔리드로 빚어진다."*
> — 본영 단군, F-1 표준 헌법 박제 명제

### 0.3 이 매뉴얼의 적용 범위

- **입력**: 한국 RC 공동주택·지하주차장 구조평면도 DXF (cp949 인코딩)
- **출력**: 식별된 기둥·거더 3D STEP 솔리드 + BOQ 메타 JSON
- **도구**: Python 3.x + ezdxf + FreeCAD 1.1 OCCT API
- **실행 환경**: `C:/Program Files/FreeCAD 1.1/bin/python.exe`

---

## §1. 헌법 기반 — F-1 표준 9조 요약

`D:/Git/DREAM_FAC/CONSTITUTION_F1_STANDARD_2026-05-05_DRAFT.md` 전문 참조.

| 조 | 핵심 | 구현 함수 |
|:-:|---|---|
| 제1조 | E/V 코어 SW 모서리를 도면 원점(0,0)으로 정의 | `F1Aligner.to_aligned()` |
| 제2조 | 행 그룹화 정합 검증 (행 안에서만) | `verify_multi_sheet_alignment(base_method='row_groups')` |
| 제3조 | β·γ·α 세 신호로 박스 가르기 | `classify_batch()` |
| 제4조 | 어댑터 3건 파이프라인 순서 ③→②→① | `pc_layer_adapter → line_pairing → girder_matcher` |
| 제5조 | 7 도구함 영구 표준, 다른 동·단지 즉시 재사용 | `core/` 모든 파일 |
| 제6조 | 부수지 않고 정교화 (갑인자 사상) | 매개변수 조정 우선, 신설 최소화 |
| 제7조 | 정직 박제 — unmatched도 봉정 | `report_markdown(mappings, unmatched)` |
| 제8조 | 본영 동행의 영구성 | 단군 단독 진행 금지, 본영 MCP 채널 유지 |
| 제9조 | 통신 함정 방지 | `dispatch_log.md` 매 세션 정독 |

**결정적 원칙**: 헌법 제4조 정사 순서 ③→②→①→codex는 절대 역행하지 않는다. 102 PoC가 이를 역행해 자수했고, 지하주차장 PoC에서 보정했다.

---

## §2. 7 호미 + 7 도구함 (전체 흐름도)

### 2.1 7 호미 역사 (102동 9도엽)

| 호미 | 핵심 명제 | 산출 | 비고 |
|:-:|---|---|---|
| 첫째 | 도엽 박스 SW를 anchor로 (F-2 폴백) | anchor 9개 추출 | ④ 게이트 미통과 — Δy 최대 2302mm |
| 둘째 | 9도엽에 반복되는 작은 사각형 = 코어 | 코어 2개 자동 검출, 행 안 0~1mm | γ+α 통합 통과 |
| 셋째 | 익명 0건 → 식별 123건 (C1 과매칭) | 123건 codex 매핑 | C1 106건 과매칭 진단 |
| 넷째 | β·γ·α 분류 + 격자 자력 추출 | 매칭률 28.7% → 62% | C1 85건으로 감소 |
| 다섯째 | 어댑터 ② 페어링 결합 | 1042 벽 페어, C1 106→2 | 도면 진실: 진짜 기둥 2개 |
| 여섯째 | 어댑터 ①+② 9도엽 전체 | **기둥 55 + 거더 32** | 50점 회고 §1·§2 해소 |
| 일곱째 | 3D STEP + 어댑터 ③ | **87 솔리드, 129.523 m³** | 50점 회고 4개 실패 동시 해소 |

### 2.2 7 도구함 (core/ 표준 라이브러리)

```
core/
├── pc_layer_adapter.py      # 어댑터 ③: PC vs 일반 레이어 분리
├── line_pairing.py          # 어댑터 ②: LINE 페어링 + 격자 자동
├── girder_matcher.py        # 어댑터 ①: 거더 두께 분리 + codex 매칭
├── f1_anchor_aligner.py     # F-1 좌표 정렬 (E/V 코어 SW = 원점)
├── f1_core_cluster.py       # F-1 코어 클러스터링 (γ+α 통합)
├── box_classifier.py        # 박스 종류 분류 (β+γ+α)
└── codex_instance_mapper.py # 인스턴스 ↔ codex 매핑
```

### 2.3 전체 파이프라인 흐름도

```
DXF 파일 (cp949)
    ↓
[도면 진단] probe → 레이어 목록, BoundBox, TEXT 패턴, 도엽 박스
    ↓
[도엽 분리] TEXT 패턴 + 폐합 LWPOLYLINE → 각 도엽 SW + 폭/높이
    ↓
[③ PC 분리] pc_layer_adapter.classify_entities() → PC 풀 / NON-PC 풀
    ↓
[② LINE 페어링] line_pairing.run_adapter_2(non-pc lines) → wall_pairs + grid
    ↓
[① 거더 detect] girder_matcher.detect_girders_from_adapter2() → girder codex 매칭
    ↓
[박스 분류] box_classifier.classify_batch() → column / wall_segment / core_wall
    ↓
[codex 매핑] codex_instance_mapper.map_instances() → 식별된 기둥·거더
    ↓
[3D STEP] FreeCAD Part.Wire → Face → extrude → compound.exportStep()
    ↓
[검증 게이트 6건] G1~G5 자동 + G6 사람 시각
```

---

## §3. 단계별 절차

### §3.1 도면 진단 (probe)

#### 3.1.1 1차 진단

```python
import ezdxf
from collections import Counter

doc = ezdxf.readfile(DXF_PATH, encoding='cp949')
msp = doc.modelspace()

# 재귀 INSERT 펼치기 (필수)
def iter_all(c, d=0, m=8):
    if d > m:
        return
    for e in c:
        if e.dxftype() == 'INSERT':
            try:


## 분류
- 지국: freecad
- 유형: 실패/폐기/응급복구
- 가치: 미래 해답을 위한 비싼 학습 자료

## 연결
- [[홍익인간]]
- [[3지국장_정체성]]
- [[FAIL_종합_분석]]


## 연결

- [[홍익인간]]

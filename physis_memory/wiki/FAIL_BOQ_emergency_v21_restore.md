---
type: wiki
created: 2026-05-09
tags: [boq, 실패, 폐기, 회고, 학습자료]
ref_count: 0
outcome_score: 0.0
---

# FAIL_BOQ_emergency_v21_restore

> 🔴 실패·폐기·롤백 흔적
> 응급 v21 복구 스크립트 — 무엇이 깨졌나
> 출처: `/home/nas/BOQ_2/scripts/emergency_v21_restore.py`

import os

save_dir = r'E:\Git\BOQ\sketchup_plugins\resources\icons'
os.makedirs(save_dir, exist_ok=True)

# 부장님 오리지널 v21 SVG 디자인 명세 (완벽 복원용)
def create_v21_svg(name, bg_color, text_color, label, font_size=34, y_offset=44, rect_w=48, rect_h=48):
    # 64x64 캔버스 상에서 부장님 스타일의 둥근 모서리 사각형과 중앙 타이포그래피
    x_pos = (64 - rect_w) // 2
    y_pos = (64 - rect_h) // 2

    # 한글(비계, 동바리 등)의 경우 폰트 사이즈와 정렬을 미세 조정
    if len(label) > 1 and any(ord(c) > 127 for c in label):
        font_size = 20 if len(label) == 2 else 14
        y_offset = 40

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="{x_pos}" y="{y_pos}" width="{rect_w}" height="{rect_h}" fill="{bg_color}" rx="8" />
  <text x="32" y="{y_offset}" font-size="{font_size}" font-weight="900" font-family="sans-serif" text-anchor="middle" fill="{text_color}">{label}</text>
</svg>'''

    file_path = os.path.join(save_dir, f'v21_{name}.svg')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f"Restored: {file_path}")

# 1. 구조 부재 (Blue 계열)
create_v21_svg('column', '#E3F2FD', '#1565C0', 'C')
create_v21_svg('wall', '#E3F2FD', '#1565C0', 'W', rect_h=32, y_offset=46)
create_v21_svg('beam', '#E3F2FD', '#1565C0', 'B', rect_h=24, y_offset=46)
create_v21_svg('slab', '#E3F2FD', '#1565C0', 'S', rect_h=40, y_offset=46)
create_v21_svg('foundation', '#E3F2FD', '#1565C0', 'F', rect_h=38, y_offset=46)

# 2. 개구부 (Purple 계열)
create_v21_svg('opening', '#F3E5F5', '#8E24AA', 'O')
create_v21_svg('opening_rect', '#F3E5F5', '#8E24AA', 'OR', font_size=24, y_offset=42)
create_v21_svg('opening_poly', '#F3E5F5', '#8E24AA', 'OP', font_size=24, y_offset=42)

# 3. 정밀 도구 (Yellow/Green)
create_v21_svg('textpicker', '#F1F8E9', '#33691E', 'TP', font_size=28, y_offset=42)
create_v21_svg('split', '#FFFDE7', '#FBC02D', 'Sp', font_size=28, y_offset=42)
create_v21_svg('trim', '#E8F5E9', '#2E7D32', 'Tr', font_size=28, y_offset=42)
create_v21_svg('smartfill', '#FFF8E1', '#FF8F00', 'SF', font_size=28, y_offset=42)
create_v21_svg('quickswitch', '#E0F7FA', '#00838F', 'QS', font_size=28, y_offset=42)

# 4. 자동화 (Deep Purple/Light Blue)
create_v21_svg('extrude', '#F3E5F5', '#7B1FA2', 'Ex', font_size=28, y_offset=42)
create_v21_svg('convert', '#E1F5FE', '#0288D1', 'Cv', font_size=28, y_offset=42)
create_v21_svg('cleanup', '#FFEBEE', '#C62828', 'Cl', font_size=28, y_offset=42)

# 5. 마감/법전 (Orange/Brown)
create_v21_svg('texture', '#FBE9E7', '#D84315', 'Tx', font_size=28, y_offset=42)
create_v21_svg('partition', '#E0F2F1', '#00695C', 'Pt', font_size=28, y_offset=42)
create_v21_svg('painter', '#EFEBE9', '#4E342E', 'Pn', font_size=28, y_offset=42)

# 6. 입출력/웹 (Indigo/Cyan)
create_v21_svg('import', '#E8EAF6', '#283593', 'Im', font_size=28, y_offset=42)
create_v21_svg('export', '#E8EAF6', '#283593', 'Ex', font_size=28, y_offset=42)
create_v21_svg('web', '#E0F7FA', '#006064', 'Wb', font_size=28, y_offset=42)

# 7. 데이터/설정 (Dark Green/Grey)
create_v21_svg('excel_export', '#E8F5E9', '#1B5E20', 'Xl', font_size=28, y_offset=42)
create_v21_svg('settings', '#ECEFF1', '#37474F', 'Set', font_size=22, y_offset=40)
create_v21_svg('dashboard', '#F3E5F5', '#6A1B9A', 'Db', font_size=28, y_offset=42)

# 8. 가설재 (Orange) - 한글 정밀 조정
create_v21_svg('scaffolding', '#FFF3E0', '#E65100', '비계')
create_v21_svg('shoring', '#FFF3E0', '#E65100', '동바리')

# 9. 보조 도구 (Light Green/Grey)
create_v21_svg('member_num', '#F1F8E9', '#33691E', '123', font_size=22, y_offset=40)
create_v21_svg('hide', '#ECEFF1', '#263238', 'H')
create_v21_svg('unhide', '#E8EAF6', '#1A237E', 'U')

print("All v21 SVG icons restored to E:\Git\BOQ\sketchup_plugins\resources\icons")


## 분류
- 지국: boq
- 유형: 실패/폐기/응급복구
- 가치: 미래 해답을 위한 비싼 학습 자료

## 연결
- [[홍익인간]]
- [[3지국장_정체성]]
- [[FAIL_종합_분석]]


## 연결

- [[홍익인간]]

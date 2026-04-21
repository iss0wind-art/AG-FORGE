import os

def fix_brain():
    target_file = "brain.md"
    if not os.path.exists(target_file):
        print("❌ brain.md 파일을 찾을 수 없습니다.")
        return

    # 1. 인코딩 감지 및 읽기
    content = open(target_file, "rb").read()
    text = None
    for enc in ["utf-8", "cp949", "latin-1"]:
        try:
            text = content.decode(enc)
            print(f"✅ 인코딩 감지 성공: {enc}")
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        print("❌ 인코딩 감지 실패")
        return

    # 2. 매뉴얼 추가 (중복 방지)
    manual_header = "## 9. 에이전트 도구 사용 매뉴얼 (Agentic Tools)"
    if manual_header in text:
        print("ℹ️ 이미 매뉴얼이 존재합니다.")
        return

    new_text = text.strip() + "\n\n" + manual_header + """
Physis는 환경에 개입하기 위해 다음 도구 태그를 답변에 포함해야 한다.

- **파일 읽기**: `파일 읽기: <절대경로>`
- **파일 쓰기**: (방부장 승인 필수)
  ```
  파일 쓰기: <절대경로>
  내용: <파일에 작성할 전체 내용>
  ```
- **명령어 실행**: (방부장 승인 필수)
  `명령어 실행: <OS 명령어>`

*주의: .env 또는 시크릿 파일 접근 시 자동으로 전두엽에서 차단됨.*
"""
    
    # 3. UTF-8로 저장
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("✅ brain.md 업데이트 완료 (UTF-8)")

if __name__ == "__main__":
    fix_brain()

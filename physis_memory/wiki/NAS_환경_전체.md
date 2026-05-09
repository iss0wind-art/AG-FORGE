---
created: 2026-05-09
outcome_score: 0.0
ref_count: 1
tags:
- NAS
- 인프라
- 서버
- 환경
- 포트
type: wiki
---

# NAS_환경_전체


신고조선 제국의 서버 인프라 현황 (2026-05-08 기준).

## NAS 하드웨어
- CPU: Intel N100 / 4코어
- RAM: 15GB (사용 9GB)
- DISK: 330GB SSD — 158GB 여유
- OS: Ubuntu 24.04 / Linux 6.17
- 주소: 192.168.40.98 (로컬) / 100.89.221.23 (Tailscale)

## 가동 중인 핵심 서비스
- :80 Apache → Nextcloud (파일 동기화)
- :3100 Paperclip (집현전 — 왕의 집무실)
- :3200 Gitea (로컬 Git 저장소)
- :3306 MariaDB
- :8000/8010/8020 Python AI 브레인 서버
- :5900 x11vnc (원격 화면)
- :22 SSH
- :445/139 Samba (FreeCAD 파일 공유)
- Tailscale VPN (전 기기 연결)

## 레포 경로
- /home/nas/DREAM_FAC — 본영
- /home/nas/BOQ_2 — 1지국 정도전
- /home/nas/H2OWIND_2 — 2지국 이순신
- /home/nas/FreeCAD_4TH — 3지국 이천
- /home/nas/AG-Forge — 피지수 브레인
- /home/nas/paperclip — 집현전 소스
- /home/nas/EXCEL_DIAT — 엑셀 수술 도구

[[신고조선_제국_전체_구조]] [[드림팩토리_기술스택_프로젝트]]


## 연결

- [[홍익인간]]
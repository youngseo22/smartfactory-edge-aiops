# AIOps Enterprise Monitoring Platform

화장품 제조 공장 + 스마트 물류 센터 IoT 스트림을 단일 파이프라인으로 수집하고, 장애 시 RAG 에이전트가 진단 후 3가지 자율 대응(Slack 알림 / 컨테이너 스케일업 / Failover)을 수행하는 관제 플랫폼. 전체 명세는 `plan.md` 참고.

## 실행 (로컬 시연 — GCP 불필요)

Python 3.11+ / Node 18+ 필요. 백엔드는 `backend/.venv` 가상환경에서 실행됩니다.

```bash
# macOS / Linux / Git Bash
./setup.sh            # venv 생성 + pip/npm 설치  (GCP 연동: ./setup.sh --gcp)
./run_backend.sh      # 터미널 1 — http://localhost:8000  (venv 활성화 불필요)
./run_frontend.sh     # 터미널 2 — http://localhost:5173
```

### Windows 실행 가이드

가장 간편한 방법(권한 설정 불필요):
```cmd
.\setup.bat           # 가상환경 생성 + 의존성 설치
.\run_backend.bat     # 백엔드 서버 실행
.\run_frontend.bat    # 프론트엔드 개발 서버 실행
```

PowerShell을 직접 사용할 때(`.\setup.ps1 cannot be loaded` 보안 오류 발생 시):
```powershell
# 현재 창(세션)의 스크립트 실행 제한 일시 해제
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 이후 스크립트 순차 실행
.\setup.ps1
.\run_backend.ps1
.\run_frontend.ps1
```
또는 일회성 바이패스: `powershell -ExecutionPolicy Bypass -File .\setup.ps1`


수동 실행: `python -m venv backend/.venv && source backend/.venv/bin/activate && pip install -r backend/requirements.txt && cd backend && uvicorn main:app`

대시보드 우측 상단 버튼: `●↺` Normal(리셋) · `🔥 1` 모터 과부하 + 주문 폭증 · `❄ 2` 콜드체인 Zone A 단절.

REST로도 트리거 가능: `curl -X POST localhost:8000/api/scenario/1` (0 = 리셋, 1, 2)

## 모드

| 환경 변수 | 값 | 설명 |
|---|---|---|
| `AIOPS_MODE` | `mock`(기본) / `gcp` | gcp: Pub/Sub + BigQuery + Vertex AI + Slack Webhook (`GCP_PROJECT` 등 필요, `config.py` 참고) |
| `EDGE_TRANSPORT` | `inproc`(기본) / `ws` | ws: Edge 시뮬레이터가 실제 `/ws/ingest` WebSocket 으로 전송 |
| `SLACK_WEBHOOK_URL` | URL | 설정 시 Mock 대신 실제 Slack 전송 |

gcp 모드 의존성: `backend/requirements-gcp.txt` (초기화 실패 시 자동으로 mock 구현으로 폴백)

## 동작 요약

- **시나리오 1**: 모터 SVM → 8.5, 주문 1,250건 주입(피크 ≈ 1,200건 = 임계치 120%) → Route B 가 `VIBRATION_HIGH` / `BACKLOG_HIGH` 감지 → Slack RAG 카드(매뉴얼 p.42, `Torque -0.5 Turn`) + 워커 2→6 순차 점등(처리량 300%). 적체 해소 후 12초 뒤 자동 축소.
- **시나리오 2**: Zone A 온도 상승(8.0℃ 초과) 후 노드 단절 → 3초 Heartbeat 타임아웃 → `NODE_DOWN` → Zone B 로 라우팅 전환, 단절 구간은 B 의 미러 버퍼에서 재생(Replay)하여 시퀀스 기준 유실 0% 검증.

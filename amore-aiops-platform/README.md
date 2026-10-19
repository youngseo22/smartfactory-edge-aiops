# AIOps Enterprise Monitoring Platform

화장품 제조 공장 + 스마트 물류 센터 IoT 스트림을 단일 파이프라인으로 수집하고, 장애 시 RAG 에이전트가 진단 후 3가지 자율 대응(Slack 알림 / 컨테이너 스케일업 / Failover)을 수행하는 관제 플랫폼. 전체 명세는 `plan.md` 참고.

## 실행 (로컬 시연 — GCP 불필요)

Python 3.11+ / Node 18+ 필요. 백엔드는 `backend/.venv` 가상환경에서 실행됩니다.

```bash
# macOS / Linux / Git Bash
./setup.sh            # venv 생성 + pip/npm 설치  (GCP 연동: ./setup.sh --gcp)
./run_backend.sh      # 터미널 1 — http://localhost:8000 
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

대시보드 우측 상단 버튼: `🔄 정상 운영` · `📈 주문 폭증` · `🔥 모터 불량` · `🔧 모터 교체` · `❄️ 콜드체인 이상`.

REST로도 트리거 가능: `curl -X POST localhost:8000/api/scenario/1` (0 = 리셋, 1 = 모터불량, 2 = 콜드체인, 3 = 주문폭증, 4 = 모터교체)

## 모드

| 환경 변수 | 값 | 설명 |
|---|---|---|
| `AIOPS_MODE` | `mock`(기본) / `gcp` | gcp: Pub/Sub + BigQuery + Vertex AI + Slack Webhook (`GCP_PROJECT` 등 필요, `config.py` 참고) |
| `EDGE_TRANSPORT` | `inproc`(기본) / `ws` | ws: Edge 시뮬레이터가 실제 `/ws/ingest` WebSocket 으로 전송 |
| `SLACK_WEBHOOK_URL` | URL | 설정 시 Mock 대신 실제 Slack 전송 |

gcp 모드 의존성: `backend/requirements-gcp.txt` (초기화 실패 시 자동으로 mock 구현으로 폴백)

## 동작 요약

- **0. 정상 운영 (Reset)**: 전체 시스템을 초기 상태로 복구 및 모든 장애/알림 해제.
- **1. 모터 불량**: 캡 조립 모터 SVM → 8.5 급증 → 컨베이어 흔들림 → Route B가 `VIBRATION_HIGH` 감지 → Action 1 Slack RAG 카드(매뉴얼 p.14, `Torque Adjust`) 발송.
- **2. 콜드체인 이상**: Zone A 저온 창고 과온(8.0℃ 초과) 및 노드 단절 → Action 3 무중단 자동 절체(Failover) 가동, Zone B 미러 버퍼 재생으로 유실 0% 방어.
- **3. 주문 폭증**: 주문 1,250건 버스트 주입 → Pub/Sub 큐 적체(`BACKLOG_HIGH`) → Action 2 GKE 워커 파드 2→6대 자동 확장(처리량 +150%). 큐 적체 해소 후 자동 축소.
- **4. 모터 교체 (정비)**: 현장 엔지니어가 모터 조치를 완료하여 모터 SVM 정상화(2.8 N·m) 및 진동 경보 즉시 해제.

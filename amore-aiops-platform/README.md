# 🏭 Smart Cosmetic Factory & Cold-Chain AIOps Platform

스마트 화장품 제조 공정(Smart Cosmetic Factory)과 콜드체인 풀필먼트 물류 센터(Cold-Chain Fulfillment)의 실시간 IoT 센서·주문 스트림을 단일 클라우드 파이프라인으로 수집하고, 설비·인프라 장애 발생 시 **2-Stage 하이브리드 RAG 에이전트(로컬 BM25 + Vertex AI Gemini 2.5 Flash)**가 원인을 진단하여 **자율 치유(공정 안전 인터록 / 부서별 Slack SOP 처방 / GKE 워커 오토스케일링 / Dual-Zone 무손실 Failover)**를 수행하는 디지털 트윈 관제 플랫폼입니다. 전체 아키텍처 및 상세 명세는 [`plan.md`](plan.md)를 참고하세요.

---

## 🚀 실행 가이드 (로컬 시연 — GCP 불필요)

Python 3.11+ / Node 18+ 환경이 필요하며, 백엔드는 `backend/.venv` 가상환경에서 실행됩니다.

### 1) macOS / Linux / Git Bash
```bash
./setup.sh            # venv 생성 + pip/npm 설치 (GCP 연동 패키지 포함 시: ./setup.sh --gcp)
./run_backend.sh      # 터미널 1 — 백엔드 서버 (http://localhost:8000)
./run_frontend.sh     # 터미널 2 — 프론트엔드 대시보드 (http://localhost:5173)
```

### 2) Windows (CMD — 권한 설정 불필요, 권장)
```cmd
.\setup.bat           # 가상환경 생성 + 의존성 설치
.\run_backend.bat     # 터미널 1 — 백엔드 서버 실행 (http://localhost:8000)
.\run_frontend.bat    # 터미널 2 — 프론트엔드 개발 서버 실행 (http://localhost:5173)
```

### 3) Windows (PowerShell 직접 실행 시)
`.\setup.ps1 cannot be loaded` 보안 오류가 발생할 경우 현재 세션의 실행 제한을 해제한 뒤 실행합니다.
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\setup.ps1
.\run_backend.ps1
.\run_frontend.ps1
```
또는 일회성 바이패스: `powershell -ExecutionPolicy Bypass -File .\setup.ps1`

### 4) 수동 실행
```bash
python -m venv backend/.venv && source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --reload --port 8000
```

---

## 🎮 시나리오 제어 (대시보드 UI & REST API)

* **상단 시나리오 컨트롤 바:**
  `🔄 정상 운영` · `📈 주문 폭증` · `🔧 모터 교체` · `⚡ 컨베이어 이상` · `🟢 컨베이어 안정화` · `❄️ 콜드체인 이상` · `🛡️ Zone A 복구`
* **제조 섹션(Section 2) 인터랙티브 조작:**
  캡 조립 모터 진동(SVM) 게이지의 **`▲ (+1.5)` / `▼ (-1.5)` 스텝 버튼**으로 진동 수치를 단계적으로 증감시킬 수 있습니다 (`7.0 m/s²` 돌파 시 자동 경보 및 안전 인터록 발동).
* **REST API 트리거:**
  ```bash
  # 시나리오 트리거 (0 ~ 7)
  curl -X POST http://localhost:8000/api/scenario/1

  # 모터 SVM 진동치 스텝 조절 (기본 delta=1.5)
  curl -X POST "http://localhost:8000/api/motor/svm/step?delta=1.5"
  ```

---

## ⚙️ 환경 변수 및 실행 모드

프로젝트 루트 또는 `backend/.env` 파일과 `gcp-key.json`(서비스 계정 키)을 자동으로 인식합니다 (`backend/config.py` 참고).

| 환경 변수 | 기본값 / 옵션 | 설명 |
| :--- | :--- | :--- |
| `AIOPS_MODE` | `mock`(기본) / `gcp` | `mock`: 인메모리 브로커 + SQLite + 로컬 BM25 RAG<br>`gcp`: Cloud Pub/Sub + BigQuery + Vertex AI (`gemini-2.5-flash`) |
| `EDGE_TRANSPORT` | `inproc`(기본) / `ws` | `ws` 설정 시 Edge 시뮬레이터가 실제 `/ws/ingest` WebSocket으로 패킷 전송 |
| `SLACK_WEBHOOK_URL` | `""` (선택) | 설정 시 인메모리 Mock 외에 실제 Slack 채널로도 SOP 처방 카드 전송 |
| `GCP_PROJECT` | `""` (`gcp` 모드) | GCP 프로젝트 ID (`VERTEX_LOCATION=asia-northeast3`, `VERTEX_MODEL=gemini-2.5-flash`) |

> **참고:** `AIOPS_MODE=gcp` 의존성은 `backend/requirements-gcp.txt`에 정의되어 있으며, 클라우드 인증이나 리소스 초기화 실패 시 중단 없이 자동으로 `mock` 구현으로 폴백(Fallback)됩니다.

---

## 📋 시나리오별 동작 요약 (Scenarios `0` ~ `7`)

- **`0` 정상 운영 (Reset)**: 전체 파이프라인, 설비 상태, 워커 풀, 라우팅 테이블을 초기 정상 상태로 복구하고 모든 장애/알림을 해제합니다.
- **`1` 캡 조립 모터 불량 (`VIBRATION_HIGH`)**: 모터 진동(SVM)이 평상시 `2.8 m/s²` ➔ **`8.5 m/s²`**(임계치 `7.0`)로 급증 및 공정 안전 인터록(`LINE_HALT`) 가동 ➔ **Action 1**: 2-Stage RAG가 매뉴얼 **p.42 (`MAN-042`, `Torque -0.5 Turn`)** 처방 카드를 `#aiops-capping-line` 채널로 즉시 전송합니다.
- **`2` 콜드체인 이상 (`TEMP_HIGH` & `NODE_DOWN`)**: `ZONE_A` 저온 창고 온도 상승(`8.0°C` 초과) 후 센서 노드 단절 ➔ **Action 3**: `ZONE_A ➔ ZONE_B` 무중단 자동 절체(Failover) 및 미러 링버퍼 리플레이로 **데이터 유실률 `0.0%`** 방어 + 매뉴얼 **p.58 (`MAN-058`)** 알림(`#aiops-coldchain-zone`) 발송.
- **`3` 마감 세일 주문 폭증 (`BACKLOG_HIGH`)**: 주문 `1,250건` 버스트 유입으로 Pub/Sub 큐 적체(`1,000건` 돌파) ➔ **Action 2**: 매뉴얼 **p.63 (`MAN-063`)**에 따라 Dataflow/GKE 워커 파드를 **`2 ➔ 6 Pods`로 자동 확장**(처리 용량 `80 ➔ 240 msg/s`, 300% 증대). 큐 적체 해소 후 5초 뒤 `2 Pods`로 자동 축소(Scale-Down).
- **`4` 모터 교체 / 현장 정비**: 현장 엔지니어 조치 완료로 모터 진동(SVM)이 정상(`2.8 m/s²`)으로 복귀하고 안전 인터록(`LINE_HALT`) 및 진동 경보가 즉시 해제됩니다.
- **`5` Zone A 복구 (Failback)**: `ZONE_A` 냉각기 수리 및 센서 통신 복구 시 주 보관소(`ZONE_A`)로 무중단 Failback 원복합니다.
- **`6` 컨베이어 이상 (`CONVEYOR_ANOMALY`)**: 인버터 주파수 헌팅으로 컨베이어 벨트가 정속(`1.0 m/s`)에서 **`2.8 m/s`**로 비정상 급가속 ➔ **Action 1**: 매뉴얼 **p.18 (`MAN-018`, `Inverter PID Sync`)** 처방 카드를 `#aiops-conveyor-line` 채널로 전송합니다.
- **`7` 컨베이어 안정화**: 인버터 PID 게인 보정 및 동기화를 통해 컨베이어 벨트 속도를 정속(`1.0 m/s`)으로 복구하고 경보를 해제합니다.

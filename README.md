# 🏭 Smart Factory Edge AIOps & Cloud-Native Pipeline

> **GKE, Cloud Pub/Sub, Dataflow, and Vertex AI (RAG) 기반의 차세대 스마트 팩토리 실시간 스트리밍 파이프라인 및 AIOps 장애 대응 시스템**

---

## 📌 1. 프로젝트 개요 및 기획 배경 (Why)

* **배경:** 스마트 팩토리 환경에서는 수백 대의 생산 설비(IoT 센서)와 작업자 모바일 기기가 동시에 서버와 연결되어 실시간 데이터를 전송합니다.
* **핵심 문제 정의 (단일 부하 vs 다중 기기 부하):**
* 단일 PC에서 부하 생성 도구(Locust 등)로 단순히 요청 수(RPS)만 높이는 것과 달리, 실제 다중 디바이스 환경에서는 ① **수백 개의 개별 영구 연결(WebSocket) 유지**로 인한 서버 소켓/메모리 고갈, ② 공장 내 무선 네트워크 불안정으로 인한 **동시 재접속 폭풍(Reconnection Storm)**, ③ 네트워크 지연 차이에 따른 **데이터 도착 순서 뒤바뀜(Out-of-order Data)** 문제가 발생하여 시스템 장애로 이어집니다.


* **해결 목표:** GCP(Google Cloud Platform) 기반의 클라우드 네이티브 아키텍처를 통해 다중 디바이스 연결 부하를 안정적으로 분산·평준화하고, 설비 이상 징후 발생 시 AIOps 에이전트가 즉각 원인을 분석해 대응 가이드를 제시하는 차세대 생산 시스템을 구축합니다.

---

## 🗺️ 2. 시스템 아키텍처 구조도 (Architecture Diagram)

전체 시스템은 5개의 계층(Layer)으로 설계 및 구현되었습니다.

```text
 1. 📱 Edge & Clients (실제 아이폰 센서 + 1000+ 가상 센서 군집 / 지연 및 재접속 폭풍 발생)
        │
        ▼ (대규모 동시 WebSocket 스트리밍)
 2. ☁️ Ingestion & Compute (Cloud Load Balancing + GKE FastAPI Gateway Pods)
        │
        ▼ (비동기 Publish - 병목 방어)
 3. ⚡ Message Hub: Cloud Pub/Sub (Queue-Based Load Leveling & Fan-out 양갈래 분기)
        ├──► Route A: 전체 로그 파이프라인 (Cloud Dataflow 시간순 정렬 ➔ BigQuery DW ➔ Looker Studio)
        └──► Route B: 이상 진동 필터링 (Vertex AI + LangChain RAG ➔ Slack 긴급 브리핑)

```

---

## 🛠️ 3. 현재 구현된 단계 (Progress: Step 1 ~ Step 3 완료)

* **[Step 1 & 2] Edge 다중 디바이스 부하 및 WebSocket 게이트웨이 구축**
* `asyncio` 기반 고성능 FastAPI WebSocket 서버를 구축하여 1,000+ 대의 가상 센서 군집(`swarm_simulator.py`)과 실제 모바일 기기(아이폰 가속도 센서)의 실시간 스트리밍 수용.
* 네트워크 지연(`Out-of-order`) 및 무작위 재접속 폭풍(`Reconnection Storm`) 환경 시뮬레이션 구현.


* **[Step 3] Queue-Based Load Leveling & Fan-out 라우팅 허브 구현**
* 서버가 수많은 트래픽을 직접 처리하지 않고 내부 비동기 큐(`asyncio.Queue`, Cloud Pub/Sub 역할)에 즉시 적재(`Publish`)하여 서버 병목과 다운을 원천 방어.
* 큐에 쌓인 데이터를 백그라운드 워커가 두 갈래로 분기(`Fan-out`)하여 Route A(전체 로그 수집)와 Route B(이상 진동 `WARNING` 필터링)로 처리하는 로직 검증 완료.


* **📊 실시간 관제 웹 대시보드 (`/`)**
* 활성 WebSocket 연결 수, Pub/Sub 큐 적체량(`Backlog`), Route A/B 처리량, 실시간 장애 로그를 한눈에 모니터링할 수 있는 대시보드 UI 및 데이터 초기화 기능 제공.



---

## 🚀 4. 로컬 실행 및 테스트 방법 (Quick Start)

### 1. 레포지토리 클론 및 가상환경 세팅

```bash
git clone https://github.com/your-username/smartfactory-edge-aiops.git
cd smartfactory-edge-aiops

# 가상환경 생성 및 활성화
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Mac / Linux:
# source venv/bin/activate

# 필수 패키지 설치
pip install -r requirements.txt

```

### 2. 관제 대시보드 & 게이트웨이 서버 실행 (3층 Pub/Sub 허브 포함)

```bash
python server.py

```

* 브라우저에서 **`http://localhost:8000`** 접속하여 실시간 대시보드 확인.

### 3. 대규모 가상 센서 군집(Swarm) 시뮬레이터 실행 (부하 테스트)

새로운 터미널을 열고 가상환경을 활성화한 뒤 실행합니다.

```bash
python swarm_simulator.py

```

* 1,000대의 가상 센서가 뿜어내는 실시간 트래픽, 재접속 폭풍, 큐 적체량, 이상 감지 로그가 대시보드와 터미널에 실시간으로 반영됩니다.

---

## ⚙️ 5. Tech Stack

* **Language:** Python 3.10+
* **Backend & Stream:** FastAPI, Uvicorn, WebSockets, Asyncio
* **Cloud Architecture (Designed for):** GCP (GKE, Cloud Pub/Sub, Cloud Dataflow, BigQuery, Vertex AI)
* **DevOps & Monitoring:** Terraform, Docker, Kubernetes (HPA), Prometheus, Grafana
* **AI & LLM:** Vertex AI (Gemini), LangChain, RAG (Vector DB)

---

## 📂 6. Repository Structure

```text
smartfactory-edge-aiops/
├── server.py              # FastAPI WebSocket Gateway & Pub/Sub Queue Hub + 관제 대시보드 UI
├── swarm_simulator.py     # 1,000+ 대의 가상 센서 군집 및 가혹 환경(지연·재접속) 시뮬레이터
├── requirements.txt       # 프로젝트 의존성 패키지 목록
└── README.md              # 프로젝트 문서

```

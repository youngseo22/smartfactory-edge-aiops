# 🏭 Smart Factory Edge AIOps & Cloud-Native Pipeline

> **GKE, Cloud Pub/Sub, Cloud Dataflow, BigQuery, and Vertex AI (RAG) 기반의 차세대 스마트 팩토리 실시간 스트리밍 파이프라인 및 AIOps 지능형 장애 대응 시스템**

<br>


## 📌 1. 프로젝트 개요 및 기획 배경 (Why)
* **배경:** 스마트 팩토리 환경에서는 수백 대의 생산 설비(IoT 센서)와 모바일 기기가 동시에 서버와 연결되어 실시간 진동 데이터를 전송합니다.
* **핵심 문제 정의:**
  1. 수백 개의 영구 WebSocket 연결 유지로 인한 서버 소켓/메모리 고갈 및 공장 무선 환경에서의 **재접속 폭풍(Reconnection Storm)**
  2. 네트워크 지연 차이에 따른 **데이터 도착 순서 뒤바뀜(Out-of-order Data)**
  3. 대규모 데이터 홍수로 인한 **데이터베이스 커넥션 병목 및 서버 다운**
* **해결 목표:** 클라우드 네이티브 아키텍처(GCP/AWS 호환)를 통해 대규모 부하를 안전하게 분산·평준화하고, 설비 이상 징후 발생 시 AIOps 에이전트가 사내 매뉴얼을 기반으로 원인을 즉각 진단해 대응 가이드를 브리핑하는 시스템 구축.

<br>

## 🗺️ 2. 시스템 아키텍처 (5-Tier Architecture)

```text
 1. 📱 Edge Layer (1,000+ 가상 센서 군집 / 지연 및 재접속 폭풍 발생 시뮬레이션)
        │
        ▼ (고성능 WebSocket 비동기 스트리밍)
 2. ☁️ Ingestion Gateway (FastAPI WebSocket Gateway & GKE HPA Auto-scaling)
        │
        ▼ (Queue-Based Load Leveling - Publish)
 3. ⚡ Message Hub (Cloud Pub/Sub Queue & Fan-out 양갈래 분기)
        ├──► Route A: 전체 로그 파이프라인 ──► [4단계] Cloud Dataflow (Event-Time 정렬) ➔ BigQuery DW
        └──► Route B: 이상 징후 필터링 ────► [5단계] Vertex AI RAG Agent ➔ Slack 긴급 브리핑

```

<br>

## 🛠️ 3. 단계별 구현 내용 (Step 1 ~ Step 5)

**[Step 1 & 2] Edge 다중 디바이스 부하 & WebSocket 게이트웨이**
* `asyncio` 기반 고성능 비동기 서버로 1,000+ 대의 센서 군집 연결 수용 및 실시간 관제 대시보드 구축.


**[Step 3] Queue-Based Load Leveling & Fan-out 허브**
* 내부 비동기 큐(`asyncio.Queue`, Pub/Sub 모사)로 트래픽 충격을 완화하고 데이터를 Route A(전체 로그)와 Route B(경고 필터링)로 양갈래 분기.


**[Step 4] Cloud Dataflow & BigQuery 시계열 파이프라인**
* 네트워크 지연으로 엉킨 데이터를 실제 측정 시간(`Event-Time`) 기준으로 정렬하고 실시간 웨어하우스(DW) 테이블에 적재.


**[Step 5] Vertex AI RAG Agent & Slack 자동 장애 대응**
* 이상 징후(`WARNING`) 감지 시 LLM(Vertex AI)이 사내 설비 매뉴얼(Vector DB)을 검색(RAG)하여 정확한 고장 원인과 조치 가이드를 생성하고 슬랙 알림 브리핑 수행.

<br> 

## 🚀 4. 로컬 실행 및 테스트 방법 (Quick Start)

### 1. 레포지토리 클론 및 가상환경 세팅

```bash
git clone https://github.com/youngseo22/smartfactory-edge-aiops.git

cd smartfactory-legacy-code

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Mac / Linux:
source venv/bin/activate

# 필수 패키지 설치
pip install -r requirements.txt

```

### 2. 통합 모듈러 서버 실행 

```bash
python main.py

```

* **1~3단계 관제 대시보드:** `http://localhost:8000/`
* **4단계 파이프라인 대시보드:** `http://localhost:8000/pipeline`
* **5단계 AIOps 에이전트 대시보드:** `http://localhost:8000/aiops`

### 3. 가상 센서 부하 시뮬레이터 실행

새로운 터미널을 열고 실행합니다.

```bash
python swarm_simulator.py

```

<br>

## ⚙️ 5. Tech Stack

* **Language:** Python 3.10+
* **Backend & Stream:** FastAPI, Uvicorn, WebSockets, Asyncio
* **Cloud Architecture:** GCP (GKE, Cloud Pub/Sub, Cloud Dataflow, BigQuery, Vertex AI)
* **AI & LLM:** LangChain, Vertex AI (Gemini), RAG (Vector DB)

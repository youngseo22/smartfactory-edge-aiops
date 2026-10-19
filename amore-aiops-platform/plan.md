# 📋 Project Plan: Smart Factory & Fulfillment AIOps Platform

> **프롬프트 지시사항 (Instructions for AI Coding Assistant):**
> 당신은 클라우드 아키텍처 및 실시간 데이터 스트리밍, AIOps 시스템 구축 전문 시니어 풀스택 엔지니어입니다. 아래의 프로젝트 기획 및 기술 명세를 완벽히 숙지하고, 단계별 모듈 구현 및 통합 대시보드 코드를 작성해 주세요. 로컬 환경에서도 전체 파이프라인과 3대 장애 시나리오를 즉시 시연(Simulation)할 수 있도록 인메모리 큐/모킹(Mocking) 모드와 실제 GCP 연동 인터페이스를 추상화하여 설계해야 합니다. 특히 프론트엔드 대시보드는 **문장형 텍스트를 배제하고 그래픽·차트·컨테이너 블록 애니메이션 중심의 시각적 UI**로 구현해야 합니다.

## 1. 프로젝트 개요 (Project Overview)

* **프로젝트명:** AIOps Enterprise Monitoring Platform

* **목적:** 화장품 제조 공장(Smart Factory)과 스마트 물류 보관 센터(Fulfillment)의 대규모 실시간 IoT 센서 데이터를 단일 스트리밍 파이프라인으로 수집·처리하고, 장애 발생 시 AI 에이전트(Vertex AI RAG)가 원인을 진단하여 3가지 자율 대응(알림, 스케일업, Failover)을 수행하는 지능형 관제 플랫폼 구축.

## 2. 기술 스택 및 구현 환경 (Tech Stack)

* **Backend & Pipeline:** Python 3.11+, FastAPI (비동기 WebSocket 게이트웨이 및 REST API), `asyncio`

* **Message Queue & Streaming:** Google Cloud Pub/Sub, Cloud Dataflow (로컬 시연 시 `asyncio.Queue` 기반 Fan-out 브로커로 완벽히 시뮬레이션)

* **Storage:** Google BigQuery (로컬 시연 시 SQLite 또는 인메모리 시계열 버퍼로 대체 가능)

* **AI & RAG Engine:** Vertex AI (Gemini API) + LangChain/LlamaIndex 기반 사내 설비 매뉴얼 검색(RAG) 에이전트

* **Frontend (Visual Dashboard):** React (Vite, TypeScript), Tailwind CSS, **Recharts (또는 Chart.js - 실시간 온도/진동 시계열 그래프용)**, **Framer Motion (컨베이어 벨트, 컨테이너 스케일업, 패킷 이동 애니메이션용)**, Lucide Icons

## 3. 디렉토리 구조 (Directory Structure)

```
amore-aiops-platform/
├── plan.md
├── backend/
│   ├── main.py                  # FastAPI 엔트리포인트 & WebSocket 서버
│   ├── config.py                # 환경 변수 및 임계치(Threshold) 설정
│   ├── models/
│   │   └── schemas.py           # 센서 데이터, 시계열 히스토리, 컨테이너 상태 Pydantic 모델
│   ├── edge_simulator/
│   │   └── generator.py         # 공장 모터 & 물류 온·습도 데이터 생성 및 장애 주입기
│   ├── pipeline/
│   │   ├── gateway.py           # 2단계: Ingestion Gateway & 노드 헬스체크(Heartbeat)
│   │   ├── message_hub.py       # 3단계: Pub/Sub Fan-out 큐 (Route A / Route B 분기)
│   │   └── dataflow_worker.py   # 4단계: Event-Time 정렬 및 BigQuery 적재 워커
│   └── aiops/
│       ├── rag_agent.py         # 5단계: Vertex AI RAG 매뉴얼 검색 에이전트
│       ├── remediation.py       # 3대 자율 대응 실행기 (Slack, Scale-up, Failover)
│       └── manual_kb.json       # 사내 설비 매뉴얼 Mock 데이터 (p.42 등)
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── PipelineTopology.tsx      # [상단] 패킷 애니메이션 기반 데이터 파이프라인 뷰
    │   │   ├── FactoryContainerView.tsx  # [중단 좌측] 실제 공장 설비/컨베이어 & 워커 컨테이너 시각화
    │   │   ├── ColdChainGraphView.tsx    # [중단 우측] 실시간 온도 시계열 라인 차트 & 창고 구역 뷰
    │   │   ├── RemediationVisualDock.tsx # [하단] 3대 자율 대응 그래픽 위젯 (미니 슬랙 팝업, Pod 블록 등)
    │   │   └── ScenarioController.tsx    # 시연용 장애 시나리오 강제 트리거 버튼 바
    │   ├── App.tsx
    │   └── main.tsx
    ├── package.json
    └── tailwind.config.js

```

## 4. 5단계 아키텍처 레이어 및 데이터 명세 (Architecture & Data Specs)

### \[Stage 1\] Edge Layer (IoT 센서 시뮬레이터)

비동기로 데이터를 생성하여 Gateway WebSocket으로 전송하며, 시나리오 모드에 따라 정상/이상 데이터를 생성합니다.

* **화장품 캡 조립 모터 센서 (`COSMETIC_MOTOR`):**

  ```
  {
    "sensor_id": "MOTOR_LINE_A_01",
    "domain": "FACTORY",
    "timestamp": "2026-10-16T16:30:00.123Z",
    "metrics": {
      "vibration_svm": 8.5,
      "torque_nm": 4.2,
      "rpm": 1200
    },
    "status": "WARNING"
  }
  
  ```

* **물류 창고 콜드체인 온·습도 센서 (`COLDCHAIN_ENV`):**

  ```
  {
    "sensor_id": "COLD_ZONE_A_01",
    "node_zone": "ZONE_A",
    "domain": "FULFILLMENT",
    "timestamp": "2026-10-16T16:30:00.456Z",
    "metrics": {
      "temperature_c": 4.5,
      "humidity_pct": 45.0
    },
    "heartbeat": true
  }
  
  ```

### \[Stage 2\] Ingestion Gateway (FastAPI WebSocket & Health Check)

* `/ws/ingest` 엔드포인트로 Edge 데이터를 고속 수신.

* **Heartbeat Monitor:** 각 구역(특히 물류 `ZONE_A`) 센서의 마지막 수신 시각을 추적하여, $3\text{초}$ 이상 데이터 미수신 시 즉시 `NODE_DOWN` 이벤트를 발생시켜 Stage 5(AIOps Engine)로 직통 전달.

* **Dynamic Routing Table:** `ZONE_A` 장애 시 유입되는 잔여 트래픽을 `ZONE_B` 백업 수집 서버로 우회시키는 라우팅 상태 관리.

### \[Stage 3\] Message Hub (Cloud Pub/Sub Queue & Fan-out)

* **Queue-Based Load Leveling:** 급증하는 트래픽을 버퍼링하고 현재 큐 적체량(`backlog_count`)과 병목 지수(`bottleneck_pct`)를 실시간 계산.

* **Fan-out 양갈래 분기:**

  * **Route A (전체 로그):** 모든 원시 데이터를 Stage 4(Dataflow/BigQuery) 큐로 전달.

  * **Route B (이상 징후 필터링):** `vibration_svm >= 7.0` 이거나 `backlog_count >= 1000`, 혹은 `NODE_DOWN` 이벤트 발생 시 Stage 5(AIOps Engine)로 즉시 전달.

### \[Stage 4\] Cloud Dataflow & BigQuery DW

* Route A로 유입된 스트리밍 데이터를 Event-Time 기준으로 윈도잉/정렬하여 BigQuery 테이블(`iot_raw_logs`)에 배치/스트리밍 적재.

* Stage 5의 `CONTAINER_SCALE_UP` 액션 발동 시, 소비 워커(Consumer Task)의 개수를 기본 \$2\\text{개}$에서 $6\text{개}$($3\text{배}$)로 동적 확장하여 백로그를 빠르게 소진하는 로직 구현.

### \[Stage 5\] Vertex AI RAG Agent & AIOps Engine

* 사내 설비 매뉴얼 문서(특히 **p.42: 캡 조립 구동 모터 베어링 마모 및 토크 조절 가이드**)가 임베딩된 경량 벡터 스토어 또는 구조화된 지식 베이스 보유.

* 이상 징후 유입 시 원인을 진단하고 아래 3대 자율 대응 액션을 비동기 실행.

## 5. 현장 시나리오 및 3대 자율 대응 로직 (Scenarios & Remediation Rules)

대시보드 상단에 \[시나리오 테스트 컨트롤러\]를 배치하여 버튼 클릭만으로 아래 상황을 즉시 재현할 수 있어야 합니다.

### 🏭 \[시나리오 1\] 화장품 제조 공정: "캡 닫힘 모터 과부하 및 주문 폭증"

1. **Trigger 조건:**

   * 마감 세일 주문 폭주 시뮬레이션으로 큐 적체량(`backlog_count`)이 **1,200건**(임계치 1,000건 대비 **120%**) 도달.

   * 동시에 `MOTOR_LINE_A_01`의 진동 수치(`vibration_svm`)가 **8.5**(임계치 7.0 초과, 위험 수준)로 급증.

2. **AI 자율 대응 (2가지 전략 동시 발동):**

   * 📢 **`[Action A: SLACK_ALERT]`:** Vertex AI RAG가 매뉴얼 `p.42`를 검색해 토크 조절 가이드를 미니 슬랙 카드 UI로 즉시 팝업.

   * 📈 **`[Action B: CONTAINER_SCALE_UP]`:** 큐 병목(1,200건) 해소를 위해 워커 컨테이너(Pod) 슬롯을 \$2\\text{개} \\rightarrow 6\\text{개}$로 즉시 점등·확장하고 백로그 게이지가 빠르게 줄어드는 것을 시각화.

### 📦 \[시나리오 2\] 스마트 물류 보관 센터: "콜드체인 온·습도 센서 노드 단절 및 온도 이상"

1. **Trigger 조건:**

   * 항온항습 창고 A구역(`ZONE_A`)의 온도가 치솟거나 센서 노드의 네트워크 단절(Heartbeat 타임아웃) 발생.

2. **AI 자율 대응:**

   * 🔀 **`[Action C: NODE_FAILOVER]`:** 게이트웨이가 단절을 감지하자마자 라우팅 화살표를 `ZONE_A (Primary)` $\rightarrow$ `ZONE_B (Backup)`로 전환하는 SVG 라인 애니메이션을 작동시키고, 온도 그래프가 끊기지 않고 `ZONE_B` 백업 라인으로 이어서 그려지며 데이터 유실 0%를 시각적으로 증명.

## 6. AIOps 관제 대시보드 UI/UX 구현 명세 (Visual-First & Digital Twin Spec)

> **핵심 UI/UX 원칙 (Zero-Sentence Policy):**
> 화면에 긴 설명 문장이나 텍스트 로그 박스를 배치하지 마세요. 모든 상태는 **아이콘, 게이지 바, 실시간 시계열 그래프, 실제 공장 설비/컨테이너 모양의 그래픽 블록, 색상 점등(🟢/🟠/🔴), 애니메이션**으로만 표현합니다.

### 🖥️ 전체 화면 와이어프레임 (Visual Layout)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 🏭 DIGITAL TWIN & AIOPS CENTER   [🟢 Normal] [🔥 Scenario 1] [❄️ Scenario 2]  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ [1. Live Pipeline Flow (패킷 이동 애니메이션 & 큐 실린더 게이지)]                   │
│   (📱 Edge) ══•══► (☁️ Gateway) ══•══► [🛢️ Pub/Sub: ████████░░ 80%] ══╦══► (📊 BQ) │
│                                                                        ╚══► (🤖 AI) │
├──────────────────────────────────────────┬──────────────────────────────────────────┤
│ [2-A. Smart Factory Container Bay]       │ [2-B. Cold-Chain Temp Graph & Node Map]  │
│  ┌────────────────────────────────────┐  │  (℃) 실시간 온도 변화 (Recharts Line)   │
│  │ ⚙️ [Motor #1]  ((🔴)) Shake!       │  │  10°│          ╭──╮  ⚠️임계치(8.0℃)      │
│  │    SVM Gauge: [█████████░] 8.5     │  │   5°├──────────╯  ╰───────── (Zone B우회)│
│  │ 🧴 ──► 🧴 ──► 🧴 (컨베이어 벨트)   │  │   0°└───────────────────────► (Time)     │
│  ├────────────────────────────────────┤  │  ┌───────────────┐      ┌──────────────┐ │
│  │ 🐳 GKE Worker Containers (Pods)    │  │  │ ❄️ Zone A     │ ───► │ ❄️ Zone B    │ │
│  │  [🟦Pod1] [🟦Pod2] [⚡Pod3]        │  │  │ 🔴 DOWN (X)   │ 우회 │ 🟢 BACKUP ON │ │
│  │  [⚡Pod4] [⚡Pod5] [⚡Pod6] (3x!)  │  │  └───────────────┘      └──────────────┘ │
│  └────────────────────────────────────┘  │                                          │
├──────────────────────────────────────────┴──────────────────────────────────────────┤
│ [3. Visual AI Remediation Dock (자율 대응 그래픽 위젯 - 문장 최소화)]               │
│  ┌─────────────────────────┐ ┌─────────────────────────┐ ┌────────────────────────┐ │
│  │ 💬 SLACK RAG CARD       │ │ 🐳 AUTO SCALE-UP        │ │ 🔀 TRAFFIC FAILOVER    │ │
│  │ ┌─────────────────────┐ │ │  Pods: [■][■][□][□][□][□]│ │  [Zone A] ❌           │ │
│  │ │ 📖 Manual p.42      │ │ │     ➔  [■][■][■][■][■][■]│ │     ╰──(⚡0% Loss)──►  │ │
│  │ │ 🔧 Torque -0.5 Turn │ │ │  Throughput: 300% ▲     │ │  [Zone B] 🟢 Active    │ │
│  │ └─────────────────────┘ │ │                         │ │                        │ │
│  └─────────────────────────┘ └─────────────────────────┘ └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘

```

### 🎨 컴포넌트별 시각적 구현 디테일 (Frontend Visual Specs)

#### 1. `PipelineTopology.tsx` (상단: 실시간 파이프라인 & 큐 탱크)

* **패킷 애니메이션:** 노드와 노드 사이를 잇는 파이프 라인 위로 작은 빛 방울(데이터 패킷)들이 실시간 유입 속도에 비례해 흘러갑니다.

* **Pub/Sub 실린더 탱크:** 큐 적체량(`backlog_count`)을 숫자와 함께 **수직/수평 액체 실린더 게이지 바**로 표현합니다. 1,000건을 넘으면 실린더가 주황색/빨간색으로 차오르며 경고등이 깜빡입니다.

#### 2. `FactoryContainerView.tsx` (중단 좌측: 실제 공장 컨테이너 & 설비 베이)

* **공장 컨테이너 프레임:** 실제 스마트 팩토리의 설비 컨테이너 내부를 들여다보는 듯한 메탈릭/산업용 다크 UI 프레임(`border-2 border-slate-700 bg-slate-900/90`)으로 디자인합니다.

* **컨베이어 벨트 & 캡 조립 모터 그래픽:**

  * 화면에 화장품 공병 아이콘(🧴)들이 컨베이어 벨트 트랙 위를 옆으로 이동하는 CSS 애니메이션을 구현합니다.

  * 중앙의 **\[캡 조립 모터 #1\]** 그래픽은 평상시 부드럽게 회전(Spin)하다가, 시나리오 1 발동 시(`SVM 8.5`) 붉은색 경고광과 함께 화면에서 실제로 덜덜 떨리는 진동 애니메이션(CSS Shake/Vibrate)과 반원형 RPM/SVM 계기판(Gauge)을 보여줍니다.

* **GKE Worker Container Rack (컨테이너 슬롯):**

  * 하단에는 실제 서버 랙/도커 컨테이너 베이처럼 6개의 컨테이너 슬롯(`[Pod #1]` \~ `[Pod #6]`)을 그리드로 배치합니다.

  * 평상시에는 2개만 초록색(`🟢 Active`)으로 켜져 있고 4개는 꺼져(`⚫ Standby`) 있다가, `SCALE_UP` 발동 시 **나머지 4개의 컨테이너 블록이 번개 아이콘(⚡)과 함께 순차적으로 파란색/초록색으로 점등되며 가동되는 시각 효과**를 줍니다.

#### 3. `ColdChainGraphView.tsx` (중단 우측: 온도 변화 실시간 그래프 & 창고 노드)

* **실시간 온도 시계열 라인 차트 (`Recharts` 활용):**

  * X축은 시간(최근 30초 슬라이딩 윈도우), Y축은 온도($0^\circ\text{C} \sim 15^\circ\text{C}$)로 구성된 실시간 라인/영역 차트(AreaChart)를 렌더링합니다.

  * 차트 내에 붉은색 점선으로 임계 온도선($8.0^\circ\text{C}$)을 표시하여, 온도가 치솟거나 노드가 전환될 때 그래프 곡선이 어떻게 변하는지 한눈에 보여줍니다.

* **창고 구역(Zone A / Zone B) 컨테이너 맵:**

  * 그래프 바로 아래에 `[Zone A 항온 컨테이너]`와 `[Zone B 백업 컨테이너]` 박스를 나란히 배치합니다.

  * 시나리오 2 발동 시 `Zone A` 컨테이너가 암전(`🔴 OFFLINE`)되면서 즉시 `Zone A`에서 `Zone B`로 향하는 **우회 화살표(SVG Path)가 밝게 빛나며 연결**되고, 상단 온도 그래프가 끊김 없이 `Zone B`의 센서 데이터로 이어지는 모습을 보여줍니다.

#### 4. `RemediationVisualDock.tsx` (하단: 무문장 그래픽 액션 보드)

긴 설명 텍스트 대신 3개의 시각적 위젯 카드로 AI의 조치를 표현합니다.

* **위젯 1 (Slack RAG 미니 카드):** 실제 Slack 앱 알림 팝업처럼 디자인된 작은 카드 안에 `📖 Manual p.42` 배지와 `🔧 Torque -0.5 Turn`이라는 핵심 키워드 및 렌치 그래픽만 굵게 표시합니다.

* **위젯 2 (Container Scale-up 미터기):** `2 Pods ➔ 6 Pods` 블록 인디케이터와 처리 속도 상승 화살표(`300% ▲`)를 그래픽으로 표시합니다.

* **위젯 3 (Failover 스위치 보드):** `Zone A (❌)`에서 `Zone B (🟢)`로 선로가 바뀐 철도 분기점 형태의 다이어그램과 `0% Data Loss` 방패 배지를 표시합니다.

## 7. 구현 순서 (Step-by-Step Implementation Guide)

1. **Step 1 (Data Models & Time-Series Buffer):** `schemas.py`에 실시간 차트 렌더링을 위한 최근 30개 포인트의 온도/진동 시계열 배열(`temp_history`, `svm_history`)과 6개 워커 컨테이너의 개별 상태 배열(`worker_pods`)을 포함한 데이터 모델 정의.

2. **Step 2 (Backend Pipeline & AIOps Engine):** FastAPI 서버 내에 인메모리 시뮬레이션 파이프라인과 시나리오 트리거 API(`POST /api/scenario/{id}`) 구현.

3. **Step 3 (Real-time WebSocket Broadcast):** 프론트엔드가 `/ws/dashboard`에 연결하면 $0.5\text{초}$ 주기로 시계열 그래프 좌표, 모터 진동 수치, 컨테이너 슬롯 상태, 라우팅 상태를 실시간 전송.

4. **Step 4 (Visual-First Frontend Dashboard):** 텍스트를 최소화하고 `Recharts` 실시간 온도 그래프, 컨베이어/모터 진동 애니메이션, 컨테이너 블록 점등 UI를 갖춘 React 대시보드 구현.
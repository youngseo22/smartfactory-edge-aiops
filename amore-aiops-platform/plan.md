# 📋 [Smart Cosmetic Factory & Cold-Chain AIOps Platform] 프로젝트 기획안

## 1. 프로젝트 요약 (Executive Summary)

본 프로젝트는 **스마트 화장품 제조 공정(Smart Cosmetic Factory)**과 **콜드체인 풀필먼트 물류 센터(Cold-Chain Fulfillment)**에서 발생하는 대규모 실시간 IoT 센서 및 주문 데이터를 단일 클라우드 스트리밍 파이프라인으로 통합 처리하고, 설비·인프라 장애 발생 시 **2-Stage 하이브리드 RAG 에이전트(BM25 + Vertex AI Gemini 2.5 Flash)가 원인을 자동 진단하여 맞춤형 자율 치유(Self-Healing: 공정 안전 인터록, 부서별 Slack 처방 전송, GKE 워커 오토스케일링, 무손실 Failover)를 수행**하는 지능형 디지털 트윈 관제 플랫폼입니다.

---

## 2. 배경 및 추진 목적 (Background & Objectives)

### 2.1 기존 현장의 3대 Pain Points
1. **데이터 단절 (Data Silos):** 제조 설비와 물류 시스템이 분리 운영되어 생산 지연부터 배송·보관 문제까지 통합적인 원인 추적이 어려움.
2. **사후 대응으로 인한 복구 지연 (Reactive Operations):** 설비 이상 발생 후 담당자가 수백 페이지의 매뉴얼(SOP)과 이력을 직접 찾아야 해 골든타임을 놓치고, 불량 공병이 후속 공정으로 유출됨.
3. **트래픽 급증 및 통신 장애 취약성 (System Bottlenecks):** 마감 세일 등 주문 폭주 시 파이프라인 병목이 발생하거나, 냉장 창고 센서 네트워크 단절 시 콜드체인 온도 기록이 유실될 위험이 존재함.

### 2.2 핵심 추진 목적 (Core Objectives)
- **제조·물류 스트림 통합:** WebSocket Ingestion Gateway와 Cloud Pub/Sub 기반 Fan-out 구조로 설비·물류·주문 데이터를 단일 파이프라인에서 통합 수집 및 분기.
- **2-Stage 하이브리드 RAG 기반 초고속 진단 및 처방:** 로컬 BM25(1ms 이내)와 Vertex AI `gemini-2.5-flash` 비동기 정밀 진단을 결합해 진단 시간을 **20분 ➔ 0.01초(95% 이상 단축)**로 혁신.
- **무중단·무손실 자율 치유 (Zero Data Loss & Auto-Scaling):** 큐 적체량 기반 워커 동적 확장(2 ➔ 6 Pods)과 Dual-Zone 미러 버퍼 리플레이를 통해 **데이터 유실률 `0.0%`** 달성.
- **디지털 트윈 실시간 관제:** 0.5초 주기 WebSocket 브로드캐스팅을 통해 파이프라인 토폴로지, 설비 애니메이션, 시계열 차트, 자율 대응 상태를 한눈에 시각화.

---

## 3. 시스템 아키텍처 및 5단계 처리 흐름 (5-Stage Architecture)

본 시스템은 데이터 수집부터 AI 자율 대응까지 총 5개의 단계별 레이어로 구성되며, `Broker`, `Sink`, `RagAgent`, `Transport`를 Python `Protocol`로 추상화하여 **로컬 시뮬레이션(`AIOPS_MODE=mock`)과 실제 클라우드(`AIOPS_MODE=gcp`) 환경을 코드 수정 없이 즉시 전환**할 수 있습니다.

```text
1. 📱 Stage 1: Edge Layer (화장품 캡 조립 모터 / 컨베이어 벨트 / 콜드체인 Zone A·B 센서 / 주문 게이트웨이)
        │
        ▼ (고성능 WebSocket `/ws/ingest` 또는 In-Proc 비동기 스트리밍 & 장애/버스트 시뮬레이션)
2. ☁️ Stage 2: Ingestion Gateway (FastAPI Gateway · 0.25s 고속 Heartbeat 모니터 · Zone B 미러 링버퍼)
        │
        ▼ (Queue-Based Load Leveling — Publish & 0.1s 백로그 감시)
3. ⚡ Stage 3: Message Hub (Cloud Pub/Sub Queue & Fan-out 양갈래 분기)
        ├──► Route A (정상 스트림) ──► [Stage 4] Cloud Dataflow Workers (2~6 Pods 동적 확장)
        │                                 └──► Event-Time 워터마크(2.0s) 정렬 ➔ BigQuery (`iot_raw_logs`) 적재
        │
        └──► Route B (이상 징후) ───► [Stage 5] 2-Stage Hybrid RAG Agent & AIOps Remediation Engine
                                          ├── [Fast Path] 로컬 BM25 매뉴얼 검색 (1ms 이내 즉각 대응)
                                          ├── [Async Path] Vertex AI (Gemini 2.5 Flash) 정밀 원인·신뢰도 보강
                                          │
                                          ├──► 📢 [Action 1] Safety Interlock (라인 정지) & 부서별 Slack SOP 카드 전송
                                          ├──► 📈 [Action 2] Dataflow/GKE 워커 파드 오토스케일링 (2 ➔ 6 Pods, 처리량 300%▲)
                                          └──► 🔀 [Action 3] Dual-Zone 무손실 Failover (Zone A ➔ B 전환 & 미러 버퍼 Replay)
```

---

## 4. 현장 시나리오 및 AI 자율 대응 전략 (Scenarios & Self-Healing)

실제 대시보드와 API(`POST /api/scenario/{id}`, `POST /api/motor/svm/step`)에서 즉시 시연 가능한 4대 핵심 시나리오와 복구 루프입니다.

### 🏭 [시나리오 1] 화장품 제조 공정: "캡 조립 모터 과부하 및 안전 인터록"
- **현장 상황:** 캡 조립 구동 모터(`MOTOR_LINE_A_01`)의 베어링 마모 및 토크 과다로 합성 진동 가속도(`vibration_svm`)가 평상시 `2.8 m/s²`에서 임계치(`7.0`)를 넘어 **`8.5 m/s²`**로 급증.
- **시스템 감지:** Route B가 `VIBRATION_HIGH` 이벤트를 즉시 감지하고, 불량 공병의 후속 공정 유출을 막기 위해 **공정 안전 인터록(`LINE_HALT`)을 가동**하여 컨베이어를 긴급 정지.
- **AI 자율 대응 (`Action 1: SLACK_ALERT & INTERLOCK`):**
  1. **2-Stage RAG 진단:** BM25 엔진이 설비 매뉴얼 **p.42 (`MAN-042`)**에서 *"토크 조절 나사 반시계 방향 0.5회전 감속(`Torque -0.5 Turn`)"* 가이드를 1ms 내에 검색해 우선 발송하고, 백그라운드에서 **Vertex AI (`gemini-2.5-flash`)**가 센서 컨텍스트를 분석해 상세 원인과 신뢰도를 카드에 실시간 업데이트.
  2. **멀티채널 라우팅 & 정비 복구:** 제조팀 전용 슬랙 채널(`#aiops-capping-line`)로 처방 카드를 전송하며, 현장 엔지니어가 **모터 교체/정비(시나리오 4)**를 수행하면 SVM이 `2.8 m/s²`로 복귀하고 안전 인터록이 자동 해제됨.

### ⚙️ [시나리오 2] 컨베이어 이송 라인: "인버터 주파수 헌팅 및 비정상 급가속"
- **현장 상황:** 컨베이어 인버터 주파수 헌팅(Hunting)으로 인해 벨트 이송 속도가 정속(`1.0 m/s`)에서 **`2.8 m/s`**로 비정상 급가속(`CONVEYOR_ANOMALY`)하며 용기 흔들림 및 정렬 불량 위험 발생.
- **AI 자율 대응 (`Action 1: SLACK_ALERT`):**
  - 매뉴얼 **p.18 (`MAN-018`)**을 검색하여 *"인버터 PID 게인 리셋 및 기준 주파수(`1.0 m/s`) 재동기화(`Inverter PID Sync`)"* 가이드를 `#aiops-conveyor-line` 채널로 즉시 전송하고, **컨베이어 안정화(시나리오 7)** 조치 시 정속(`1.0 m/s`)으로 복구.

### ❄️ [시나리오 3] 스마트 물류 보관 센터: "콜드체인 과온 및 센서 노드 단절"
- **현장 상황:** 고가 기능성 앰플이 보관된 주 보관소(`ZONE_A`) 냉각기 이상으로 온도가 매 틱마다 `+1.0°C`씩 상승해 관리 기준선(**`8.0°C`**)을 초과(`TEMP_HIGH`)한 뒤, 네트워크/전원 장애로 센서 노드가 완전 단절됨.
- **시스템 감지:** 2단계 게이트웨이의 고속 하트비트 모니터(0.25s 폴링)가 **`3.0초`** 무수신 타임아웃을 감지하여 `NODE_DOWN` 발행.
- **AI 자율 대응 (`Action 3: NODE_FAILOVER` & `Action 1: SLACK_ALERT`):**
  1. **무손실 자동 절체 (Zero Data Loss):** 에이전트가 즉시 라우팅 테이블을 `ZONE_A(Primary) ➔ ZONE_B(Backup)`로 스위칭하고, 평상시 인메모리 링버퍼(`maxlen=60`)에 미러링해 둔 `ZONE_B` 패킷 중 마지막 처리 시퀀스(`_last_active_seq`) 이후 누락분을 즉시 재생(Replay)하여 **데이터 유실률 `0.0%`** 달성.
  2. **관제 알림 & Failback:** 매뉴얼 **p.58 (`MAN-058`)** 기반 냉각기 점검 가이드를 물류 채널(`#aiops-coldchain-zone`)로 전송하며, 수리 완료 후 **Zone A 복구(시나리오 5)** 트리거 시 주 보관소(`ZONE_A`)로 무중단 Failback 원복.

### 📈 [시나리오 4] 풀필먼트 & 파이프라인: "마감 세일 주문 폭증 및 메시지 큐 병목"
- **현장 상황:** 마감 세일 이벤트로 단시간에 **`1,250건`**(`25 chunks × 50건`)의 주문 데이터(`ORDER_GW`)가 버스트 유입되어 기본 워커 2개(용량 `80 msg/s`)의 처리 한계를 초과하고, Pub/Sub 큐 적체량이 임계치 **`1,000건`** 돌파(최대 약 1,200건, 병목 지수 `120%`).
- **시스템 감지:** 3단계 메시지 허브가 0.1초 주기로 백로그를 감시하여 `backlog >= 1,000` 도달 시 래치(Latch) 기반 `BACKLOG_HIGH` 이벤트 발행 (중복 트리거 방지).
- **AI 자율 대응 (`Action 2: CONTAINER_SCALE_UP` & Auto Scale-Down):**
  1. **동적 스케일 아웃:** 매뉴얼 **p.63 (`MAN-063`)** 전략에 따라 Dataflow/GKE 소비 워커 파드를 기본 **2개에서 최대 6개(3배)로 순차 확장**(`STANDBY ➔ STARTING ➔ ACTIVE`, 0.35s 스태거링)하여 처리량을 **`80 ➔ 240 msg/s (300%)`**로 높여 백로그를 수 초 내에 고속 소진.
  2. **지능형 오토스케일 인 (비용 최적화):** 적체량이 임계치의 5%(`50건`) 미만으로 떨어진 후 **`5.0초`** 동안 안정 상태가 유지되면 워커를 자동으로 `6개 ➔ 2개`로 축소(Scale-Down)하여 클라우드 인프라 유지 비용을 60% 이상 절감.

---

## 5. AIOps & Digital Twin 관제 대시보드 UI/UX 설계

복잡한 텍스트 로그 대신, 관리자가 파이프라인의 데이터 흐름, 물리적 제조·물류 현장의 디지털 트윈 상태, 그리고 AI 자율 치유 현황을 한 화면(`1520px` 와이드 그리드)에서 직관적으로 파악할 수 있도록 **5대 핵심 섹션**으로 설계했습니다.

### 🖥️ 화면 레이아웃 구조

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ 🏭 SMART FACTORY AIOps & DIGITAL TWIN  [🟢 실시간 연동 LIVE]                             │
│    [🔄 정상 운영] [📈 주문 폭증] [🔧 모터 교체] [⚡ 컨베이어 이상] [❄️ 콜드체인 이상] ... │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ [SECTION 1. Live Pipeline Topology & Pub/Sub Queue (실시간 5-Stage 파이프라인 토폴로지)] │
│                                                                                          │
│  [Stage 1: Edge] ──► [Stage 2: Gateway] ──► [Stage 3: Pub/Sub Hub (Backlog: 1,200건)]    │
│   (edge msg/s)        (Active: ZONE_A)       ├─► Route A ──► [Stage 4: Dataflow ➔ BQ]   │
│                                              └─► Route B ──► [Stage 5: Vertex AI RAG]    │
├───────────────────────────┬──────────────────────────────┬───────────────────────────────┤
│ [SECTION 2. 스마트 제조]  │ [SECTION 3. 스마트 콜드체인] │ [SECTION 4. 처리 컨테이너]    │
│  • 캡 조립 모터 SVM 게이지│  • Zone A(주) / Zone B(백업) │  • GKE Worker Pod 매트릭스    │
│    (2.8 ➔ 8.5 m/s² 위험!) │    실시간 온도 듀얼 차트     │    (Pod #1~#6 상태/부하 표시) │
│  • SVM 스텝 조절 (+/-)    │  • 관리 임계선 (8.0°C) 표시  │  • 실시간 처리율 (Throughput) │
│  • 컨베이어 벨트 디지털   │  • 하트비트 & Failover 브릿징│    100% ➔ 300% (240 msg/s)    │
│    트윈 & 안전 인터록 표시│    (데이터 유실률 0.0% 배지) │  • BigQuery 누적 적재 행 수   │
├───────────────────────────┴──────────────────────────────┴───────────────────────────────┤
│ [SECTION 5. AIOps Autonomous Remediation Dock (3대 자율 치유 실행 상태 및 RAG 처방 카드)]│
│                                                                                          │
│  ┌────────────────────────────┐ ┌───────────────────────────┐ ┌────────────────────────┐ │
│  │ 📢 Action 1: RAG Slack 처방│ │ 📈 Action 2: HPA 스케일업 │ │ 🔀 Action 3: Failover  │ │
│  │ • 채널: #aiops-capping-line│ │ • 워커 파드: 2 ➔ 6 Pods   │ │ • 경로: ZONE_A ➔ ZONE_B│ │
│  │ • 매뉴얼: MAN-042 (p.42)   │ │ • 처리 용량: 300% 증대    │ │ • 리플레이: 누락 0건   │ │
│  │ • 조치: Torque -0.5 Turn   │ │ • 안정화 시 자동 축소 대기│ │ • 유실률: 0.0% 무손실  │ │
│  │ • Gemini 2.5 정밀 진단 완료│ └───────────────────────────┘ └────────────────────────┘ │
│  └────────────────────────────┘                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### 🎨 시각적 대시보드의 핵심 설계 포인트 (Why This UX?)

1. **상단 시나리오 컨트롤러 & 양방향 조작:**
   - 우측 상단 컨트롤 바와 섹션 2의 모터 진동(SVM) 스텝 조절 버튼(`+1.5` / `-1.5`)을 통해 별도 CLI 명령 없이도 장애 주입(모터 과부하, 컨베이어 급가속, 콜드체인 단절, 주문 폭증)부터 현장 수리·원복까지 전 과정을 실시간 인터랙티브하게 시연할 수 있습니다.
2. **엔드투엔드 파이프라인 토폴로지 (Section 1):**
   - 데이터가 수집되어 Route A(BigQuery 적재)와 Route B(AI 긴급 대응)로 분기되는 초당 처리율(`msg/s`)과 큐 백로그 수치를 실시간 애니메이션으로 시각화하여 병목 구간을 즉시 역추적합니다.
3. **도메인별 디지털 트윈 뷰 (Section 2 · 3 · 4):**
   - **제조(Section 2):** 모터 진동 시계열 차트와 함께 실제 회전하는 컨베이어 벨트·공병 애니메이션을 배치해, 안전 인터록(`LINE_HALT`) 작동이나 급가속(`2.8 m/s`) 상황을 직관적으로 체감하게 합니다.
   - **물류(Section 3):** `ZONE_A` 단절 시 `ZONE_B` 백업 곡선이 끊김 없이 이어지는 브릿징(Bridging) 차트와 `데이터 유실 0.0%` 배지로 무손실 Failover를 시각적으로 입증합니다.
   - **인프라(Section 4):** 6개 워커 파드(`Pod #1 ~ #6`)의 상태(`STANDBY` ➔ `STARTING` ➔ `ACTIVE`)와 개별 부하율(`load_pct`)을 컨테이너 매트릭스로 표현해 오토스케일링 동작을 명확히 보여줍니다.
4. **2-Stage RAG & 3대 자율 치유 독 (Section 5):**
   - AI 에이전트가 검색한 매뉴얼 번호(`MAN-042`, `MAN-018`, `MAN-058`, `MAN-063`), 핵심 조치 태그(`Torque -0.5 Turn` 등), 담당 Slack 채널, 그리고 Vertex AI Gemini의 정밀 진단 결과를 실제 Slack 메시지 카드 형태로 렌더링하여 AIOps의 효용성을 증명합니다.

---

## 6. 기술 스택 및 실행 환경 (Tech Stack & Architecture Specs)

| 구분 | 핵심 기술 및 구성 요소 | 비고 |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide Icons | `/ws/dashboard` 0.5초 실시간 스냅샷 렌더링 |
| **Backend & Gateway** | Python 3.11+, FastAPI, Uvicorn, Asyncio, WebSockets, Pydantic v2 | 비동기 스트림 처리 및 REST/WS 멀티플렉싱 |
| **Cloud Pipeline (GCP)** | Google Cloud Pub/Sub, Cloud Dataflow (Event-Time Window), BigQuery, GKE | `AIOPS_MODE=gcp` 전환 시 실 서비스 즉시 연동 |
| **AI & RAG Engine** | 로컬 BM25 (한글 바이그램 토크나이저) + **Vertex AI (`gemini-2.5-flash`)** | 2-Stage 하이브리드 진단 및 Slack Webhook 연동 |

---

## 7. 향후 고도화 로드맵 (Future Work)

1. **사전 예측 정비 (Predictive Maintenance):** BigQuery에 축적된 시계열 로그(`iot_raw_logs`)를 기반으로 LSTM / Autoencoder / TimesFM 모델을 학습시켜 베어링 마모 및 냉각기 이상을 고장 발생 30분 전에 사전 예측(RUL 추정).
2. **멀티모달 벡터 RAG 확장:** 경량 BM25 검색에 **Vertex AI Vector Search**를 결합하고, 텍스트 매뉴얼뿐만 아니라 설비 도면·조치 영상·과거 장애 리포트(Post-mortem)까지 멀티모달 검색 지원.
3. **Closed-Loop 양방향 PLC 제어:** Slack 알림 전송(Human-in-the-Loop)을 넘어, 안전성이 검증된 조치는 Edge Gateway에서 **OPC-UA / Modbus** 프로토콜로 공장 PLC에 직접 감속·토크 보정 명령을 하달하는 완전 자율 제어 구현.
4. **KEDA 기반 프로덕션 컨테이너 오토스케일링 & Multi-Cloud (AWS) 확장:** 워커 풀을 실제 Docker 컨테이너 및 GKE **KEDA**(`num_undelivered_messages` 지표)와 연동하고, 엔터프라이즈 표준인 **AWS IoT Core · Kinesis · Bedrock** 환경으로도 1:1 어댑터 이식(`AIOPS_MODE=aws`) 지원.

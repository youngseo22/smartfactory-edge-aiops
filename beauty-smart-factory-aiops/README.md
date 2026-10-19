# 🏭 AIOps Enterprise Monitoring & Autonomous Remediation Platform

> **화장품 제조 공장(Smart Factory) & 스마트 물류 센터(Fulfillment) 디지털 트윈 관제 플랫폼**  
> 실시간 IoT 센서 스트리밍 파이프라인 수집 및 장애 발생 시 Vertex AI RAG 에이전트 기반 3대 자율 대응(알림, 스케일업, Failover) 시스템

---

## 📌 주요 특징 (Key Features)

1. **실시간 데이터 스트리밍 & 디지털 트윈 (Zero-Sentence Policy Visual UI)**
   - 텍스트 로그 나열을 배제하고 그래픽, 계기판, Recharts 실시간 시계열 라인 차트, 컨베이어 벨트 화장품 공병 이동 애니메이션, GKE 워커 랙 점등 애니메이션으로 완벽 시각화.
2. **5단계 아키텍처 파이프라인**
   - **Stage 1 (Edge Layer):** 화장품 캡 조립 모터 센서(`COSMETIC_MOTOR`), 콜드체인 온·습도 센서(`COLDCHAIN_ENV`), 주문 폭주 이벤트 생성기.
   - **Stage 2 (Ingestion Gateway):** 고속 WebSocket 수신, 3초 Heartbeat 모니터링(`NODE_DOWN`), 동적 라우팅 테이블.
   - **Stage 3 (Message Hub):** Pub/Sub 큐 기반 부하 평활화, Route A(전체 로그) 및 Route B(이상 징후 필터링) Fan-out.
   - **Stage 4 (Cloud Dataflow & BigQuery):** Event-Time 정렬 윈도우 적재, 워커 컨테이너 풀 동적 제어.
   - **Stage 5 (Vertex AI RAG Agent & AIOps Engine):** 사내 설비 매뉴얼(`manual_kb.json`, p.42 등) 검색 기반 자율 대응.
3. **원클릭 장애 시연 컨트롤러 (3대 자율 대응 시나리오)**
   - **🟢 Normal:** 정상 운영 상태 (모터 SVM 2.4, 기본 Pod 2대 활성, Zone A 정상).
   - **🔥 Scenario 1 (화장품 제조 공정 모터 과부하 & 주문 폭증):**
     - 큐 적체량 1,200건 도달 & 모터 진동 SVM 8.5 급증.
     - **Action A (SLACK_ALERT):** RAG가 매뉴얼 `p.42`를 검색하여 `Torque -0.5 Turn` 미니 슬랙 카드 팝업.
     - **Action B (CONTAINER_SCALE_UP):** 워커 Pod를 2개 ➔ 6개(3배)로 즉시 확장 점등하여 백로그 급속 소진.
   - **❄️ Scenario 2 (콜드체인 센서 노드 단절 및 온도 이상):**
     - Zone A 네트워크 단절 (3초 Heartbeat 미수신 감지).
     - **Action C (NODE_FAILOVER):** 트래픽을 `Zone A ➔ Zone B`로 즉시 우회(SVG 라인 점등)하고, 단절 시간 동안의 로컬 버퍼 데이터를 재전송하여 **데이터 유실 0%** 달성.

---

## 📂 디렉토리 구조 (Directory Structure)

```
beauty-smart-factory-aiops/
├── .venv/                      # Python 가상환경
├── requirements.txt            # 백엔드 의존성
├── requirements-gcp.txt        # 실제 GCP 연동 의존성 (선택 사항)
├── .gitignore                  # Git 무시 파일
├── README.md                   # 프로젝트 매뉴얼
├── aiops.md                    # 프로젝트 명세서
├── backend/
│   ├── main.py                 # FastAPI 엔트리포인트 & WebSocket 서버
│   ├── config.py               # 임계치 및 환경 설정
│   ├── runtime.py              # 5단계 파이프라인 통합 런타임
│   ├── models/
│   │   ├── schemas.py          # Pydantic 데이터 모델
│   │   └── timeseries.py       # 인메모리 30초 시계열 슬라이딩 윈도우
│   ├── edge_simulator/
│   │   └── generator.py        # 엣지 센서 및 장애 주입기
│   ├── pipeline/
│   │   ├── gateway.py          # 2단계: Ingestion Gateway & Heartbeat
│   │   ├── message_hub.py      # 3단계: Pub/Sub Fan-out 큐
│   │   └── dataflow_worker.py  # 4단계: 워커 풀 & BigQuery 적재
│   └── aiops/
│       ├── rag_agent.py        # 5단계: TF-IDF & Vertex AI RAG 검색
│       ├── remediation.py      # 3대 자율 대응 실행기
│       └── manual_kb.json      # 설비 매뉴얼 데이터 (p.42 등)
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── components/
        │   ├── PipelineTopology.tsx      # 실시간 파이프라인 및 큐 실린더 게이지
        │   ├── FactoryContainerView.tsx  # 설비 컨베이어 공병 이동 & 모터 진동 & 6 Pods 랙
        │   ├── ColdChainGraphView.tsx    # Recharts 시계열 온도 차트 & 창고 구역 우회 맵
        │   ├── RemediationVisualDock.tsx # 3대 자율 대응 그래픽 위젯
        │   └── ScenarioController.tsx    # 시나리오 트리거 버튼 바
        ├── App.tsx
        ├── main.tsx
        └── index.css
```

---

## 🚀 빠른 시작 가이드 (Quick Start)

### 1. 백엔드 실행 (Python 가상환경)

```bash
# 가상환경 활성화 (Windows PowerShell 기준)
.\.venv\Scripts\Activate.ps1

# (선택) 의존성 설치 확인
pip install -r requirements.txt

# 백엔드 서버 시작 (포트 8000)
cd backend
python -m uvicorn main:app --reload --port 8000
```

> 백엔드 API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)  
> 헬스체크: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 2. 프론트엔드 실행 (React + Vite)

새 터미널 창을 열고:

```bash
cd frontend

# 패키지 설치 (최초 1회)
npm install

# 개발 서버 실행 (포트 5173)
npm run dev
```

브라우저에서 **[http://localhost:5173](http://localhost:5173)** 로 접속하면 디지털 트윈 관제 대시보드가 즉시 가동됩니다.

---

## 🧪 시나리오 시연 방법

대시보드 상단 우측의 시나리오 버튼으로 테스트할 수 있습니다:

1. **[🟢 Normal] 클릭:** 평상시 정상 가동 상태로 복구됩니다.
2. **[🔥 Scenario 1] 클릭:**
   - 화장품 캡 조립 모터가 붉은색 경고광과 함께 실제로 떨리기 시작합니다 (`SVM 8.5`).
   - 주문 폭주로 Pub/Sub 실린더가 1,200건까지 차오릅니다.
   - RAG 매뉴얼 p.42 Slack 알림 카드가 팝업됩니다.
   - GKE Worker 컨테이너가 2대에서 6대로 번개 표시와 함께 확장 점등되며 큐 적체가 빠르게 해소됩니다.
3. **[❄️ Scenario 2] 클릭:**
   - Zone A 콜드체인 온도가 상승하며 3초 후 네트워크 단절(`OFFLINE`)이 발생합니다.
   - Zone A ➔ Zone B 백업 경로로 SVG 우회 라인이 점등됩니다.
   - 상단 실시간 온도 그래프가 끊김 없이 보라색 라인으로 이어지며 `Loss 0%`가 시각적으로 증명됩니다.

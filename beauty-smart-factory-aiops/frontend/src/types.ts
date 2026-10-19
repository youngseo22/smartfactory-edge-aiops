// backend/models/schemas.py 의 DashboardSnapshot 미러 타입

export type ScenarioId = "NORMAL" | "SCENARIO_1" | "SCENARIO_2";
export type SensorStatus = "NORMAL" | "WARNING" | "CRITICAL";
export type PodState = "STANDBY" | "BOOTING" | "ACTIVE" | "DRAINING";
export type ZoneStatus = "ONLINE" | "WARNING" | "OFFLINE" | "STANDBY" | "BACKUP_ON";
export type ActionType =
  | "SLACK_ALERT"
  | "CONTAINER_SCALE_UP"
  | "CONTAINER_SCALE_DOWN"
  | "NODE_FAILOVER"
  | "DIAGNOSIS";

export interface TempPoint {
  t: number;
  zone_a: number | null;
  zone_b: number | null;
  route: "ZONE_A" | "ZONE_B" | null;
  a_primary: number | null;
  a_backup: number | null;
}

export interface SvmPoint {
  t: number;
  svm: number | null;
  torque: number | null;
  rpm: number | null;
}

export interface WorkerPod {
  pod_id: string;
  index: number;
  state: PodState;
  load_pct: number;
  processed: number;
  boosted: boolean;
}

export interface PipelineStats {
  edge_rate: number;
  ingress_rate: number;
  route_a_rate: number;
  route_b_rate: number;
  consume_rate: number;
  backlog_count: number;
  backlog_threshold: number;
  bottleneck_pct: number;
  bq_rows: number;
  ai_events: number;
}

export interface MotorState {
  sensor_id: string;
  vibration_svm: number;
  torque_nm: number;
  rpm: number;
  status: SensorStatus;
  threshold: number;
  critical: number;
}

export interface FactoryState {
  motor: MotorState;
  svm_history: SvmPoint[];
  worker_pods: WorkerPod[];
  active_workers: number;
  base_workers: number;
  max_workers: number;
  throughput_pct: number;
}

export interface ZoneState {
  zone: string;
  role: "PRIMARY" | "BACKUP";
  status: ZoneStatus;
  temperature_c: number | null;
  humidity_pct: number | null;
  last_seen_ago_s: number;
  link_up: boolean;
}

export interface ColdChainState {
  temp_history: TempPoint[];
  zones: Record<string, ZoneState>;
  temp_threshold: number;
}

export interface RoutingState {
  table: Record<string, string>;
  failover_active: boolean;
  data_loss_pct: number;
  buffered_msgs: number;
  recovered_msgs: number;
}

export interface SlackCard {
  active: boolean;
  page: string | null;
  title: string | null;
  keyword: string | null;
  metric: string | null;
  severity: SensorStatus;
  source: "LOCAL_RAG" | "VERTEX_AI";
  confidence: number;
  delivered: boolean;
  ts: number | null;
}

export interface ScaleUpWidget {
  active: boolean;
  from_pods: number;
  to_pods: number;
  active_pods: number;
  throughput_pct: number;
  ts: number | null;
}

export interface FailoverWidget {
  active: boolean;
  from_zone: string;
  to_zone: string;
  data_loss_pct: number;
  recovered_msgs: number;
  ts: number | null;
}

export interface ActionRecord {
  action: ActionType;
  target: string;
  ts: number;
  meta: Record<string, unknown>;
}

export interface DashboardSnapshot {
  ts: number;
  scenario: ScenarioId;
  mode: "MOCK" | "GCP";
  pipeline: PipelineStats;
  factory: FactoryState;
  coldchain: ColdChainState;
  routing: RoutingState;
  remediation: {
    slack: SlackCard;
    scale_up: ScaleUpWidget;
    failover: FailoverWidget;
  };
  actions: ActionRecord[];
}

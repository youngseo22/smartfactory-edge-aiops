// backend/models/schemas.py 의 DashboardSnapshot 과 1:1 대응

export interface TempPoint {
  ts: number
  temp_a: number | null
  temp_b: number | null
  zone: string
}

export interface SvmPoint {
  ts: number
  svm: number
}

export interface PodState {
  id: number
  status: 'ACTIVE' | 'STARTING' | 'STANDBY'
  load_pct: number
}

export interface MotorState {
  sensor_id: string
  svm: number
  torque_nm: number
  rpm: number
  status: 'NORMAL' | 'WARNING' | 'OFFLINE'
}

export interface ZoneState {
  zone: string
  role: 'PRIMARY' | 'BACKUP'
  status: 'ONLINE' | 'WARNING' | 'OFFLINE' | 'UNKNOWN'
  serving: boolean
  temp_c: number | null
  humidity_pct: number | null
  last_seen_age_s: number | null
}

export interface RoutingState {
  primary_zone: string
  backup_zone: string
  active_zone: string
  failover_active: boolean
  data_loss_pct: number
  replayed: number
  switched_at: number | null
  table: Record<string, string>
}

export interface QueueState {
  backlog_count: number
  bottleneck_pct: number
  severity: 'OK' | 'WARN' | 'CRIT'
  throughput_pct: number
  rows_written: number
}

export interface PipelineRates {
  edge_rate: number
  route_a_rate: number
  route_b_rate: number
  drain_rate: number
  bq_rate: number
}

export interface SlackCard {
  channel: string
  severity: 'WARN' | 'CRIT'
  manual_page: number
  manual_title: string
  key_action: string
  cause: string
  confidence: number
  svm: number
  ts: number
}

export interface ScaleAction {
  from_pods: number
  to_pods: number
  status: 'RUNNING' | 'DONE'
  ts: number
}

export interface FailoverAction {
  from_zone: string
  to_zone: string
  status: 'DONE' | 'NO_BACKUP'
  data_loss_pct: number
  replayed: number
  ts: number
}

export interface RemediationState {
  slack: SlackCard | null
  scale: ScaleAction | null
  failover: FailoverAction | null
}

export interface Snapshot {
  ts: number
  mode: string
  active_scenarios: number[]
  motor: MotorState
  svm_history: SvmPoint[]
  temp_history: TempPoint[]
  zones: Record<string, ZoneState>
  routing: RoutingState
  queue: QueueState
  pipeline: PipelineRates
  worker_pods: PodState[]
  remediation: RemediationState
  events: string[]
}

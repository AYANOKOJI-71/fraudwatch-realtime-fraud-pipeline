export type Action = 'allow' | 'review' | 'block'

export interface Decision {
  event_id: string
  action: Action
  score: number
  rules: string[]
  velocity_count_5m: number
  latency_ms: number
  created_at: string
}

export interface Overview {
  processed_events: number
  duplicate_events: number
  decisions: Record<Action, number>
  open_cases: number
  avg_latency_ms: number
  recent_decisions: Decision[]
}

export interface Case {
  case_id: string
  event_id: string
  priority: 'high' | 'critical'
  score: number
  rules: string[]
  status: 'open' | 'triaged' | 'closed'
  created_at: string
}

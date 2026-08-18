import type { Action, Decision } from './types'

export const actionLabel = (action: Action) => action.charAt(0).toUpperCase() + action.slice(1)

export const compactLatency = (latency: number) => `${latency < 1 ? latency.toFixed(3) : latency.toFixed(1)} ms`

export const ruleLabel = (rule: string) => rule.replaceAll('_', ' ')

export const severityFor = (decision: Decision) => {
  if (decision.action === 'block') return 'critical'
  if (decision.action === 'review') return 'attention'
  return 'clear'
}

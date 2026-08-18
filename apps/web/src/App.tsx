import { useCallback, useEffect, useMemo, useState } from 'react'

import { actionLabel, compactLatency, ruleLabel, severityFor } from './format'
import type { Case, Decision, Overview } from './types'

const emptyOverview: Overview = {
  processed_events: 0,
  duplicate_events: 0,
  decisions: { allow: 0, review: 0, block: 0 },
  open_cases: 0,
  avg_latency_ms: 0,
  recent_decisions: []
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) throw new Error(`Request failed (${response.status})`)
  return response.json() as Promise<T>
}

export default function App() {
  const [overview, setOverview] = useState<Overview>(emptyOverview)
  const [cases, setCases] = useState<Case[]>([])
  const [selected, setSelected] = useState<Decision | null>(null)
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [nextOverview, nextCases] = await Promise.all([
        request<Overview>('/api/overview'),
        request<Case[]>('/api/cases')
      ])
      setOverview(nextOverview)
      setCases(nextCases)
      setSelected((current) => current ?? nextOverview.recent_decisions[0] ?? null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to reach the analyst API')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const task = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(task)
  }, [load])

  const seed = async () => {
    setSeeding(true)
    try {
      await request<Decision[]>('/api/demo/seed', { method: 'POST' })
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Demo seeding failed')
    } finally {
      setSeeding(false)
    }
  }

  const total = useMemo(() => Object.values(overview.decisions).reduce((sum, value) => sum + value, 0), [overview])
  const reviewRate = total ? Math.round(((overview.decisions.review + overview.decisions.block) / total) * 100) : 0

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">F</span><div><strong>FraudWatch</strong><span>streaming risk operations</span></div></div>
        <div className="environment"><i /> SYNTHETIC LAB <span>·</span> Kafka-ready</div>
        <button className="outline" onClick={() => void load()} disabled={loading}>Refresh data</button>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">Live decision intelligence</p>
          <h1>Explainable risk decisions,<br /><em>before events become cases.</em></h1>
          <p className="lede">A local streaming lab for observing idempotent transaction events, stateful velocity controls, and analyst review queues. All data is synthetic.</p>
        </div>
        <div className="hero-actions">
          <button className="primary" onClick={() => void seed()} disabled={seeding}>{seeding ? 'Seeding events…' : 'Inject demo event stream'}</button>
          <span>Generates deterministic synthetic events only.</span>
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}

      <section className="metrics" aria-label="Fraud risk metrics">
        <Metric label="Events processed" value={overview.processed_events.toLocaleString()} meta={`${overview.duplicate_events} idempotent replays`} tone="neutral" />
        <Metric label="Review rate" value={`${reviewRate}%`} meta={`${overview.decisions.review} review · ${overview.decisions.block} block`} tone="amber" />
        <Metric label="Open investigations" value={overview.open_cases.toString()} meta="human decision required" tone="red" />
        <Metric label="Processor latency" value={compactLatency(overview.avg_latency_ms)} meta="risk scoring only" tone="mint" />
      </section>

      <section className="workspace">
        <div className="panel stream-panel">
          <div className="panel-header"><div><p className="eyebrow">Decision stream</p><h2>Latest risk outcomes</h2></div><span className="topic">fraud.decisions.v1</span></div>
          <div className="decision-list">
            {overview.recent_decisions.length === 0 && <p className="empty">No events yet. Inject the demo event stream to inspect the pipeline.</p>}
            {overview.recent_decisions.map((decision) => (
              <button className={`decision-row ${selected?.event_id === decision.event_id ? 'selected' : ''}`} key={decision.event_id} onClick={() => setSelected(decision)}>
                <span className={`decision-dot ${severityFor(decision)}`} />
                <span className="event-id">{decision.event_id}</span>
                <span className={`status ${decision.action}`}>{actionLabel(decision.action)}</span>
                <span className="score">{decision.score}<small>/100</small></span>
              </button>
            ))}
          </div>
        </div>

        <aside className="panel explanation">
          <div className="panel-header"><div><p className="eyebrow">Decision explanation</p><h2>{selected ? selected.event_id : 'Select an event'}</h2></div>{selected && <span className={`status ${selected.action}`}>{actionLabel(selected.action)}</span>}</div>
          {selected ? <>
            <div className="score-orbit"><span>{selected.score}</span><small>risk score<br />out of 100</small></div>
            <div className="rule-stack">
              <p>Matched policy controls</p>
              {selected.rules.length ? selected.rules.map((rule) => <span className="rule" key={rule}>{ruleLabel(rule)}</span>) : <span className="rule neutral">no escalated signals</span>}
            </div>
            <dl className="facts"><div><dt>5-minute velocity</dt><dd>{selected.velocity_count_5m} events</dd></div><div><dt>Processor latency</dt><dd>{compactLatency(selected.latency_ms)}</dd></div><div><dt>Outcome</dt><dd>{selected.action === 'allow' ? 'Synthetic event recorded' : 'Analyst review opportunity created'}</dd></div></dl>
          </> : <p className="empty">An explanation appears after the first synthetic event is processed.</p>}
        </aside>
      </section>

      <section className="panel cases-panel">
        <div className="panel-header"><div><p className="eyebrow">Investigation queue</p><h2>Decisions requiring human review</h2></div><span className="queue-count">{cases.length} open</span></div>
        <div className="case-table"><div className="table-head"><span>Case</span><span>Priority</span><span>Score</span><span>Triggered controls</span><span>Status</span></div>
          {cases.length === 0 ? <p className="empty">No analyst cases yet.</p> : cases.map((item) => <div className="case-row" key={item.case_id}><span>{item.case_id}</span><span className={`priority ${item.priority}`}>{item.priority}</span><span>{item.score}</span><span>{item.rules.map(ruleLabel).join(' · ')}</span><span className="case-status">{item.status}</span></div>)}
        </div>
      </section>

      <footer><span>FraudWatch is a synthetic demonstration. Decisions are explainable analyst-review recommendations, not financial actions.</span><span>Kafka · Python · Redis · PostgreSQL · Prometheus</span></footer>
    </main>
  )
}

function Metric({ label, value, meta, tone }: { label: string; value: string; meta: string; tone: string }) {
  return <article className={`metric ${tone}`}><p>{label}</p><strong>{value}</strong><span>{meta}</span></article>
}

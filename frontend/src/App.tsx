import { FormEvent, ReactNode, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import './analysis.css'
import { Activity, ArrowLeft, ArrowUpRight, Check, CircleHelp, Clock3, Command, ExternalLink, LoaderCircle, Skull, Swords, Trophy } from 'lucide-react'

type Health = { status: string; service: string }
type Fight = {
  fight_id: number
  encounter_id: number
  name: string
  start_time_ms: number
  end_time_ms: number
  duration_ms: number
  kill: boolean | null
  fight_percentage: number | null
  friendly_players: number[]
}
type Boss = { encounter_id: number; name: string; attempts: number; kills: number; wipes: number; fights: Fight[] }
type Report = {
  code: string
  title: string
  zone: string | null
  guild: string | null
  start_time: string
  end_time: string
  duration_ms: number
  fight_count: number
  boss_count: number
  kill_count: number
  wipe_count: number
  bosses: Boss[]
  fights: Fight[]
}
type FightAnalysis = { fight: Fight; tables: Record<string, unknown>; actors: Array<{ id: number; name: string; type: string; subType: string | null }> }
type PlayerInsight = { name: string; className: string | null; notes: string[] }

async function getHealth(): Promise<Health> {
  const response = await fetch('/api/health')
  if (!response.ok) throw new Error('API unavailable')
  return response.json()
}

async function parseReportURL(reportUrl: string): Promise<{ report_code: string }> {
  const response = await fetch('/api/reports/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report_url: reportUrl }),
  })
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.detail ?? 'Could not read that report URL.')
  return payload
}

async function fetchReport(code: string): Promise<Report> {
  const response = await fetch(`/api/reports/${encodeURIComponent(code)}`)
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.detail ?? 'Could not load this report.')
  return payload
}

async function fetchFights(code: string): Promise<Fight[]> {
  const response = await fetch(`/api/reports/${encodeURIComponent(code)}/fights`)
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.detail ?? 'Could not load fight progression.')
  return payload
}

async function fetchFightAnalysis(code: string, fightId: number): Promise<FightAnalysis> {
  const response = await fetch(`/api/reports/${encodeURIComponent(code)}/fights/${fightId}/analysis`)
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.detail ?? 'Could not load fight analysis.')
  return payload
}

function tableRows(value: unknown): Array<Record<string, unknown>> {
  let parsed = value
  if (typeof parsed === 'string') {
    try { parsed = JSON.parse(parsed) } catch { return [] }
  }
  if (Array.isArray(parsed)) return parsed.filter((row): row is Record<string, unknown> => Boolean(row) && typeof row === 'object')
  if (!parsed || typeof parsed !== 'object') return []
  const table = parsed as Record<string, unknown>
  for (const key of ['data', 'entries', 'actors', 'table']) {
    if (Array.isArray(table[key])) return (table[key] as unknown[]).filter((row): row is Record<string, unknown> => Boolean(row) && typeof row === 'object')
  }
  return []
}

function displayValue(value: unknown): string {
  if (typeof value === 'number') return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 1 })
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'string') return value
  return ''
}

function labelFor(key: string): string {
  return key.replace(/([A-Z])/g, ' $1').replace(/^./, (letter) => letter.toUpperCase())
}

function formatDuration(milliseconds: number): string {
  const totalSeconds = Math.floor(milliseconds / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function formatDate(date: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }).format(new Date(date)) + ' UTC'
}

function Header({ connected }: { connected?: boolean }) {
  return <header className="topbar">
    <a className="brand" href="/"><span className="brand-mark"><Command size={17} /></span><span>hellotherelogs</span><span className="version">LOCAL / 0.2</span></a>
    {connected !== undefined && <div className="system-status"><span className={`status-dot ${connected ? 'online' : ''}`} /> API {connected ? 'CONNECTED' : 'OFFLINE'}</div>}
  </header>
}

function HomePage() {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, retry: 1 })
  const [reportUrl, setReportUrl] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function analyzeReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const { report_code } = await parseReportURL(reportUrl)
      window.location.assign(`/reports/${encodeURIComponent(report_code)}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not read that report URL.')
      setSubmitting(false)
    }
  }

  return <main className="shell">
    <Header connected={health.isSuccess} />
    <section className="intro">
      <div className="eyebrow"><Activity size={14} /> WARCRAFT LOGS · FRESH</div>
      <h1>Read the raid.</h1>
      <p>A private, self-hosted workspace for understanding every pull.</p>
    </section>
    <section className="connect-panel">
      <div className="panel-heading"><div><span className="step">01</span><h2>Connect a report</h2></div><span className="ready"><Check size={14} /> READY FOR INPUT</span></div>
      <form className="report-form" onSubmit={analyzeReport}>
        <label htmlFor="report-url">REPORT URL</label>
        <div className="input-row"><input id="report-url" type="url" required value={reportUrl} onChange={(event) => setReportUrl(event.target.value)} placeholder="https://fresh.warcraftlogs.com/reports/…" /><button type="submit" disabled={submitting}>{submitting ? <LoaderCircle className="spin" size={15} /> : 'ANALYZE LOG'} {!submitting && <ArrowUpRight size={15} />}</button></div>
        {error && <p className="form-error" role="alert">{error}</p>}
      </form>
      <div className="panel-foot"><span>Paste a public Fresh report link to begin.</span><span>PRIVATE BY DESIGN</span></div>
    </section>
    <section className="empty-state"><div className="empty-icon"><Swords size={19} /></div><div><h3>Awaiting encounter data</h3><p>Report overview, boss progression, kills, wipes, and fight durations appear after analysis.</p></div><span className="empty-index">— / —</span></section>
    <Footer />
  </main>
}

function ReportPage({ code }: { code: string }) {
  const report = useQuery({ queryKey: ['report', code], queryFn: () => fetchReport(code), retry: 1 })
  const fights = useQuery({ queryKey: ['report-fights', code], queryFn: () => fetchFights(code), enabled: report.isSuccess, retry: 1 })
  const [selectedFightId, setSelectedFightId] = useState<number | null>(null)
  const analysisFightId = selectedFightId ?? report.data?.fights.find((fight) => fight.encounter_id > 0)?.fight_id ?? null
  const analysis = useQuery({ queryKey: ['fight-analysis', code, analysisFightId], queryFn: () => fetchFightAnalysis(code, analysisFightId as number), enabled: analysisFightId !== null, retry: 1 })
  const improvementNotes = useMemo(() => {
    if (!analysis.data) return []
    const deaths = tableRows(analysis.data.tables.deaths)
    const interrupts = tableRows(analysis.data.tables.interrupts)
    const notes: string[] = []
    if (deaths.length) notes.push(`${deaths.length} death record${deaths.length === 1 ? '' : 's'} in this pull. Review each death’s damage taken and the seconds before it to distinguish lethal mechanics from healing or defensive gaps.`)
    if (interrupts.length) notes.push(`Interrupt activity is available for ${interrupts.length} row${interrupts.length === 1 ? '' : 's'}. Compare interrupted casts with dangerous casts that completed before assigning kick coverage.`)
    if (!notes.length) notes.push('This pull has no death or interrupt rows to review. Use the damage, healing, damage taken, and buff uptime tables to find the next discussion point.')
    return notes
  }, [analysis.data])
  const playerInsights = useMemo<PlayerInsight[]>(() => {
    if (!analysis.data) return []
    const deaths = tableRows(analysis.data.tables.deaths)
    const interrupts = tableRows(analysis.data.tables.interrupts)
    const rowForActor = (rows: Array<Record<string, unknown>>, id: number) => rows.find((row) => Number(row.id ?? row.actorID ?? row.sourceID ?? row.targetID) === id)
    return analysis.data.actors.filter((actor) => actor.type === 'Player').map((actor) => {
      const death = rowForActor(deaths, actor.id)
      const interrupt = rowForActor(interrupts, actor.id)
      const deathCount = Number(death?.total ?? death?.count ?? 0)
      const interruptCount = Number(interrupt?.total ?? interrupt?.count ?? 0)
      const notes = deathCount > 0
        ? [`${deathCount} recorded death${deathCount === 1 ? '' : 's'}: review the damage and mechanic in the seconds before each death, then check defensive timing.`]
        : ['No death is recorded for this pull.']
      notes.push(interruptCount > 0
        ? `${interruptCount} recorded interrupt${interruptCount === 1 ? '' : 's'}: compare these with the assigned dangerous casts to spot coverage gaps.`
        : 'No interrupt is recorded. If assigned to interrupt, review missed casts and ability availability.')
      return { name: actor.name, className: actor.subType, notes }
    })
  }, [analysis.data])

  return <main className="shell report-shell">
    <Header connected />
    <div className="report-back"><a href="/"><ArrowLeft size={14} /> ALL REPORTS</a><a href={`https://fresh.warcraftlogs.com/reports/${encodeURIComponent(code)}`} target="_blank" rel="noreferrer">OPEN IN WARCRAFT LOGS <ExternalLink size={13} /></a></div>
    {report.isLoading && <section className="loading-panel"><LoaderCircle className="spin" size={18} /> FETCHING REPORT FROM FRESH WARCRAFT LOGS</section>}
    {report.isError && <section className="error-panel"><CircleHelp size={18} /><div><h2>Report could not be loaded</h2><p>{report.error.message}</p><a href="/">Try another report <ArrowUpRight size={13} /></a></div></section>}
    {report.data && <>
      <section className="report-heading">
        <div className="eyebrow"><Activity size={14} /> REPORT / {report.data.code}</div>
        <h1>{report.data.title}</h1>
        <div className="report-meta"><span>{report.data.zone ?? 'Unknown zone'}</span>{report.data.guild && <><i /> <span>{report.data.guild}</span></>}<i /><span>{formatDate(report.data.start_time)}</span></div>
      </section>
      <section className="stat-grid" aria-label="Report summary">
        <Stat icon={<Clock3 size={15} />} label="RAID DURATION" value={formatDuration(report.data.duration_ms)} tint="blue" />
        <Stat icon={<Swords size={15} />} label="BOSS ENCOUNTERS" value={String(report.data.boss_count).padStart(2, '0')} tint="lavender" />
        <Stat icon={<Trophy size={15} />} label="KILLS" value={String(report.data.kill_count).padStart(2, '0')} tint="mint" />
        <Stat icon={<Skull size={15} />} label="WIPES" value={String(report.data.wipe_count).padStart(2, '0')} tint="pink" />
      </section>
      <section className="progression-section">
        <div className="section-heading"><div><span className="step">02</span><h2>Boss progression</h2></div><span>{report.data.fight_count} TOTAL FIGHTS</span></div>
        {report.data.bosses.length === 0 ? <div className="no-bosses">No boss encounters were found in this report.</div> : <div className="boss-list">
          {report.data.bosses.map((boss, index) => <article className="boss-row" key={boss.encounter_id}>
            <div className="boss-summary"><span className="boss-index">{String(index + 1).padStart(2, '0')}</span><span className="boss-mark"><Swords size={16} /></span><div className="boss-name"><h3>{boss.name}</h3><span>ENCOUNTER {boss.encounter_id} · {boss.attempts} {boss.attempts === 1 ? 'ATTEMPT' : 'ATTEMPTS'}</span></div><div className="boss-results"><span className="kill-count"><Trophy size={13} /> {boss.kills}</span><span className="wipe-count"><Skull size={13} /> {boss.wipes}</span></div><div className={`boss-state ${boss.kills ? 'boss-killed' : 'boss-open'}`}>{boss.kills ? 'DEFEATED' : 'IN PROGRESS'}</div></div>
            <div className="attempt-list">{boss.fights.map((fight, attempt) => <div className="attempt" key={fight.fight_id}>
              <span className="attempt-number">PULL {String(attempt + 1).padStart(2, '0')}</span>
              <span className={`attempt-status ${fight.kill ? 'attempt-kill' : fight.kill === false ? 'attempt-wipe' : 'attempt-unknown'}`}>{fight.kill ? 'KILL' : fight.kill === false ? 'WIPE' : 'UNKNOWN'}</span>
              <div className="attempt-track"><span className={fight.kill ? 'track-kill' : 'track-wipe'} style={{ width: `${fight.kill ? 100 : Math.max(4, Math.min(100, fight.fight_percentage ?? 4))}%` }} /></div>
              <span className="attempt-duration">{formatDuration(fight.duration_ms)}</span>
              {fight.fight_percentage !== null && fight.fight_percentage !== undefined && !fight.kill && <span className="attempt-percent">{fight.fight_percentage.toFixed(1)}%</span>}
            </div>)}</div>
          </article>)}
        </div>}
      </section>
      <section className="analysis-section">
        <div className="section-heading"><div><span className="step">03</span><h2>Encounter review</h2></div><span>PLAYER METRICS & REVIEW POINTS</span></div>
        <div className="analysis-controls"><label htmlFor="fight-select">SELECT A PULL</label><select id="fight-select" value={analysisFightId ?? ''} onChange={(event) => setSelectedFightId(Number(event.target.value))}>
          {report.data.fights.filter((fight) => fight.encounter_id > 0).map((fight, index) => <option key={fight.fight_id} value={fight.fight_id}>{fight.name} · Pull {index + 1} · {fight.kill ? 'Kill' : 'Wipe'} · {formatDuration(fight.duration_ms)}</option>)}
        </select></div>
        {analysis.isLoading && <div className="minor-loading"><LoaderCircle className="spin" size={14} /> LOADING DAMAGE, HEALING, SURVIVABILITY, INTERRUPTS & UPTIME</div>}
        {analysis.isError && <div className="inline-error">Encounter analysis unavailable: {analysis.error.message}</div>}
        {analysis.data && <>
          <div className="review-notes"><h3>Review points</h3>{improvementNotes.map((note) => <p key={note}>{note}</p>)}<small>These are evidence-led prompts, not player grades. Encounter mechanics and assigned roles matter.</small></div>
          <div className="player-review"><h3>Player review</h3><div className="player-review-grid">{playerInsights.map((player) => <article className="player-review-card" key={player.name}><div><strong>{player.name}</strong><span>{player.className ?? 'Player'}</span></div>{player.notes.map((note) => <p key={note}>{note}</p>)}</article>)}</div></div>
          <div className="analysis-grid">
            <AnalysisTable title="Damage done" value={analysis.data.tables.damage} />
            <AnalysisTable title="Healing done" value={analysis.data.tables.healing} />
            <AnalysisTable title="Damage taken" value={analysis.data.tables.damage_taken} />
            <AnalysisTable title="Deaths" value={analysis.data.tables.deaths} />
            <AnalysisTable title="Interrupts" value={analysis.data.tables.interrupts} />
            <AnalysisTable title="Buff uptime" value={analysis.data.tables.buff_uptimes} />
          </div>
        </>}
      </section>
      <section className="fight-log">
        <div className="section-heading"><div><span className="step">04</span><h2>Fight log</h2></div><span>{fights.data?.length ?? '—'} ENTRIES</span></div>
        {fights.isLoading && <div className="minor-loading"><LoaderCircle className="spin" size={14} /> LOADING FIGHTS</div>}
        {fights.isError && <div className="inline-error">Fight list unavailable: {fights.error.message}</div>}
        {fights.data?.filter((fight) => fight.encounter_id === 0).map((fight) => <div className="trash-row" key={fight.fight_id}><span>TRASH</span><strong>{fight.name}</strong><span>{formatDuration(fight.duration_ms)}</span></div>)}
      </section>
    </>}
    <Footer />
  </main>
}

function AnalysisTable({ title, value }: { title: string; value: unknown }) {
  const rows = tableRows(value)
  const keys = [...new Set(rows.flatMap((row) => Object.keys(row)))]
  const columns = keys.filter((key) => rows.some((row) => ['string', 'number', 'boolean'].includes(typeof row[key])))
  const priority = ['name', 'type', 'total', 'dps', 'hps', 'uptime', 'activeTime', 'count', 'deaths', 'id']
  columns.sort((a, b) => (priority.indexOf(a) < 0 ? 100 : priority.indexOf(a)) - (priority.indexOf(b) < 0 ? 100 : priority.indexOf(b)))
  const hasDetails = rows.some((row) => Object.values(row).some((field) => field !== null && typeof field === 'object'))
  return <article className="analysis-card"><h3>{title}</h3>{rows.length === 0 ? <p className="analysis-empty">No rows returned for this pull.</p> : <div className="analysis-table-wrap"><table><thead><tr>{columns.slice(0, 7).map((column) => <th key={column}>{labelFor(column)}</th>)}{hasDetails && <th>Breakdown</th>}</tr></thead><tbody>{rows.slice(0, 30).map((row, index) => <tr key={`${String(row.id ?? row.name ?? title)}-${index}`}>{columns.slice(0, 7).map((column) => <td key={column}>{displayValue(row[column])}</td>)}{hasDetails && <td>{Object.values(row).some((field) => field !== null && typeof field === 'object') && <details><summary>View</summary><pre>{JSON.stringify(Object.fromEntries(Object.entries(row).filter(([, field]) => field !== null && typeof field === 'object')), null, 2)}</pre></details>}</td>}</tr>)}</tbody></table></div>}</article>
}

function Stat({ icon, label, value, tint }: { icon: ReactNode; label: string; value: string; tint: string }) {
  return <article className="stat-card"><span className={`stat-icon tint-${tint}`}>{icon}</span><span className="stat-label">{label}</span><strong>{value}</strong></article>
}

function Footer() {
  return <footer><span>HELLOTHERELOGS <span className="muted">· SELF-HOSTED RAID ANALYTICS</span></span><span>WCL CREDENTIALS STAY SERVER-SIDE</span></footer>
}

export default function App() {
  const match = window.location.pathname.match(/^\/reports\/([A-Za-z0-9]+)\/?$/)
  return match ? <ReportPage code={match[1]} /> : <HomePage />
}

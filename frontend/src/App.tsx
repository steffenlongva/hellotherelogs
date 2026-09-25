import { FormEvent, ReactNode, useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import './analysis.css'
import { Activity, ArrowLeft, ArrowUpRight, Check, CircleHelp, Clock3, Command, ExternalLink, LoaderCircle, Moon, Skull, Sun, Swords, Trophy } from 'lucide-react'

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
type Actor = { id: number; name: string; type: string; subType: string | null }
type FightAnalysis = { fight: Fight; tables: Record<string, unknown>; events: Record<string, unknown>; player_details: unknown; actors: Actor[] }
type PlayerStats = Actor & { damage: number | null; dps: number | null; healing: number | null; hps: number | null; damageTaken: number | null; friendlyDamage: number | null; deaths: Array<Record<string, unknown>>; interrupts: Array<Record<string, unknown>>; consumables: string[]; gear: Array<Record<string, unknown>>; auras: string[] }

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

function parseJSON(value: unknown): unknown {
  let parsed = value
  if (typeof parsed === 'string') {
    try { parsed = JSON.parse(parsed) } catch { return value }
  }
  return parsed
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function tableRows(value: unknown, depth = 0): Array<Record<string, unknown>> {
  const parsed = parseJSON(value)
  if (depth > 7 || parsed === null || parsed === undefined) return []
  if (Array.isArray(parsed)) {
    const records = parsed.filter(isRecord)
    if (records.some((row) => ['name', 'id', 'guid', 'total', 'amount', 'timestamp', 'sourceID', 'targetID', 'type'].some((key) => row[key] !== undefined))) return records
    return records.flatMap((row) => tableRows(row, depth + 1))
  }
  if (!isRecord(parsed)) return []
  for (const key of ['data', 'entries', 'events', 'actors', 'table', 'series', 'groups', 'sources', 'targets', 'players']) {
    if (parsed[key] !== undefined) {
      const rows = tableRows(parsed[key], depth + 1)
      if (rows.length) return rows
    }
  }
  return []
}

function eventDataAvailable(value: unknown): boolean {
  if (value === null || value === undefined) return false
  const parsed = parseJSON(value)
  if (isRecord(parsed) && 'data' in parsed) return parsed.data !== null && parsed.data !== undefined
  return true
}

function allRecords(value: unknown, output: Array<Record<string, unknown>> = [], depth = 0): Array<Record<string, unknown>> {
  const parsed = parseJSON(value)
  if (depth > 9 || parsed === null || parsed === undefined) return output
  if (Array.isArray(parsed)) {
    for (const item of parsed) allRecords(item, output, depth + 1)
  } else if (isRecord(parsed)) {
    output.push(parsed)
    for (const item of Object.values(parsed)) allRecords(item, output, depth + 1)
  }
  return output
}

function actorId(row: Record<string, unknown>, role?: 'source' | 'target'): number | null {
  const nested = role && isRecord(row[role]) ? row[role] as Record<string, unknown> : null
  const value = (role === 'source' ? row.sourceID ?? row.sourceId : role === 'target' ? row.targetID ?? row.targetId : undefined)
    ?? row.id ?? row.actorID ?? row.actorId ?? nested?.id
  const id = Number(value)
  return Number.isFinite(id) ? id : null
}

function actorName(row: Record<string, unknown>, role?: 'source' | 'target'): string {
  const nested = role && isRecord(row[role]) ? row[role] as Record<string, unknown> : null
  const value = (role === 'source' ? row.sourceName : role === 'target' ? row.targetName : undefined)
    ?? row.name ?? nested?.name
  return typeof value === 'string' ? value : 'Unknown'
}

function rowForActor(value: unknown, actor: Actor, role?: 'source' | 'target'): Record<string, unknown> | undefined {
  return tableRows(value).find((row) => actorId(row, role) === actor.id || (actorId(row, role) === null && actorName(row, role) === actor.name))
}

function numericValue(row: Record<string, unknown> | undefined, keys: string[]): number | null {
  for (const key of keys) {
    const value = row?.[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (isRecord(value)) {
      const nested = Object.values(value).find((item) => typeof item === 'number')
      if (typeof nested === 'number') return nested
    }
  }
  return null
}

function makePlayerStats(analysis: FightAnalysis): PlayerStats[] {
  const participants = new Set(analysis.fight.friendly_players)
  const deaths = tableRows(analysis.events.deaths)
  const interrupts = tableRows(analysis.events.interrupts)
  const combatantEvents = tableRows(analysis.events.combatant_info)
  const durationSeconds = analysis.fight.duration_ms / 1000
  return analysis.actors
    .filter((actor) => actor.type === 'Player' && participants.has(actor.id))
    .map((actor) => {
      const damageRow = rowForActor(analysis.tables.damage, actor, 'source')
      const healingRow = rowForActor(analysis.tables.healing, actor, 'source')
      const takenRow = rowForActor(analysis.tables.damage_taken, actor, 'target')
      const friendlyRow = rowForActor(analysis.tables.friendly_damage, actor, 'source')
      const castsRow = rowForActor(analysis.tables.casts, actor, 'source')
      const actorDeathEvents = deaths.filter((event) => actorId(event, 'target') === actor.id)
      const actorInterrupts = interrupts.filter((event) => actorId(event, 'source') === actor.id)
      const actorCombatant = combatantEvents.find((event) => actorId(event, 'source') === actor.id || actorId(event, 'target') === actor.id)
      const details = allRecords(analysis.player_details).find((record) => Number(record.id ?? record.actorID ?? record.actorId) === actor.id && (Array.isArray(record.gear) || isRecord(record.combatantInfo) || isRecord(record.combatantinfo)))
      const combatantInfo = isRecord(details?.combatantInfo) ? details.combatantInfo : isRecord(details?.combatantinfo) ? details.combatantinfo : actorCombatant
      const gear = Array.isArray(details?.gear) ? details.gear.filter(isRecord) : Array.isArray(combatantInfo?.gear) ? combatantInfo.gear.filter(isRecord) : []
      const auras = Array.isArray(combatantInfo?.auras) ? combatantInfo.auras.map((aura) => isRecord(aura) ? String((isRecord(aura.ability) ? aura.ability.name : undefined) ?? aura.name ?? '') : '').filter(Boolean) : []
      const consumablePattern = /potion|flask|elixir|food|feast|rune|healthstone|mana stone|wizard oil|sharpening|consecrated|free action|protection potion/i
      const consumables = [...new Set(allRecords(castsRow).map((record) => record.name).filter((name): name is string => typeof name === 'string' && consumablePattern.test(name)))]
      return {
        ...actor,
        damage: numericValue(damageRow, ['total', 'amount', 'damage']),
        dps: numericValue(damageRow, ['dps']) ?? (numericValue(damageRow, ['total', 'amount', 'damage']) !== null && durationSeconds > 0 ? (numericValue(damageRow, ['total', 'amount', 'damage']) as number) / durationSeconds : null),
        healing: numericValue(healingRow, ['total', 'amount', 'healing']),
        hps: numericValue(healingRow, ['hps']) ?? (numericValue(healingRow, ['total', 'amount', 'healing']) !== null && durationSeconds > 0 ? (numericValue(healingRow, ['total', 'amount', 'healing']) as number) / durationSeconds : null),
        damageTaken: numericValue(takenRow, ['total', 'amount', 'damageTaken', 'damage']),
        friendlyDamage: numericValue(friendlyRow, ['total', 'amount', 'damage']),
        deaths: actorDeathEvents,
        interrupts: actorInterrupts,
        consumables,
        gear,
        auras,
      }
    })
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

function AppearanceControls() {
  const [theme, setTheme] = useState(() => localStorage.getItem('htl-theme') === 'light' ? 'light' : 'dark')
  const [fontScale, setFontScale] = useState(() => {
    const stored = Number(localStorage.getItem('htl-font-scale'))
    return Number.isFinite(stored) && stored >= 0.9 && stored <= 1.3 ? stored : 1
  })
  useEffect(() => {
    document.body.dataset.theme = theme
    document.documentElement.style.setProperty('--font-scale', String(fontScale))
    localStorage.setItem('htl-theme', theme)
    localStorage.setItem('htl-font-scale', String(fontScale))
  }, [theme, fontScale])
  return <div className="appearance-controls" aria-label="Display settings">
    <label className="font-scale-control" title="Adjust interface text size"><span>A</span><input aria-label="Text size" type="range" min="0.9" max="1.3" step="0.05" value={fontScale} onChange={(event) => setFontScale(Number(event.target.value))} /><span className="large-a">A</span></label>
    <button className="theme-toggle" type="button" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>{theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}<span>{theme === 'dark' ? 'LIGHT' : 'DARK'}</span></button>
  </div>
}

function Header({ connected }: { connected?: boolean }) {
  return <header className="topbar">
    <a className="brand" href="/"><span className="brand-mark"><Command size={17} /></span><span>hellotherelogs</span><span className="version">LOCAL / 0.2</span></a>
    <div className="topbar-tools"><AppearanceControls />
    {connected !== undefined && <div className="system-status"><span className={`status-dot ${connected ? 'online' : ''}`} /> API {connected ? 'CONNECTED' : 'OFFLINE'}</div>}
    </div>
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
  const playerStats = useMemo(() => analysis.data ? makePlayerStats(analysis.data) : [], [analysis.data])
  const deathEvents = analysis.data ? tableRows(analysis.data.events.deaths) : []
  const interruptEvents = analysis.data ? tableRows(analysis.data.events.interrupts) : []
  const metricLeaders = (key: 'damage' | 'healing' | 'damageTaken' | 'friendlyDamage') => [...playerStats].filter((player) => player[key] !== null).sort((a, b) => (b[key] ?? 0) - (a[key] ?? 0)).slice(0, 5)

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
          <div className="review-notes"><h3>Pull review</h3><p>Showing {playerStats.length} friendly players recorded in this pull. Compare output alongside assignments, role and encounter mechanics.</p><small>Suggestions use observable log evidence. Missing data is shown as unavailable; a zero is only shown when the event data is present.</small></div>
          <div className="leader-grid">
            <LeaderCard title="Top damage" players={metricLeaders('damage')} metric="damage" tint="blue" />
            <LeaderCard title="Top healing" players={metricLeaders('healing')} metric="healing" tint="mint" />
            <LeaderCard title="Most damage taken" players={metricLeaders('damageTaken')} metric="damageTaken" tint="pink" />
            <LeaderCard title="Friendly fire" players={metricLeaders('friendlyDamage')} metric="friendlyDamage" tint="lavender" />
          </div>
          <article className="analysis-card roster-card"><div className="card-heading"><div><h3>Player performance</h3><p>Per pull totals and event counts</p></div><span>{playerStats.length} PLAYERS</span></div>
            {playerStats.length === 0 ? <p className="analysis-empty">No friendly player roster was returned for this pull.</p> : <div className="analysis-table-wrap"><table><thead><tr><th>Player</th><th>Damage</th><th>DPS</th><th>Healing</th><th>HPS</th><th>Damage taken</th><th>Friendly damage</th><th>Deaths</th><th>Interrupts</th></tr></thead><tbody>{playerStats.map((player) => <tr key={player.id}><td><strong>{player.name}</strong><small>{player.subType ?? 'Player'}</small></td><td>{formatMetric(player.damage)}</td><td>{formatMetric(player.dps)}</td><td>{formatMetric(player.healing)}</td><td>{formatMetric(player.hps)}</td><td>{formatMetric(player.damageTaken)}</td><td>{formatMetric(player.friendlyDamage)}</td><td>{eventDataAvailable(analysis.data?.events.deaths) ? player.deaths.length : '—'}</td><td>{eventDataAvailable(analysis.data?.events.interrupts) ? player.interrupts.length : '—'}</td></tr>)}</tbody></table></div>}
          </article>
          <div className="detail-grid">
            <EventCard title="Deaths" rows={deathEvents} unavailable={!eventDataAvailable(analysis.data.events.deaths)} kind="death" fight={analysis.data.fight} />
            <EventCard title="Interrupts" rows={interruptEvents} unavailable={!eventDataAvailable(analysis.data.events.interrupts)} kind="interrupt" fight={analysis.data.fight} />
          </div>
          <article className="analysis-card roster-card"><div className="card-heading"><div><h3>Gear, auras & consumables</h3><p>Only fields present in the Warcraft Logs response are shown</p></div></div><div className="equipment-grid">{playerStats.map((player) => <section className="equipment-player" key={player.id}><h4>{player.name} <span>{player.subType ?? ''}</span></h4>{player.gear.length ? <ul>{player.gear.map((item, index) => <li key={index}><strong>{String(item.name ?? item.itemName ?? `Item ${item.id ?? ''}`)}</strong><span>{item.itemLevel ? `ilvl ${displayValue(item.itemLevel)}` : ''}{item.permanentEnchantName ? ` · ${String(item.permanentEnchantName)}` : ''}{item.temporaryEnchantName ? ` · ${String(item.temporaryEnchantName)}` : ''}{Array.isArray(item.gems) ? ` · ${item.gems.map((gem) => isRecord(gem) ? String(gem.name ?? gem.itemLevel ?? 'gem') : String(gem)).join(', ')}` : ''}</span></li>)}</ul> : <p className="analysis-empty">Gear detail unavailable</p>}{player.auras.length > 0 && <p className="equipment-meta"><b>Auras at pull</b> · {player.auras.join(', ')}</p>}<p className="equipment-meta"><b>Consumable casts</b> · {player.consumables.length ? player.consumables.join(', ') : 'No matching casts returned'}</p></section>)}</div></article>
          <div className="analysis-grid">
            <AnalysisTable title="Ability uptime" value={analysis.data.tables.buff_uptimes} />
            <AnalysisTable title="Cast activity" value={analysis.data.tables.casts} />
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

function formatMetric(value: number | null): string { return value === null ? '—' : Math.round(value).toLocaleString() }

function LeaderCard({ title, players, metric, tint }: { title: string; players: PlayerStats[]; metric: 'damage' | 'healing' | 'damageTaken' | 'friendlyDamage'; tint: string }) {
  const max = Math.max(1, ...players.map((player) => player[metric] ?? 0))
  return <article className="leader-card"><h3><span className={`leader-dot tint-${tint}`} />{title}</h3>{players.length === 0 ? <p className="analysis-empty">Metric unavailable</p> : players.map((player, index) => <div className="leader-row" key={player.id}><span className="leader-rank">{index + 1}</span><span className="leader-name">{player.name}<i><b style={{ width: `${Math.max(3, 100 * (player[metric] ?? 0) / max)}%` }} /></i></span><strong>{formatMetric(player[metric])}</strong></div>)}</article>
}

function EventCard({ title, rows, unavailable, kind, fight }: { title: string; rows: Array<Record<string, unknown>>; unavailable: boolean; kind: 'death' | 'interrupt'; fight: Fight }) {
  return <article className="analysis-card event-card"><div className="card-heading"><div><h3>{title}</h3><p>Encounter event timeline</p></div><span>{unavailable ? 'UNAVAILABLE' : `${rows.length} EVENTS`}</span></div>{unavailable ? <p className="analysis-empty">The log response did not include this event data.</p> : rows.length === 0 ? <p className="analysis-empty">No {kind} events were recorded for this pull.</p> : <div className="event-list">{rows.map((row, index) => { const time = Number(row.timestamp); const relative = Number.isFinite(time) ? Math.max(0, time - fight.start_time_ms) : null; return <div className="event-row" key={`${index}-${String(row.timestamp ?? '')}`}><time>{relative === null ? '—' : formatDuration(relative)}</time><strong>{actorName(row, kind === 'death' ? 'target' : 'source')}</strong><span>{String((isRecord(row.ability) && row.ability.name) || row.abilityName || row.name || (kind === 'death' ? 'Death' : 'Interrupt'))}</span>{kind === 'death' && <small>{String((isRecord(row.killingAbility) && row.killingAbility.name) || row.killerName || '')}</small>}</div>})}</div>}</article>
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

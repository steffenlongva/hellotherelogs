import { Activity, ArrowUpRight, Command, ShieldCheck, Swords } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'

type Health = { status: string; service: string }

async function getHealth(): Promise<Health> {
  const response = await fetch('/api/health')
  if (!response.ok) throw new Error('API unavailable')
  return response.json()
}

export default function App() {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, retry: 1 })

  return <main className="shell">
    <header className="topbar">
      <a className="brand" href="#"><span className="brand-mark"><Command size={17} /></span><span>logloom</span><span className="version">LOCAL / 0.1</span></a>
      <div className="system-status"><span className={`status-dot ${health.isSuccess ? 'online' : ''}`} /> API {health.isSuccess ? 'CONNECTED' : health.isLoading ? 'CHECKING' : 'OFFLINE'}</div>
    </header>
    <section className="intro">
      <div className="eyebrow"><Activity size={14} /> WARCRAFT LOGS · FRESH</div>
      <h1>Read the raid.</h1>
      <p>A private, self-hosted workspace for understanding every pull.</p>
    </section>
    <section className="connect-panel">
      <div className="panel-heading"><div><span className="step">01</span><h2>Connect a report</h2></div><span className="ready"><ShieldCheck size={14} /> READY FOR INPUT</span></div>
      <form className="report-form" onSubmit={(event) => event.preventDefault()}>
        <label htmlFor="report-url">REPORT URL</label>
        <div className="input-row"><input id="report-url" type="url" placeholder="https://fresh.warcraftlogs.com/reports/…" /><button type="submit">OPEN REPORT <ArrowUpRight size={15} /></button></div>
      </form>
      <div className="panel-foot"><span>Paste a public Fresh report link to begin.</span><span>PRIVATE BY DESIGN</span></div>
    </section>
    <section className="empty-state"><div className="empty-icon"><Swords size={19} /></div><div><h3>Awaiting encounter data</h3><p>Your report overview, progression, and fight analysis will appear here.</p></div><span className="empty-index">— / —</span></section>
    <footer><span>LOGLOOM <span className="muted">· SELF-HOSTED RAID ANALYTICS</span></span><span>WCL CREDENTIALS STAY SERVER-SIDE</span></footer>
  </main>
}

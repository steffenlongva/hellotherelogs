export const refreshIntervals = [30, 60, 120, 300]
export const sessionDurations = [30, 60, 120, 240]
export const defaultSessionMinutes = 120

export type LiveSession = { refreshSeconds: number; endsAt: number }

export function startLiveSession(refreshSeconds: number, minutes: number, now = Date.now()): LiveSession {
  return {
    refreshSeconds: refreshIntervals.includes(refreshSeconds) ? refreshSeconds : 0,
    endsAt: now + (sessionDurations.includes(minutes) ? minutes : defaultSessionMinutes) * 60_000,
  }
}

export function readLiveSession(search: string, now = Date.now()): LiveSession {
  const params = new URLSearchParams(search)
  const refreshSeconds = Number(params.get('refresh'))
  if (!refreshIntervals.includes(refreshSeconds)) return { refreshSeconds: 0, endsAt: 0 }
  // Older live links get one bounded session; the caller persists its deadline.
  if (!params.has('until')) return startLiveSession(refreshSeconds, defaultSessionMinutes, now)
  const endsAt = Number(params.get('until'))
  return { refreshSeconds, endsAt: Number.isFinite(endsAt) && endsAt > 0 && endsAt <= now + 240 * 60_000 ? endsAt : now }
}

export function isLiveSessionActive(session: LiveSession, now = Date.now()): boolean {
  return session.refreshSeconds > 0 && now < session.endsAt
}

export function changeLiveInterval(session: LiveSession, refreshSeconds: number, minutes: number, now = Date.now()): LiveSession {
  if (!refreshIntervals.includes(refreshSeconds)) return { ...session, refreshSeconds: 0 }
  return isLiveSessionActive(session, now) ? { ...session, refreshSeconds } : startLiveSession(refreshSeconds, minutes, now)
}

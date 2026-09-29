import assert from 'node:assert/strict'
import test from 'node:test'
import { changeLiveInterval, isLiveSessionActive, readLiveSession, startLiveSession } from '../src/live-session.ts'

const now = 1_800_000_000_000

test('sessions stop at their deadline even after a long background sleep', () => {
  const session = startLiveSession(30, 30, now)
  assert.equal(isLiveSessionActive(session, session.endsAt - 1), true)
  assert.equal(isLiveSessionActive(session, session.endsAt), false)
  assert.equal(isLiveSessionActive(session, session.endsAt + 24 * 60 * 60_000), false)
})

test('reloading or reopening a live URL never extends its deadline', () => {
  const session = startLiveSession(60, 120, now)
  const search = `?refresh=60&until=${session.endsAt}`
  assert.deepEqual(readLiveSession(search, now + 60_000), session)
  const reopened = readLiveSession(search, session.endsAt + 1)
  assert.equal(reopened.endsAt, session.endsAt)
  assert.equal(isLiveSessionActive(reopened, session.endsAt + 1), false)
})

test('old live links default to two hours and ordinary reports stay off', () => {
  assert.deepEqual(readLiveSession('?refresh=60', now), startLiveSession(60, 120, now))
  assert.deepEqual(readLiveSession('', now), { refreshSeconds: 0, endsAt: 0 })
  assert.equal(readLiveSession('?refresh=1', now).refreshSeconds, 0)
})

test('invalid and unbounded deadlines cannot enable endless polling', () => {
  for (const until of ['Infinity', 'NaN', '', '-1', String(now + 241 * 60_000)]) {
    assert.equal(isLiveSessionActive(readLiveSession(`?refresh=30&until=${until}`, now), now), false)
  }
})

test('changing frequency preserves the deadline and Off stops immediately', () => {
  const session = startLiveSession(60, 30, now)
  const changed = changeLiveInterval(session, 30, 240, now + 60_000)
  assert.equal(changed.endsAt, session.endsAt)
  assert.equal(changed.refreshSeconds, 30)
  assert.equal(isLiveSessionActive(changeLiveInterval(changed, 0, 240, now + 60_000), now + 60_000), false)
})

test('only an explicit new session starts a fresh deadline after expiry', () => {
  const session = startLiveSession(60, 30, now)
  const restarted = changeLiveInterval(session, 120, 60, session.endsAt + 1)
  assert.equal(restarted.endsAt, session.endsAt + 1 + 60 * 60_000)
  assert.equal(isLiveSessionActive(restarted, session.endsAt + 1), true)
})

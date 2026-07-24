const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function request(path, options = {}) {
  const response = await fetch(`${BASE}/api${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (body.detail) detail = body.detail
    } catch {
      // Non-JSON error body — the status message is the best we have.
    }
    throw new Error(detail)
  }

  return response.status === 204 ? null : response.json()
}

export const getHealth = () => request('/health')
export const listComplaints = () => request('/complaints')
export const saveComplaint = (payload) =>
  request('/complaints', { method: 'POST', body: JSON.stringify(payload) })
export const checkDuplicates = (payload) =>
  request('/complaints/check-duplicates', { method: 'POST', body: JSON.stringify(payload) })
export const askAssistant = (payload) =>
  request('/ai/chat', { method: 'POST', body: JSON.stringify(payload) })

/**
 * Runs the extraction agent and calls onEvent for each NDJSON line the server
 * emits, so the progress bar tracks real graph nodes rather than a timer.
 */
export async function streamExtraction({ file, text }, onEvent) {
  const form = new FormData()
  if (file) form.append('file', file)
  if (text) form.append('text', text)

  const response = await fetch(`${BASE}/api/ai/extract`, { method: 'POST', body: form })

  if (!response.ok) {
    let detail = `Extraction failed (${response.status})`
    try {
      const body = await response.json()
      if (body.detail) detail = body.detail
    } catch {
      /* keep the status-based message */
    }
    throw new Error(detail)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    // The last element may be a partial line; hold it back until more arrives.
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.trim()) continue
      try {
        onEvent(JSON.parse(line))
      } catch {
        console.warn('Skipped malformed stream line:', line)
      }
    }
  }

  if (buffer.trim()) {
    try {
      onEvent(JSON.parse(buffer))
    } catch {
      console.warn('Skipped malformed trailing line:', buffer)
    }
  }
}

import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'

import { sendChatMessage, userMessageAdded } from '../store/aiSlice'

export default function ChatBox() {
  const dispatch = useDispatch()
  const { messages, chatPending } = useSelector((state) => state.ai)
  const [draft, setDraft] = useState('')
  const logRef = useRef(null)

  useEffect(() => {
    // Keep the newest message in view as the thread grows.
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, chatPending])

  const submit = (event) => {
    event.preventDefault()
    const message = draft.trim()
    if (!message || chatPending) return

    dispatch(userMessageAdded(message))
    dispatch(sendChatMessage(message))
    setDraft('')
  }

  return (
    <>
      <div className="assistant-label">AI assistant</div>

      <div className="chat-log" ref={logRef} aria-live="polite">
        {messages.length === 0 ? (
          <div className="bubble bubble-assistant">
            Upload a complaint document or paste the text above. I will extract the
            details, populate the form, and assess the initial risk. You can then ask
            me anything about the complaint.
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`bubble ${message.role === 'user' ? 'bubble-user' : 'bubble-assistant'}`}
            >
              {message.content}
            </div>
          ))
        )}

        {chatPending && <div className="bubble bubble-assistant">Thinking…</div>}
      </div>

      <form className="chat-form" onSubmit={submit}>
        <label className="visually-hidden" htmlFor="chat-input">
          Ask about this complaint
        </label>
        <input
          id="chat-input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask me anything about this complaint..."
        />
        <button
          type="submit"
          className="chat-send"
          disabled={chatPending || !draft.trim()}
          aria-label="Send message"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>

      <p className="disclaimer">
        AI responses may contain errors. Verify before triage.
      </p>
    </>
  )
}

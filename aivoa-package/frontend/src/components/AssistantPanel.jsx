import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'

import { runExtraction } from '../store/aiSlice'
import AiInsights from './AiInsights'
import ChatBox from './ChatBox'
import DropZone from './DropZone'
import ExtractionProgress from './ExtractionProgress'

export default function AssistantPanel() {
  const dispatch = useDispatch()
  const { isExtracting, error, sourceDocumentName, health } = useSelector((state) => state.ai)
  const [pasteMode, setPasteMode] = useState(false)
  const [pastedText, setPastedText] = useState('')

  const analyseFile = (file) => dispatch(runExtraction({ file }))

  const analyseText = () => {
    if (pastedText.trim()) dispatch(runExtraction({ text: pastedText.trim() }))
  }

  return (
    <section className="panel" aria-labelledby="assistant-heading">
      <header className="panel-header">
        <div>
          <h2 className="panel-title" style={{ fontSize: 16 }} id="assistant-heading">
            AI Complaint Intake Assistant
          </h2>
          <p className="panel-subtitle">
            Powered by LangGraph
            {health?.extraction_model ? ` · ${health.extraction_model}` : ''}
          </p>
        </div>
        <span className={`badge ${health?.llm_enabled ? 'badge-green' : 'badge-grey'}`}>
          {health ? (health.llm_enabled ? 'AI live' : 'Offline mode') : 'Checking…'}
        </span>
      </header>

      <div className="panel-body">
        {!pasteMode ? (
          <>
            <DropZone onFile={analyseFile} disabled={isExtracting} />
            <div className="divider">OR</div>
            <button
              type="button"
              className="btn"
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={() => setPasteMode(true)}
              disabled={isExtracting}
            >
              Paste complaint text / email
            </button>
          </>
        ) : (
          <>
            <label className="field-label" htmlFor="paste-area">
              Complaint text or email body
            </label>
            <textarea
              id="paste-area"
              rows={8}
              value={pastedText}
              onChange={(event) => setPastedText(event.target.value)}
              placeholder="Paste the customer's email or complaint text here..."
              style={{ marginTop: 5 }}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={analyseText}
                disabled={isExtracting || !pastedText.trim()}
              >
                {isExtracting && <span className="spinner" aria-hidden="true" />}
                {isExtracting ? 'Analysing…' : 'Analyse complaint'}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => setPasteMode(false)}
                disabled={isExtracting}
              >
                Upload a file instead
              </button>
            </div>
          </>
        )}

        <div className="hint hint-green">
          <div>
            Supported formats: PDF, DOCX, TXT, EML
            <br />
            Max file size: 10 MB
          </div>
        </div>

        {sourceDocumentName && (
          <div className="hint hint-blue">
            <div>
              Analysing <strong>{sourceDocumentName}</strong>
            </div>
          </div>
        )}

        {error && (
          <div className="hint hint-red" role="alert">
            <div>{error}</div>
          </div>
        )}

        <ExtractionProgress />
        <AiInsights />
        <ChatBox />
      </div>
    </section>
  )
}

import { useSelector } from 'react-redux'

const SEVERITY_CLASS = {
  Critical: 'badge-red',
  Major: 'badge-amber',
  Minor: 'badge-grey',
}

/**
 * Everything the agent produced beyond the form fields themselves. Each block
 * is framed as a suggestion for a QA reviewer to accept or reject — the model
 * proposes, the human disposes.
 */
export default function AiInsights() {
  const { insights } = useSelector((state) => state.ai)
  const { completeness, risk, duplicates, recommendations, summary, warnings } = insights

  const hasAnything =
    completeness || risk || summary || duplicates.length > 0 || recommendations

  if (!hasAnything && warnings.length === 0) return null

  return (
    <div>
      {warnings.map((warning) => (
        <div className="hint hint-amber" key={warning}>
          <div>{warning}</div>
        </div>
      ))}

      {summary && (
        <div className="insight">
          <div className="insight-title">
            <span>Complaint summary</span>
          </div>
          <p>{summary}</p>
        </div>
      )}

      {risk && (risk.severity || risk.rationale) && (
        <div className="insight">
          <div className="insight-title">
            <span>AI risk classification</span>
            <span style={{ display: 'flex', gap: 6 }}>
              {risk.severity && (
                <span className={`badge ${SEVERITY_CLASS[risk.severity] || 'badge-grey'}`}>
                  {risk.severity}
                </span>
              )}
              {risk.priority && <span className="badge badge-blue">{risk.priority}</span>}
            </span>
          </div>
          {risk.rationale && <p>{risk.rationale}</p>}
          {risk.regulatory_reportable && (
            <p style={{ marginTop: 6, color: 'var(--red)', fontWeight: 500 }}>
              Flagged as potentially reportable — confirm against your regulatory
              reporting procedure before triage closes.
            </p>
          )}
        </div>
      )}

      {completeness && (
        <div className="insight">
          <div className="insight-title">
            <span>Completeness check</span>
            <span
              className={`badge ${completeness.score === 100 ? 'badge-green' : 'badge-amber'}`}
            >
              {completeness.score}%
            </span>
          </div>
          {completeness.missing_required.length > 0 ? (
            <>
              <p>Missing: {completeness.missing_required.join(', ')}.</p>
              {completeness.follow_up_questions.length > 0 && (
                <>
                  <p style={{ marginTop: 8, fontWeight: 500 }}>Suggested questions back to the customer:</p>
                  <ul>
                    {completeness.follow_up_questions.map((question) => (
                      <li key={question}>{question}</li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : (
            <p>All required fields captured.</p>
          )}
        </div>
      )}

      {duplicates.length > 0 && (
        <div className="insight">
          <div className="insight-title">
            <span>Possible duplicates</span>
            <span className="badge badge-amber">{duplicates.length}</span>
          </div>
          <ul>
            {duplicates.map((duplicate) => (
              <li key={duplicate.complaint_id}>
                <strong>{duplicate.complaint_number}</strong> —{' '}
                {Math.round(duplicate.similarity * 100)}% match ({duplicate.reason})
              </li>
            ))}
          </ul>
        </div>
      )}

      {recommendations && recommendations.probable_root_causes?.length > 0 && (
        <div className="insight">
          <div className="insight-title">
            <span>Probable root causes</span>
          </div>
          <ul>
            {recommendations.probable_root_causes.map((cause) => (
              <li key={cause}>{cause}</li>
            ))}
          </ul>
        </div>
      )}

      {recommendations && recommendations.investigation_steps?.length > 0 && (
        <div className="insight">
          <div className="insight-title">
            <span>Suggested investigation steps</span>
          </div>
          <ul>
            {recommendations.investigation_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
        </div>
      )}

      {recommendations && recommendations.capa_actions?.length > 0 && (
        <div className="insight">
          <div className="insight-title">
            <span>Draft CAPA actions</span>
          </div>
          <ul>
            {recommendations.capa_actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

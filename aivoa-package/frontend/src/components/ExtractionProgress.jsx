import { useSelector } from 'react-redux'

/**
 * The percentage comes from the LangGraph stream, not a timer — each step
 * advances only when that node has actually finished on the server.
 */
export default function ExtractionProgress() {
  const { isExtracting, progress, progressMessage } = useSelector((state) => state.ai)

  if (!isExtracting && progress === 0) return null

  return (
    <div className="progress-block">
      <div className="progress-head">
        <span>Extraction progress</span>
        <span>{progress}%</span>
      </div>

      <div
        className="progress-track"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Complaint extraction progress"
      >
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      {progressMessage && <p className="progress-message">{progressMessage}</p>}
    </div>
  )
}

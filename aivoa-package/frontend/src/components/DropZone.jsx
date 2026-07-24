import { useRef, useState } from 'react'

const ACCEPT = '.pdf,.docx,.txt,.eml,.md,.csv'

/**
 * File intake. Clicking anywhere in the zone opens the picker, and the whole
 * area is a real <button> so keyboard users get the same affordance as a drop.
 */
export default function DropZone({ onFile, disabled }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = (fileList) => {
    const file = fileList?.[0]
    if (file) onFile(file)
  }

  return (
    <>
      <button
        type="button"
        className={`dropzone${dragging ? ' dragging' : ''}`}
        style={{ width: '100%' }}
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault()
          if (!disabled) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          if (!disabled) handleFiles(event.dataTransfer.files)
        }}
      >
        <div className="dropzone-icon" aria-hidden="true">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        <div className="dropzone-text">
          Drag &amp; drop complaint document here
          <br />
          or <span style={{ color: 'var(--blue)', fontWeight: 500 }}>click to browse</span>
        </div>
      </button>

      <input
        ref={inputRef}
        type="file"
        className="visually-hidden"
        accept={ACCEPT}
        onChange={(event) => {
          handleFiles(event.target.files)
          // Reset so selecting the same file twice still fires onChange.
          event.target.value = ''
        }}
      />
    </>
  )
}

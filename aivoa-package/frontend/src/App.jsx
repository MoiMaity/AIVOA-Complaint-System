import { useEffect } from 'react'
import { useDispatch } from 'react-redux'

import AssistantPanel from './components/AssistantPanel'
import ComplaintForm from './components/ComplaintForm'
import { fetchHealth } from './store/aiSlice'

export default function App() {
  const dispatch = useDispatch()

  useEffect(() => {
    // Tells the UI whether Groq is wired up, so the badge is honest about
    // whether the user is seeing model output or the rule-based fallback.
    dispatch(fetchHealth())
  }, [dispatch])

  return (
    <div className="app">
      <div className="workspace">
        <ComplaintForm />
        <AssistantPanel />
      </div>
    </div>
  )
}

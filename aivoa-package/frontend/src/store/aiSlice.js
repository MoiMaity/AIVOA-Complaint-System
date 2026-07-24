import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'

import { askAssistant, getHealth, streamExtraction } from '../api/client'
import { applyExtraction } from './complaintSlice'

export const fetchHealth = createAsyncThunk('ai/health', getHealth)

export const sendChatMessage = createAsyncThunk(
  'ai/chat',
  async (message, { getState, rejectWithValue }) => {
    const { ai, complaint } = getState()
    try {
      const { reply } = await askAssistant({
        message,
        history: ai.messages.filter((m) => m.role !== 'system').slice(-8),
        form_state: complaint.form,
        source_text: ai.sourceText,
      })
      return reply
    } catch (error) {
      return rejectWithValue(error.message)
    }
  },
)

/**
 * Kicks off extraction and pumps stream events straight into the store, so the
 * form fills in the same moment the agent finishes its extraction node.
 */
export const runExtraction = createAsyncThunk(
  'ai/extract',
  async ({ file, text }, { dispatch, rejectWithValue }) => {
    dispatch(extractionStarted({ fileName: file?.name ?? null }))

    try {
      await streamExtraction({ file, text }, (event) => {
        if (event.type === 'progress') {
          dispatch(progressUpdated(event))
        } else if (event.type === 'error') {
          dispatch(extractionFailed(event.message))
        } else if (event.type === 'result') {
          const values = {}
          const confidences = {}
          for (const [name, payload] of Object.entries(event.result.fields || {})) {
            values[name] = payload.value
            confidences[name] = payload.confidence
          }
          dispatch(applyExtraction(values))
          dispatch(extractionFinished({ ...event.result, confidences }))
        }
      })
      return true
    } catch (error) {
      dispatch(extractionFailed(error.message))
      return rejectWithValue(error.message)
    }
  },
)

const initialState = {
  isExtracting: false,
  progress: 0,
  progressMessage: '',
  error: null,
  sourceDocumentName: null,
  sourceText: null,
  confidences: {},
  insights: {
    completeness: null,
    risk: null,
    duplicates: [],
    recommendations: null,
    summary: null,
    warnings: [],
  },
  messages: [],
  chatPending: false,
  health: null,
}

const aiSlice = createSlice({
  name: 'ai',
  initialState,
  reducers: {
    extractionStarted(state, action) {
      state.isExtracting = true
      state.progress = 0
      state.progressMessage = 'Uploading…'
      state.error = null
      state.sourceDocumentName = action.payload.fileName
      state.insights = initialState.insights
      state.confidences = {}
    },
    progressUpdated(state, action) {
      state.progress = action.payload.percent
      state.progressMessage = action.payload.message
    },
    extractionFinished(state, action) {
      const result = action.payload
      state.isExtracting = false
      state.progress = 100
      state.progressMessage = 'Extraction complete.'
      state.confidences = result.confidences || {}
      state.sourceText = result.raw_text_preview || null
      state.insights = {
        completeness: result.completeness,
        risk: result.risk,
        duplicates: result.duplicates || [],
        recommendations: result.recommendations,
        summary: result.summary,
        warnings: result.warnings || [],
      }
      state.messages.push({
        role: 'assistant',
        content:
          result.summary ||
          'I have populated the form from the document. Please review each field before saving.',
      })
    },
    extractionFailed(state, action) {
      state.isExtracting = false
      state.progress = 0
      state.progressMessage = ''
      state.error = action.payload
    },
    userMessageAdded(state, action) {
      state.messages.push({ role: 'user', content: action.payload })
    },
    clearAi() {
      return { ...initialState }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendChatMessage.pending, (state) => {
        state.chatPending = true
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.chatPending = false
        state.messages.push({ role: 'assistant', content: action.payload })
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.chatPending = false
        state.messages.push({
          role: 'assistant',
          content: `I couldn't answer that: ${action.payload}`,
        })
      })
      .addCase(fetchHealth.fulfilled, (state, action) => {
        state.health = action.payload
      })
  },
})

export const {
  extractionStarted,
  progressUpdated,
  extractionFinished,
  extractionFailed,
  userMessageAdded,
  clearAi,
} = aiSlice.actions

export default aiSlice.reducer

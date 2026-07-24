import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'

import { checkDuplicates, listComplaints, saveComplaint } from '../api/client'
import { EMPTY_FORM } from '../constants'

export const fetchComplaints = createAsyncThunk('complaints/fetch', listComplaints)

export const submitComplaint = createAsyncThunk(
  'complaints/submit',
  async (_, { getState, rejectWithValue }) => {
    const { complaint, ai } = getState()
    try {
      return await saveComplaint(toPayload(complaint.form, ai))
    } catch (error) {
      return rejectWithValue(error.message)
    }
  },
)

export const runDuplicateCheck = createAsyncThunk(
  'complaints/duplicateCheck',
  async (_, { getState, rejectWithValue }) => {
    const { complaint, ai } = getState()
    try {
      return await checkDuplicates(toPayload(complaint.form, ai))
    } catch (error) {
      return rejectWithValue(error.message)
    }
  },
)

/** Convert form strings into the types the API expects. */
function toPayload(form, ai) {
  const numeric = parseFloat(form.quantity_affected)

  return {
    ...form,
    quantity_affected: Number.isFinite(numeric) ? numeric : null,
    // Empty strings would fail date validation server-side.
    manufacturing_date: form.manufacturing_date || null,
    expiry_date: form.expiry_date || null,
    complaint_date: form.complaint_date || null,
    source_document_name: ai.sourceDocumentName || null,
    source_text: ai.sourceText || null,
    ai_metadata: {
      confidences: ai.confidences,
      completeness: ai.insights.completeness,
      risk: ai.insights.risk,
      recommendations: ai.insights.recommendations,
      summary: ai.insights.summary,
      duplicates_at_intake: ai.insights.duplicates,
      warnings: ai.insights.warnings,
    },
  }
}

const initialState = {
  form: { ...EMPTY_FORM },
  // Fields the reviewer has edited by hand — these keep their "verified" style
  // and are never overwritten by a later extraction run.
  touched: {},
  saveStatus: 'idle', // idle | saving | saved | error
  saveError: null,
  saved: null,
  duplicateWarnings: [],
  recent: [],
}

const complaintSlice = createSlice({
  name: 'complaint',
  initialState,
  reducers: {
    setField(state, action) {
      const { name, value } = action.payload
      state.form[name] = value
      state.touched[name] = true
      state.saveStatus = 'idle'
    },
    applyExtraction(state, action) {
      // Only fill fields the reviewer hasn't already typed into.
      for (const [name, value] of Object.entries(action.payload)) {
        if (!state.touched[name] && value != null && value !== '') {
          state.form[name] = String(value)
        }
      }
    },
    resetForm() {
      return { ...initialState, recent: [] }
    },
    dismissDuplicates(state) {
      state.duplicateWarnings = []
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitComplaint.pending, (state) => {
        state.saveStatus = 'saving'
        state.saveError = null
      })
      .addCase(submitComplaint.fulfilled, (state, action) => {
        state.saveStatus = 'saved'
        state.saved = action.payload
        state.duplicateWarnings = []
      })
      .addCase(submitComplaint.rejected, (state, action) => {
        state.saveStatus = 'error'
        state.saveError = action.payload || 'Could not save the complaint.'
      })
      .addCase(runDuplicateCheck.fulfilled, (state, action) => {
        state.duplicateWarnings = action.payload || []
      })
      .addCase(fetchComplaints.fulfilled, (state, action) => {
        state.recent = action.payload || []
      })
  },
})

export const { setField, applyExtraction, resetForm, dismissDuplicates } =
  complaintSlice.actions

export default complaintSlice.reducer

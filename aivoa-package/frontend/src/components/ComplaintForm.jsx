import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'

import {
  COMPLAINT_SOURCES,
  COMPLAINT_TYPES,
  PRIORITIES,
  QUANTITY_UNITS,
  SEVERITIES,
} from '../constants'
import {
  dismissDuplicates,
  fetchComplaints,
  resetForm,
  runDuplicateCheck,
  setField,
  submitComplaint,
} from '../store/complaintSlice'
import { clearAi } from '../store/aiSlice'
import FormField from './FormField'
import RecentComplaints from './RecentComplaints'

const REQUIRED = [
  'customer_name',
  'product_name',
  'batch_lot_number',
  'complaint_type',
  'complaint_description',
  'complaint_date',
]

export default function ComplaintForm() {
  const dispatch = useDispatch()
  const { form, saveStatus, saveError, saved, duplicateWarnings } = useSelector(
    (state) => state.complaint,
  )

  useEffect(() => {
    dispatch(fetchComplaints())
  }, [dispatch])

  const missing = REQUIRED.filter((key) => !form[key])
  const canSave = missing.length === 0 && saveStatus !== 'saving'

  const handleSave = async () => {
    // Duplicate check runs first: logging the same defect twice splits an
    // investigation and skews complaint trending.
    const result = await dispatch(runDuplicateCheck())
    const found = result.payload
    if (Array.isArray(found) && found.length > 0) return

    const outcome = await dispatch(submitComplaint())
    if (submitComplaint.fulfilled.match(outcome)) dispatch(fetchComplaints())
  }

  const handleSaveAnyway = async () => {
    dispatch(dismissDuplicates())
    const outcome = await dispatch(submitComplaint())
    if (submitComplaint.fulfilled.match(outcome)) dispatch(fetchComplaints())
  }

  const handleReset = () => {
    dispatch(resetForm())
    dispatch(clearAi())
    dispatch(fetchComplaints())
  }

  return (
    <section className="panel" aria-labelledby="form-heading">
      <header className="panel-header">
        <div>
          <h1 className="panel-title" id="form-heading">
            Log Customer Complaint
          </h1>
          <p className="panel-subtitle">API &amp; FDF Quality Assurance Module</p>
        </div>
        <span className="badge badge-amber">
          {saved ? saved.complaint_number : 'Pending Triage'}
        </span>
      </header>

      <div className="panel-body">
        <fieldset className="section" style={{ border: 0, margin: 0, padding: 0 }}>
          <legend className="section-label">
            <span>1.</span>
            <span>Origin &amp; Customer Details</span>
          </legend>
          <div className="field-grid">
            <FormField name="complaint_source" type="select" options={COMPLAINT_SOURCES} />
            <FormField name="customer_name" required />
          </div>
        </fieldset>

        <fieldset className="section" style={{ border: 0, margin: 0, padding: 0 }}>
          <legend className="section-label">
            <span>2.</span>
            <span>Product &amp; Batch Identification</span>
          </legend>
          <div className="field-grid">
            <FormField name="product_name" required />
            <FormField name="product_strength" />
            <FormField name="batch_lot_number" required />
            <FormField name="manufacturing_date" type="date" />
            <FormField name="expiry_date" type="date" />
            <FormField name="quantity_affected" type="number">
              <select
                className="unit-select"
                aria-label="Quantity unit"
                value={form.quantity_unit}
                onChange={(event) =>
                  dispatch(setField({ name: 'quantity_unit', value: event.target.value }))
                }
              >
                {QUANTITY_UNITS.map((unit) => (
                  <option key={unit} value={unit}>
                    {unit}
                  </option>
                ))}
              </select>
            </FormField>
          </div>
        </fieldset>

        <fieldset className="section" style={{ border: 0, margin: 0, padding: 0 }}>
          <legend className="section-label">
            <span>3.</span>
            <span>Complaint Details</span>
          </legend>
          <div className="field-grid">
            <FormField name="complaint_type" type="select" options={COMPLAINT_TYPES} required />
            <FormField name="complaint_date" type="date" required />
            <FormField name="complaint_description" type="textarea" full required />
          </div>
        </fieldset>

        <fieldset className="section" style={{ border: 0, margin: 0, padding: 0 }}>
          <legend className="section-label">
            <span>4.</span>
            <span>Initial Assessment &amp; Priority</span>
          </legend>
          <div className="field-grid">
            <FormField name="initial_severity" type="select" options={SEVERITIES} />
            <FormField name="priority" type="select" options={PRIORITIES} />
          </div>
        </fieldset>

        {duplicateWarnings.length > 0 && (
          <div className="hint hint-amber" role="alert">
            <div>
              <strong>Possible duplicate.</strong> This complaint closely matches{' '}
              {duplicateWarnings
                .map((d) => `${d.complaint_number} (${Math.round(d.similarity * 100)}% — ${d.reason})`)
                .join('; ')}
              .{' '}
              <button type="button" className="btn-link" onClick={handleSaveAnyway}>
                Save as a separate complaint
              </button>
            </div>
          </div>
        )}

        {saveStatus === 'saved' && saved && (
          <div className="hint hint-green" role="status">
            <div>
              Complaint <strong>{saved.complaint_number}</strong> saved with status{' '}
              {saved.status}. It is now in the triage queue.
            </div>
          </div>
        )}

        {saveStatus === 'error' && (
          <div className="hint hint-red" role="alert">
            <div>{saveError}</div>
          </div>
        )}

        {missing.length > 0 && (
          <div className="hint hint-blue">
            <div>
              Still needed before saving:{' '}
              {missing.map((key) => key.replaceAll('_', ' ')).join(', ')}.
            </div>
          </div>
        )}

        <div className="form-actions">
          <button type="button" className="btn" onClick={handleReset}>
            Reset form
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSave}
            disabled={!canSave}
          >
            {saveStatus === 'saving' && <span className="spinner" aria-hidden="true" />}
            {saveStatus === 'saving' ? 'Saving…' : 'Save complaint'}
          </button>
        </div>

        <RecentComplaints />
      </div>
    </section>
  )
}

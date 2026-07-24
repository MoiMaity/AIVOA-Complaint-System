import { useDispatch, useSelector } from 'react-redux'

import { FIELD_LABELS } from '../constants'
import { setField } from '../store/complaintSlice'

const DEFAULT_PLACEHOLDER = 'Awaiting AI extraction...'

/**
 * One labelled control. Fields the agent filled are tinted and carry a
 * confidence chip; anything below 60% is flagged amber so the reviewer knows
 * where to look first. Editing a field clears that state — a human value
 * outranks a model value.
 */
export default function FormField({
  name,
  type = 'text',
  options = [],
  placeholder,
  required = false,
  full = false,
  children,
}) {
  const dispatch = useDispatch()
  const value = useSelector((state) => state.complaint.form[name] ?? '')
  const touched = useSelector((state) => Boolean(state.complaint.touched[name]))
  const confidence = useSelector((state) => state.ai.confidences[name])

  const aiFilled = !touched && confidence != null && value !== ''
  const onChange = (event) =>
    dispatch(setField({ name, value: event.target.value }))

  const inputId = `field-${name}`
  const shared = {
    id: inputId,
    name,
    value,
    onChange,
    placeholder: placeholder ?? DEFAULT_PLACEHOLDER,
  }

  return (
    <div className={`field${full ? ' field-full' : ''}${aiFilled ? ' ai-filled' : ''}`}>
      <label className="field-label" htmlFor={inputId}>
        {FIELD_LABELS[name]}
        {required && <span className="required" aria-hidden="true">*</span>}
        {aiFilled && (
          <span
            className={`confidence${confidence < 0.6 ? ' low' : ''}`}
            title="AI confidence in this extracted value"
          >
            AI {Math.round(confidence * 100)}%
          </span>
        )}
      </label>

      <div className="control">
        {type === 'select' && (
          <select {...shared}>
            <option value="">{placeholder ?? 'Awaiting AI extraction...'}</option>
            {options.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        )}

        {type === 'textarea' && <textarea {...shared} rows={4} />}

        {type === 'date' && <input {...shared} type="date" placeholder="" />}

        {type === 'number' && (
          <input {...shared} type="number" step="any" min="0" />
        )}

        {type === 'text' && <input {...shared} type="text" />}

        {children}
      </div>
    </div>
  )
}

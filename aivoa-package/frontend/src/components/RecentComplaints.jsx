import { useSelector } from 'react-redux'

const SEVERITY_CLASS = {
  Critical: 'badge-red',
  Major: 'badge-amber',
  Minor: 'badge-grey',
}

/**
 * Recent records, shown mainly so duplicate detection is demonstrable: log one
 * complaint, then log a similar one and watch the warning fire.
 */
export default function RecentComplaints() {
  const recent = useSelector((state) => state.complaint.recent)

  return (
    <div className="recent">
      <div className="section-label" style={{ marginTop: 20 }}>
        <span>—</span>
        <span>Recently logged complaints</span>
      </div>

      {recent.length === 0 ? (
        <div className="empty">No complaints logged yet.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th scope="col">Number</th>
              <th scope="col">Product</th>
              <th scope="col">Batch</th>
              <th scope="col">Type</th>
              <th scope="col">Severity</th>
            </tr>
          </thead>
          <tbody>
            {recent.slice(0, 6).map((item) => (
              <tr key={item.id}>
                <td style={{ fontWeight: 600, color: '#0f172a' }}>{item.complaint_number}</td>
                <td>{item.product_name || '—'}</td>
                <td>{item.batch_lot_number || '—'}</td>
                <td>{item.complaint_type || '—'}</td>
                <td>
                  {item.initial_severity ? (
                    <span className={`badge ${SEVERITY_CLASS[item.initial_severity] || 'badge-grey'}`}>
                      {item.initial_severity}
                    </span>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

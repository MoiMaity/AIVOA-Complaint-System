// Kept in sync with backend/app/agents/prompts.py — the agent is constrained to
// these same values, so anything it returns always matches a dropdown option.

export const COMPLAINT_SOURCES = [
  'Customer Email',
  'Distributor',
  'Regulatory Authority',
  'Field Sales',
  'Internal QA',
  'Phone Call',
  'Customer Portal',
]

export const COMPLAINT_TYPES = [
  'Physical / Appearance Defect',
  'Contamination / Foreign Matter',
  'Out of Specification (Analytical)',
  'Packaging / Labelling Defect',
  'Documentation / CoA Error',
  'Quantity / Shortage Discrepancy',
  'Transit Damage',
  'Stability / Degradation',
  'Odour / Colour Change',
  'Adverse Event Related',
]

export const SEVERITIES = ['Critical', 'Major', 'Minor']
export const PRIORITIES = ['Urgent', 'High', 'Medium', 'Low']
export const QUANTITY_UNITS = ['kg', 'g', 'L', 'ml', 'vials', 'bottles', 'packs', 'drums']

export const EMPTY_FORM = {
  complaint_source: '',
  customer_name: '',
  product_name: '',
  product_strength: '',
  batch_lot_number: '',
  manufacturing_date: '',
  expiry_date: '',
  quantity_affected: '',
  quantity_unit: 'kg',
  complaint_type: '',
  complaint_date: '',
  complaint_description: '',
  initial_severity: '',
  priority: '',
}

export const FIELD_LABELS = {
  complaint_source: 'Complaint Source',
  customer_name: 'Customer Name',
  product_name: 'Product Name',
  product_strength: 'Product Strength/Grade',
  batch_lot_number: 'Batch/Lot Number',
  manufacturing_date: 'Manufacturing Date',
  expiry_date: 'Expiry Date',
  quantity_affected: 'Quantity Affected',
  quantity_unit: 'Unit',
  complaint_type: 'Complaint Type',
  complaint_date: 'Complaint Date',
  complaint_description: 'Detailed Complaint Description',
  initial_severity: 'Initial Severity',
  priority: 'Priority',
}

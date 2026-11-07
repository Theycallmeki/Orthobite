import { apiClient } from './api'
import type { AxiosResponse } from 'axios'

// ===========================================================================
// Colocated TypeScript Types & Contracts
// ===========================================================================

export type PaymentMethod = 'Cash' | 'GCash' | 'Card'

export interface ToothMetadata {
  id: number // Universal Number (1-32)
  fdi_number: number // FDI Notation (11-48)
  name: string
  arch: 'upper' | 'lower'
  quadrant: string
  type: string // molar, premolar, canine, incisor
  row: number
  col: number
  x: number
  y: number
  width: number
  height: number
}

export interface ToothChartTemplateResponse {
  system: string
  layout: string
  total_teeth: number
  canvas_dimensions: {
    viewBox_width: number
    viewBox_height: number
    cell_width: number
    cell_height: number
    arch_gap: number
    col_gap: number
  }
  upper_arch: ToothMetadata[]
  lower_arch: ToothMetadata[]
  teeth: ToothMetadata[]
}

export interface SignatureUploadResponse {
  url: string
  filename: string
  content_type: string
}

export interface PaymentResponse {
  id: number
  treatment_record_id: number | null
  patient_id: number
  amount: number | string
  payment_date: string
  method: PaymentMethod
  receipt_no: string | null
  notes: string | null
  created_at: string
}

export interface TreatmentRecordResponse {
  id: number
  patient_id: number
  patient_name: string | null
  doctor_id: number | null
  doctor_name: string | null
  date: string
  treatment_name: string
  tooth_number: string | null
  value_of_work: number | string
  total_paid: number | string
  balance: number | string
  signature_url: string | null
  notes: string | null
  created_at: string
  updated_at?: string | null
  payments: PaymentResponse[]
}

export interface PatientLedgerSummary {
  patient_id: number
  patient_name: string
  patient_email: string
  patient_phone: string | null
  treatments: TreatmentRecordResponse[]
  all_payments: PaymentResponse[]
  total_value_of_work: number | string
  total_amount_paid: number | string
  balance_due: number | string
}

export interface TreatmentRecordCreateRequest {
  patient_id: number
  doctor_id?: number
  treatment_name: string
  tooth_number?: string
  value_of_work: number | string
  date?: string
  notes?: string
  signature_url?: string
  signature_base64?: string
}

export interface TreatmentRecordUpdate {
  doctor_id?: number
  date?: string
  treatment_name?: string
  tooth_number?: string
  value_of_work?: number | string
  notes?: string
  signature_url?: string
  signature_base64?: string
}

export interface PaymentCreateRequest {
  patient_id?: number
  treatment_record_id?: number
  amount: number | string
  payment_date?: string
  method: PaymentMethod
  receipt_no?: string
  notes?: string
}

// ===========================================================================
// Patient Records & Financial Ledger API Endpoints
// ===========================================================================

export const recordsApi = {
  /**
   * Universal (1-32) and FDI rectangular layout coordinates for dual-arch tooth chart.
   * Endpoint: GET /records/tooth-chart/template
   */
  getToothChartTemplate(): Promise<AxiosResponse<ToothChartTemplateResponse>> {
    return apiClient.get('/records/tooth-chart/template')
  },

  /**
   * Upload signed treatment sheet or physical signature scan image file.
   * Endpoint: POST /records/signatures/upload
   */
  uploadSignatureFile(file: File): Promise<AxiosResponse<SignatureUploadResponse>> {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/records/signatures/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /**
   * Save patient signature captured directly on the HTML5 Canvas pad as Base64 PNG.
   * Endpoint: POST /records/signatures/base64
   */
  saveSignatureBase64(signatureData: string): Promise<AxiosResponse<SignatureUploadResponse>> {
    return apiClient.post('/records/signatures/base64', {
      signature_data: signatureData,
    })
  },

  /**
   * Create a digital treatment entry in the patient ledger.
   * Staff only.
   * Endpoint: POST /records/
   */
  createTreatmentRecord(payload: TreatmentRecordCreateRequest): Promise<AxiosResponse<TreatmentRecordResponse>> {
    return apiClient.post('/records/', payload)
  },

  /**
   * Retrieve treatment record details including all linked payment installments.
   * Staff or owning patient.
   * Endpoint: GET /records/{recordId}
   */
  getTreatmentRecord(recordId: number): Promise<AxiosResponse<TreatmentRecordResponse>> {
    return apiClient.get(`/records/${recordId}`)
  },

  /**
   * Update clinical observations, tooth numbers, or value of work.
   * Staff only.
   * Endpoint: PATCH /records/{recordId}
   */
  updateTreatmentRecord(
    recordId: number,
    payload: TreatmentRecordUpdate,
  ): Promise<AxiosResponse<TreatmentRecordResponse>> {
    return apiClient.patch(`/records/${recordId}`, payload)
  },

  /**
   * Delete a treatment record entry.
   * Staff only.
   * Endpoint: DELETE /records/{recordId}
   */
  deleteTreatmentRecord(recordId: number): Promise<AxiosResponse<{ message: string }>> {
    return apiClient.delete(`/records/${recordId}`)
  },

  /**
   * Record a downpayment or installment directly against a specific procedure.
   * Staff only.
   * Endpoint: POST /records/{recordId}/payments
   */
  createPaymentForRecord(
    recordId: number,
    payload: PaymentCreateRequest,
  ): Promise<AxiosResponse<PaymentResponse>> {
    return apiClient.post(`/records/${recordId}/payments`, payload)
  },

  /**
   * Record a general payment or advance balance settlement for a patient.
   * Staff only.
   * Endpoint: POST /records/payments
   */
  createGeneralPayment(payload: PaymentCreateRequest): Promise<AxiosResponse<PaymentResponse>> {
    return apiClient.post('/records/payments', payload)
  },

  /**
   * Dynamic zero-drift ledger calculation across all procedures and installment payments.
   * Computes exact total value of work, total amount paid, and net balance due.
   * Endpoint: GET /records/patient/{patientId}/ledger
   */
  getPatientLedger(patientId: number): Promise<AxiosResponse<PatientLedgerSummary>> {
    return apiClient.get(`/records/patient/${patientId}/ledger`)
  },
}

export default recordsApi

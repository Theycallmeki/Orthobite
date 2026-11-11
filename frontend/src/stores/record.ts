import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  recordsApi,
  type ToothChartTemplateResponse,
  type PatientLedgerSummary,
  type TreatmentRecordResponse,
  type TreatmentRecordCreateRequest,
  type TreatmentRecordUpdate,
  type PaymentCreateRequest,
  type PaymentResponse,
  type SignatureUploadResponse,
} from '@/api/record'

function extractError(err: unknown, fallback: string): string {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || fallback
}

export const useRecordStore = defineStore('record', () => {
  const toothTemplate = ref<ToothChartTemplateResponse | null>(null)
  const selectedTeeth = ref<number[]>([])
  const currentPatientLedger = ref<PatientLedgerSummary | null>(null)
  const currentRecord = ref<TreatmentRecordResponse | null>(null)
  const capturedSignatureUrl = ref<string | null>(null)
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)

  const totalValueOfWork = computed<number>(() =>
    Number(currentPatientLedger.value?.total_value_of_work ?? 0),
  )

  const totalPaid = computed<number>(() =>
    Number(currentPatientLedger.value?.total_amount_paid ?? 0),
  )

  const balanceDue = computed<number>(() =>
    Number(currentPatientLedger.value?.balance_due ?? 0),
  )

  const isLedgerSettled = computed<boolean>(() =>
    currentPatientLedger.value !== null && balanceDue.value <= 0,
  )

  const selectedTeethLabels = computed<string[]>(() => {
    const allTeeth = toothTemplate.value?.teeth || []
    return selectedTeeth.value.map((id) => {
      const meta = allTeeth.find((t) => t.id === id)
      return meta ? `#${meta.id} (${meta.fdi_number} - ${meta.name})` : `#${id}`
    })
  })

  const selectedTeethString = computed<string>(() =>
    [...selectedTeeth.value].sort((a, b) => a - b).join(', '),
  )

  function toggleToothSelection(toothId: number): void {
    const idx = selectedTeeth.value.indexOf(toothId)
    if (idx !== -1) {
      selectedTeeth.value.splice(idx, 1)
    } else {
      selectedTeeth.value.push(toothId)
    }
  }

  function clearSelectedTeeth(): void {
    selectedTeeth.value = []
  }

  function clearSignature(): void {
    capturedSignatureUrl.value = null
  }

  async function fetchToothTemplate(): Promise<ToothChartTemplateResponse> {
    if (toothTemplate.value) {
      return toothTemplate.value
    }
    isLoading.value = true
    error.value = null
    try {
      const response = await recordsApi.getToothChartTemplate()
      toothTemplate.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to load tooth chart template')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function uploadSignatureFile(file: File): Promise<SignatureUploadResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await recordsApi.uploadSignatureFile(file)
      capturedSignatureUrl.value = response.data.url
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to upload signature file')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function saveSignatureBase64(signatureData: string): Promise<SignatureUploadResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await recordsApi.saveSignatureBase64(signatureData)
      capturedSignatureUrl.value = response.data.url
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to save signature canvas')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchPatientLedger(patientId: number): Promise<PatientLedgerSummary> {
    isLoading.value = true
    error.value = null
    try {
      const response = await recordsApi.getPatientLedger(patientId)
      currentPatientLedger.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to load patient treatment ledger')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function getTreatmentRecord(recordId: number): Promise<TreatmentRecordResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await recordsApi.getTreatmentRecord(recordId)
      currentRecord.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to fetch treatment record')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createTreatmentRecord(
    payload: TreatmentRecordCreateRequest,
  ): Promise<TreatmentRecordResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await recordsApi.createTreatmentRecord(payload)
      currentRecord.value = response.data
      if (currentPatientLedger.value?.patient_id === payload.patient_id) {
        await fetchPatientLedger(payload.patient_id)
      }
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to create treatment record')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function updateTreatmentRecord(
    recordId: number,
    payload: TreatmentRecordUpdate,
  ): Promise<TreatmentRecordResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await recordsApi.updateTreatmentRecord(recordId, payload)
      currentRecord.value = response.data
      if (currentPatientLedger.value?.patient_id === response.data.patient_id) {
        await fetchPatientLedger(response.data.patient_id)
      }
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to update treatment record')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function deleteTreatmentRecord(recordId: number): Promise<{ message: string }> {
    isLoading.value = true
    error.value = null
    try {
      const targetPatientId =
        currentRecord.value?.id === recordId
          ? currentRecord.value.patient_id
          : currentPatientLedger.value?.treatments.find((t) => t.id === recordId)?.patient_id

      const response = await recordsApi.deleteTreatmentRecord(recordId)
      if (currentRecord.value?.id === recordId) {
        currentRecord.value = null
      }
      if (targetPatientId && currentPatientLedger.value?.patient_id === targetPatientId) {
        await fetchPatientLedger(targetPatientId)
      }
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to delete treatment record')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function addPaymentForRecord(
    recordId: number,
    payload: PaymentCreateRequest,
  ): Promise<PaymentResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await recordsApi.createPaymentForRecord(recordId, payload)
      if (currentPatientLedger.value?.patient_id === response.data.patient_id) {
        await fetchPatientLedger(response.data.patient_id)
      }
      if (currentRecord.value?.id === recordId) {
        await getTreatmentRecord(recordId)
      }
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to record installment payment')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function addGeneralPayment(payload: PaymentCreateRequest): Promise<PaymentResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await recordsApi.createGeneralPayment(payload)
      if (currentPatientLedger.value?.patient_id === response.data.patient_id) {
        await fetchPatientLedger(response.data.patient_id)
      }
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to record general payment')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  return {
    toothTemplate,
    selectedTeeth,
    currentPatientLedger,
    currentRecord,
    capturedSignatureUrl,
    isLoading,
    error,
    totalValueOfWork,
    totalPaid,
    balanceDue,
    isLedgerSettled,
    selectedTeethLabels,
    selectedTeethString,
    toggleToothSelection,
    clearSelectedTeeth,
    clearSignature,
    fetchToothTemplate,
    uploadSignatureFile,
    saveSignatureBase64,
    fetchPatientLedger,
    getTreatmentRecord,
    createTreatmentRecord,
    updateTreatmentRecord,
    deleteTreatmentRecord,
    addPaymentForRecord,
    addGeneralPayment,
  }
})


import { apiClient } from './api'

export interface PatientFile {
  id: number
  patient_id: number
  display_name: string
  description: string | null
  media_type: string
  size_bytes: number
  version: number
  uploaded_by_id: number
  uploaded_by_name: string
  created_at: string
  updated_at: string
}

export interface PatientFileUpdate {
  display_name?: string
  description?: string | null
}

const multipart = { headers: { 'Content-Type': 'multipart/form-data' } }

function filesPath(patientId: number) {
  return `/patients/${patientId}/files`
}

export const patientFilesApi = {
  list(patientId: number, skip: number, limit: number, signal: AbortSignal) {
    return apiClient.get<PatientFile[]>(filesPath(patientId), { params: { skip, limit }, signal })
  },

  upload(patientId: number, file: File, description: string) {
    const form = new FormData()
    form.append('file', file)
    form.append('folder', 'other')
    if (description) form.append('description', description)
    return apiClient.post<PatientFile>(filesPath(patientId), form, multipart)
  },

  getContent(patientId: number, fileId: number, preview: boolean, signal: AbortSignal) {
    return apiClient.get<Blob>(`${filesPath(patientId)}/${fileId}/content`, {
      params: { preview }, responseType: 'blob', signal,
    })
  },

  update(patientId: number, fileId: number, data: PatientFileUpdate) {
    return apiClient.patch<PatientFile>(`${filesPath(patientId)}/${fileId}`, data)
  },

  replace(patientId: number, fileId: number, file: File) {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<PatientFile>(`${filesPath(patientId)}/${fileId}/versions`, form, multipart)
  },

  remove(patientId: number, fileId: number) {
    return apiClient.delete(`${filesPath(patientId)}/${fileId}`)
  },
}

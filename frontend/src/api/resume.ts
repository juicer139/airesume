/** 简历模块 API：类型 + 接口封装 */
import request from './request'

/** 对应后端 schemas.ResumeOut */
export interface ResumeItem {
  id: number
  filename: string
  status: string
  error_message: string | null
  job_description: string | null
  created_at: string
}

/** 创建分析任务的响应 */
export interface ResumeTaskResp {
  record_id: number
  task_id: string
  status: string
}

/** 轮询状态接口的响应 */
export interface ResumeStatusResp {
  record_id: number
  status: string
  error_message: string | null
}

/** 上传简历：FormData（multipart/form-data），可附带岗位 JD */
export function uploadResume(formData: FormData) {
  return request.post<FormData, ResumeItem>('/api/resumes/upload', formData)
}

/** 我的分析记录列表（最新在前） */
export function fetchResumes() {
  return request.get<unknown, ResumeItem[]>('/api/resumes')
}

/** 创建异步分析任务（入队，立即返回） */
export function analyzeResume(recordId: number) {
  return request.post<unknown, ResumeTaskResp>(`/api/resumes/${recordId}/analyze`)
}

/** 轮询任务状态（每 2 秒调一次） */
export function fetchResumeStatus(recordId: number) {
  return request.get<unknown, ResumeStatusResp>(`/api/resumes/${recordId}/status`)
}

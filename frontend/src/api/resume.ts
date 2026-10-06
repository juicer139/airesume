/** 简历模块 API：类型 + 接口封装 */
import request from './request'

/** 对应后端 schemas.ResumeOut */
export interface ResumeItem {
  id: number
  filename: string
  status: string
  job_description: string | null
  created_at: string
}

/** 上传简历：FormData（multipart/form-data），可附带岗位 JD */
export function uploadResume(formData: FormData) {
  return request.post<FormData, ResumeItem>('/api/resumes/upload', formData)
}

/** 我的分析记录列表（最新在前） */
export function fetchResumes() {
  return request.get<unknown, ResumeItem[]>('/api/resumes')
}

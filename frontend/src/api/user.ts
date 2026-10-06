/** 用户模块 API：类型定义 + 接口封装 */
import request from './request'

/** 对应后端 schemas.UserOut */
export interface UserInfo {
  id: number
  username: string
  email: string
  created_at: string
}

/** 对应后端 schemas.Token */
export interface TokenResp {
  access_token: string
  token_type: string
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
}

export interface LoginPayload {
  username: string
  password: string
}

// request 的拦截器已把响应剥成 data，所以用 post<请求体, 响应体> 两个泛型
export function register(payload: RegisterPayload) {
  return request.post<RegisterPayload, UserInfo>('/api/users/register', payload)
}

export function login(payload: LoginPayload) {
  return request.post<LoginPayload, TokenResp>('/api/users/login', payload)
}

export function fetchMe() {
  return request.get<unknown, UserInfo>('/api/users/me')
}

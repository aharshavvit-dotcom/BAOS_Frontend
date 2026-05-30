import apiClient from './client';
import type { AuthTokens, LoginCredentials, SignupData, User } from '@/types';

export interface AuthResponse extends AuthTokens {
  user: User;
}

export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  const res = await apiClient.post<AuthResponse>('/api/auth/login', credentials);
  return res.data;
}

export async function signup(data: SignupData): Promise<AuthResponse> {
  const res = await apiClient.post<AuthResponse>('/api/auth/signup', data);
  return res.data;
}

export async function getCurrentUser(): Promise<User> {
  const res = await apiClient.get<User>('/api/auth/me');
  return res.data;
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/auth/logout');
}

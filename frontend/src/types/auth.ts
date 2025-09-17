// Authentication types
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'hr' | 'recruiter';
  companyId: string;
  isEmailVerified: boolean;
  has2FA: boolean;
  avatar?: string;
  permissions?: string[];
}

export interface LoginRequest {
  email: string;
  password: string;
  tenantSubdomain?: string;
  mfaToken?: string;
  rememberMe?: boolean;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
  requires_mfa?: boolean;
  mfa_methods?: string[];
  userId?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  loading: boolean;
  error: string | null;
  isInitialized: boolean;
}
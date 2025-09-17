import axios, { AxiosResponse } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

interface LoginRequest {
  email: string;
  password: string;
  tenantSubdomain?: string;
  mfaToken?: string;
  rememberMe?: boolean;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: any;
  requires_mfa?: boolean;
  mfa_methods?: string[];
  userId?: string;
}

interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await authApi.refreshToken(refreshToken);
          const newToken = response.access_token;

          // Update stored tokens
          if (localStorage.getItem('auth_token')) {
            localStorage.setItem('auth_token', newToken);
            localStorage.setItem('refresh_token', response.refresh_token);
          } else {
            sessionStorage.setItem('auth_token', newToken);
            sessionStorage.setItem('refresh_token', response.refresh_token);
          }

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
        sessionStorage.removeItem('auth_token');
        sessionStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response: AxiosResponse<LoginResponse> = await apiClient.post('/auth/login', data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },

  refreshToken: async (refreshToken: string): Promise<RefreshTokenResponse> => {
    const response: AxiosResponse<RefreshTokenResponse> = await apiClient.post('/auth/refresh', {
      refresh_token: refreshToken
    });
    return response.data;
  },

  getCurrentUser: async (): Promise<any> => {
    const response: AxiosResponse<any> = await apiClient.get('/auth/me');
    return response.data;
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    await apiClient.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    });
  },

  requestPasswordReset: async (email: string, tenantSubdomain: string): Promise<void> => {
    await apiClient.post('/auth/password-reset', {
      email,
      tenant_subdomain: tenantSubdomain
    });
  },

  confirmPasswordReset: async (token: string, newPassword: string): Promise<void> => {
    await apiClient.post('/auth/password-reset/confirm', {
      token,
      new_password: newPassword
    });
  },

  verifyMFA: async (userId: string, mfaToken: string): Promise<LoginResponse> => {
    const response: AxiosResponse<LoginResponse> = await apiClient.post('/auth/mfa/verify', {
      user_id: userId,
      mfa_token: mfaToken
    });
    return response.data;
  }
};

export default apiClient;
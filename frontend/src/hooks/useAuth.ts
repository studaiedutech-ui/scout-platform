import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from './useRedux';
import { RootState } from '../shared/store/store';
import {
  loginStart,
  loginSuccess,
  loginFailure,
  logout,
  clearError,
  setUser
} from '../shared/store/authSlice';
import { authApi } from '../services/api/authApi';

interface LoginData {
  email: string;
  password: string;
  tenantSubdomain?: string;
  mfaToken?: string;
  rememberMe?: boolean;
}

interface AuthResult {
  user: any;
  access_token: string;
  refresh_token: string;
  expires_in: number;
  requires_mfa?: boolean;
  mfa_methods?: string[];
  userId?: string;
}

export const useAuth = () => {
  const dispatch = useAppDispatch();
  const {
    user,
    isAuthenticated,
    loading,
    error,
    isInitialized
  } = useAppSelector((state: RootState) => state.auth);

  const login = useCallback(async (data: LoginData): Promise<AuthResult> => {
    try {
      dispatch(loginStart());
      
      const response = await authApi.login(data);
      
      if (response.requires_mfa) {
        return {
          user: null,
          access_token: '',
          refresh_token: '',
          expires_in: 0,
          requires_mfa: true,
          mfa_methods: response.mfa_methods,
          userId: response.userId
        };
      }

      dispatch(loginSuccess({
        user: response.user,
        token: response.access_token,
        refreshToken: response.refresh_token
      }));

      // Store tokens in localStorage if rememberMe is true
      if (data.rememberMe) {
        localStorage.setItem('auth_token', response.access_token);
        localStorage.setItem('refresh_token', response.refresh_token);
      } else {
        sessionStorage.setItem('auth_token', response.access_token);
        sessionStorage.setItem('refresh_token', response.refresh_token);
      }

      return response;
    } catch (error: any) {
      dispatch(loginFailure(error.message || 'Login failed'));
      throw error;
    }
  }, [dispatch]);

  const logoutUser = useCallback(async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      dispatch(logout());
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
      sessionStorage.removeItem('auth_token');
      sessionStorage.removeItem('refresh_token');
    }
  }, [dispatch]);

  const initialize = useCallback(async () => {
    try {
      const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
      
      if (!token) {
        dispatch(setUser({ user: null, isInitialized: true }));
        return;
      }

      const user = await authApi.getCurrentUser();
      dispatch(loginSuccess({
        user,
        token,
        refreshToken: localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token') || ''
      }));
      dispatch(setUser({ user, isInitialized: true }));
    } catch (error) {
      console.error('Auth initialization failed:', error);
      // Clear invalid tokens
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
      sessionStorage.removeItem('auth_token');
      sessionStorage.removeItem('refresh_token');
      dispatch(setUser({ user: null, isInitialized: true }));
    }
  }, [dispatch]);

  const refreshToken = useCallback(async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
      
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await authApi.refreshToken(refreshToken);
      
      dispatch(loginSuccess({
        user: user,
        token: response.access_token,
        refreshToken: response.refresh_token
      }));

      // Update stored tokens
      if (localStorage.getItem('auth_token')) {
        localStorage.setItem('auth_token', response.access_token);
        localStorage.setItem('refresh_token', response.refresh_token);
      } else {
        sessionStorage.setItem('auth_token', response.access_token);
        sessionStorage.setItem('refresh_token', response.refresh_token);
      }

      return response.access_token;
    } catch (error) {
      dispatch(logout());
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
      sessionStorage.removeItem('auth_token');
      sessionStorage.removeItem('refresh_token');
      throw error;
    }
  }, [dispatch, user]);

  const clearAuthError = useCallback(() => {
    dispatch(clearError());
  }, [dispatch]);

  return {
    user,
    isAuthenticated,
    loading,
    error,
    isInitialized,
    login,
    logout: logoutUser,
    refreshToken,
    initialize,
    clearError: clearAuthError
  };
};
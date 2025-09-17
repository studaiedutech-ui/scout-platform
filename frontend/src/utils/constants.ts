// Application constants

export const APP_NAME = 'S.C.O.U.T.';
export const APP_VERSION = '1.0.0';

// API Configuration
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
export const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

// Authentication
export const TOKEN_STORAGE_KEY = 'auth_token';
export const REFRESH_TOKEN_STORAGE_KEY = 'refresh_token';

// Routes
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/admin/dashboard',
  CANDIDATES: '/admin/candidates',
  ASSESSMENTS: '/admin/assessments',
  JOBS: '/admin/jobs',
  SETTINGS: '/admin/settings',
  CANDIDATE_WELCOME: '/apply/:companySlug/:jobSlug',
  ASSESSMENT: '/assessment/:sessionId',
  ASSESSMENT_COMPLETE: '/assessment/:sessionId/complete'
} as const;

// User roles
export const USER_ROLES = {
  ADMIN: 'admin',
  HR: 'hr',
  RECRUITER: 'recruiter'
} as const;

// Assessment types
export const ASSESSMENT_TYPES = {
  TECHNICAL: 'technical',
  BEHAVIORAL: 'behavioral',
  MIXED: 'mixed'
} as const;

// Assessment statuses
export const ASSESSMENT_STATUSES = {
  DRAFT: 'draft',
  ACTIVE: 'active',
  ARCHIVED: 'archived'
} as const;

// Candidate statuses
export const CANDIDATE_STATUSES = {
  INVITED: 'invited',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  HIRED: 'hired',
  REJECTED: 'rejected'
} as const;

// File upload
export const ALLOWED_FILE_TYPES = {
  RESUME: ['.pdf', '.doc', '.docx'],
  IMAGE: ['.jpg', '.jpeg', '.png', '.webp'],
  VIDEO: ['.mp4', '.webm', '.mov']
} as const;

export const MAX_FILE_SIZES = {
  RESUME: 5 * 1024 * 1024, // 5MB
  IMAGE: 2 * 1024 * 1024, // 2MB
  VIDEO: 50 * 1024 * 1024 // 50MB
} as const;

// Pagination
export const DEFAULT_PAGE_SIZE = 10;
export const PAGE_SIZE_OPTIONS = [5, 10, 20, 50, 100];

// Timeouts
export const API_TIMEOUT = 30000; // 30 seconds
export const ASSESSMENT_TIMEOUT = 3600000; // 1 hour

// Local storage keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_PREFERENCES: 'user_preferences',
  ASSESSMENT_DRAFT: 'assessment_draft'
} as const;
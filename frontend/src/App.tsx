import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';

// Company (HR) Pages
import CompanyLogin from './company/pages/Login';
import CompanyRegister from './company/pages/Register';
import CompanyOnboarding from './company/pages/Onboarding';
import CompanyDashboard from './company/pages/Dashboard';
import JobPositionView from './company/pages/JobPositionView';
import CreateJobPosition from './company/pages/CreateJobPosition';
import Settings from './company/pages/Settings';

// Candidate Pages
import CandidateWelcome from './candidate/pages/Welcome';
import CandidateApplication from './candidate/pages/Application';
import Assessment from './candidate/pages/Assessment';
import AssessmentComplete from './candidate/pages/AssessmentComplete';

// Shared Components
import LoadingSpinner from './shared/components/LoadingSpinner';
import ErrorBoundary from './shared/components/ErrorBoundary';
import ProtectedRoute from './shared/components/ProtectedRoute';

// Types
import { RootState } from './shared/store/store';

const App: React.FC = () => {
  const { isAuthenticated, loading } = useSelector((state: RootState) => state.auth);

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="App min-h-screen bg-gray-50">
      <ErrorBoundary>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          
          {/* Company Authentication Routes */}
          <Route path="/login" element={<CompanyLogin />} />
          <Route path="/register" element={<CompanyRegister />} />
          
          {/* Company Protected Routes */}
          <Route 
            path="/onboarding" 
            element={
              <ProtectedRoute>
                <CompanyOnboarding />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <CompanyDashboard />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/positions/new" 
            element={
              <ProtectedRoute>
                <CreateJobPosition />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/positions/:jobId" 
            element={
              <ProtectedRoute>
                <JobPositionView />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/settings" 
            element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            } 
          />
          
          {/* Candidate Public Routes */}
          <Route 
            path="/apply/:companySlug/:jobSlug" 
            element={<CandidateWelcome />} 
          />
          <Route 
            path="/apply/:companySlug/:jobSlug/start" 
            element={<CandidateApplication />} 
          />
          <Route 
            path="/assessment/:sessionId" 
            element={<Assessment />} 
          />
          <Route 
            path="/assessment/complete" 
            element={<AssessmentComplete />} 
          />
          
          {/* 404 Route */}
          <Route 
            path="*" 
            element={
              <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                  <h1 className="text-4xl font-bold text-gray-900">404</h1>
                  <p className="text-gray-600 mt-2">Page not found</p>
                  <button 
                    onClick={() => window.history.back()}
                    className="btn-primary mt-4"
                  >
                    Go Back
                  </button>
                </div>
              </div>
            } 
          />
        </Routes>
      </ErrorBoundary>
    </div>
  );
};

export default App;
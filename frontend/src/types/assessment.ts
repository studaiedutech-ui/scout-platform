// Assessment types
export interface Assessment {
  id: string;
  title: string;
  description: string;
  type: 'technical' | 'behavioral' | 'mixed';
  duration: number;
  status: 'draft' | 'active' | 'archived';
  createdAt: string;
  updatedAt: string;
}

export interface AssessmentSession {
  id: string;
  candidateId: string;
  assessmentId: string;
  status: 'pending' | 'in_progress' | 'completed' | 'expired';
  startedAt?: string;
  completedAt?: string;
  score?: number;
  responses: AssessmentResponse[];
}

export interface AssessmentResponse {
  questionId: string;
  response: string;
  score?: number;
  timeSpent: number;
}

export interface Question {
  id: string;
  type: 'multiple_choice' | 'text' | 'code' | 'video';
  question: string;
  options?: string[];
  correctAnswer?: string;
  maxScore: number;
}

// Candidate types
export interface Candidate {
  id: string;
  email: string;
  name: string;
  phone?: string;
  resumeUrl?: string;
  status: 'invited' | 'in_progress' | 'completed' | 'hired' | 'rejected';
  assessmentSessions: AssessmentSession[];
  createdAt: string;
  updatedAt: string;
}

// Job types
export interface Job {
  id: string;
  title: string;
  description: string;
  requirements: string[];
  location: string;
  type: 'full_time' | 'part_time' | 'contract';
  salaryRange: {
    min: number;
    max: number;
    currency: string;
  };
  status: 'draft' | 'active' | 'closed';
  assessmentId?: string;
  createdAt: string;
  updatedAt: string;
}
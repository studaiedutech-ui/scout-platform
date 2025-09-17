import React from 'react';

const CandidateApplication: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900">Application Form</h1>
        <p className="text-gray-600 mt-2">Candidate information and resume upload</p>
      </div>
    </div>
  );
};

export default CandidateApplication;
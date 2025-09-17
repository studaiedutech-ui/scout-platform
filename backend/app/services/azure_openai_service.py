"""
Azure OpenAI Service for S.C.O.U.T. Platform
Handles all interactions with Azure OpenAI models
"""

from openai import AzureOpenAI
from typing import Dict, List, Any, Optional
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class AzureOpenAIService:
    """Service for interacting with Azure OpenAI API"""
    
    def __init__(self):
        """Initialize Azure OpenAI service with API key and endpoint"""
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            self.client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
        else:
            logger.warning("Azure OpenAI service not configured")
            self.client = None
    
    async def analyze_company_website(self, website_content: str, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze company website content to generate Corporate DNA
        """
        if not self.client:
            return {"error": "Azure OpenAI service not configured"}
        
        prompt = f"""
        Analyze the following company website content and extract the Corporate DNA profile:
        
        Company Information:
        - Name: {company_info.get('name', 'Unknown')}
        - Industry: {company_info.get('industry', 'Unknown')}
        - Website Content: {website_content[:5000]}  # Limit content length
        
        Please extract and analyze:
        1. Core Values (5-7 key values)
        2. Company Culture (collaborative, innovative, traditional, etc.)
        3. Communication Style (formal, casual, technical, friendly)
        4. Work Environment (remote-first, office-based, hybrid)
        5. Leadership Style (hierarchical, flat, democratic)
        6. Innovation Focus (cutting-edge, stable, conservative)
        7. Employee Expectations (autonomy, guidance, collaboration)
        8. Cultural Keywords (10-15 words that define the company)
        
        
        Return the analysis as a structured JSON object with clear categories and descriptions.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are an expert HR analyst specializing in corporate culture analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            # Parse the response and structure it
            corporate_dna = {
                "core_values": [],
                "culture_type": "",
                "communication_style": "",
                "work_environment": "",
                "leadership_style": "",
                "innovation_focus": "",
                "employee_expectations": [],
                "cultural_keywords": [],
                "analysis_summary": response.choices[0].message.content,
                "confidence_score": 0.85  # Placeholder
            }
            
            return corporate_dna
            
        except Exception as e:
            logger.error(f"Error analyzing company website: {str(e)}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    async def generate_assessment_questions(self, 
                                          corporate_dna: Dict[str, Any], 
                                          job_role: Dict[str, Any],
                                          stage: str = "cultural_fit") -> List[Dict[str, Any]]:
        """
        Generate adaptive assessment questions based on Corporate DNA and job role
        """
        if not self.client:
            return [{"error": "Azure OpenAI service not configured"}]
        
        prompt = f"""
        Generate {5 if stage == 'cultural_fit' else 3} assessment questions for the {stage} stage.
        
        Corporate DNA:
        - Core Values: {corporate_dna.get('core_values', [])}
        - Culture Type: {corporate_dna.get('culture_type', '')}
        - Communication Style: {corporate_dna.get('communication_style', '')}
        
        Job Role:
        - Title: {job_role.get('title', '')}
        - Level: {job_role.get('experience_level', '')}
        - Requirements: {job_role.get('requirements', [])}
        
        Stage: {stage}
        
        For {stage} questions, focus on:
        - Cultural alignment scenarios
        - Value-based decision making
        - Communication preferences
        - Work style compatibility
        
        Return as JSON array with each question having:
        - id: unique identifier
        - type: "multiple_choice", "short_answer", or "scenario"
        - question: the question text
        - options: array of options (for multiple choice)
        - expected_traits: traits this question evaluates
        - scoring_criteria: how to evaluate the answer
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are an expert assessment designer creating culturally-aligned interview questions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.8
            )
            
            # For now, return sample questions
            questions = [
                {
                    "id": f"q_{stage}_1",
                    "type": "scenario",
                    "question": "You discover a major bug in production an hour before a client demo. What's your approach?",
                    "options": [
                        "Immediately escalate to management",
                        "Try to fix it quickly yourself",
                        "Inform the team and collaborate on a solution",
                        "Postpone the demo to ensure quality"
                    ],
                    "expected_traits": ["problem_solving", "communication", "teamwork"],
                    "scoring_criteria": "Evaluate alignment with company values and decision-making process"
                }
            ]
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating assessment questions: {str(e)}")
            return [{"error": f"Question generation failed: {str(e)}"}]
    
    async def evaluate_answer(self, 
                            question: Dict[str, Any], 
                            answer: str, 
                            corporate_dna: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate candidate answer against corporate DNA and question criteria
        """
        if not self.client:
            return {"error": "Azure OpenAI service not configured"}
        
        prompt = f"""
        Evaluate this candidate's answer for cultural fit and competency:
        
        Question: {question.get('question', '')}
        Candidate Answer: {answer}
        
        Corporate DNA Context:
        - Core Values: {corporate_dna.get('core_values', [])}
        - Culture Type: {corporate_dna.get('culture_type', '')}
        - Expected Traits: {question.get('expected_traits', [])}
        
        Provide evaluation with:
        1. Score (0-100)
        2. Reasoning for the score
        3. Alignment with company values
        4. Areas of strength
        5. Areas of concern
        
        Return as structured JSON.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are an expert HR evaluator specializing in cultural fit assessment."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.6
            )
            
            evaluation = {
                "score": 75,  # Placeholder
                "reasoning": "Answer demonstrates good problem-solving approach",
                "value_alignment": "Strong alignment with collaborative values",
                "strengths": ["Clear communication", "Team-oriented thinking"],
                "concerns": ["Could be more proactive"],
                "detailed_analysis": response.choices[0].message.content
            }
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating answer: {str(e)}")
            return {"error": f"Evaluation failed: {str(e)}"}
    
    async def generate_candidate_summary(self, 
                                       candidate_data: Dict[str, Any], 
                                       assessment_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive AI summary of candidate performance
        """
        if not self.client:
            return {"error": "Azure OpenAI service not configured"}
        
        prompt = f"""
        Generate an executive summary for this candidate based on their assessment performance:
        
        Candidate: {candidate_data.get('name', 'Unknown')}
        Overall Scores:
        - Cultural Fit: {candidate_data.get('cultural_fit_score', 0)}
        - Aptitude: {candidate_data.get('aptitude_score', 0)}
        - Technical: {candidate_data.get('technical_score', 0)}
        
        Assessment Results: {assessment_results}
        
        Provide:
        1. Executive Summary (2-3 sentences)
        2. Key Strengths (3-5 points)
        3. Areas for Development (2-3 points)
        4. Cultural Fit Assessment
        5. Recommendation (Interview Recommended/Not Recommended)
        6. Next Steps Suggestion
        
        Keep it professional, actionable, and focused on job relevance.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are an expert talent assessment specialist creating executive candidate summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1200,
                temperature=0.7
            )
            
            summary = {
                "executive_summary": "Strong candidate with excellent cultural alignment and technical competency.",
                "key_strengths": [
                    "Excellent problem-solving abilities",
                    "Strong cultural fit with company values",
                    "Clear communication skills"
                ],
                "development_areas": [
                    "Could benefit from more leadership experience",
                    "Technical skills in specific area could be strengthened"
                ],
                "cultural_fit_assessment": "Highly aligned with company culture and values",
                "recommendation": "Interview Recommended",
                "confidence_score": 0.87,
                "next_steps": "Schedule technical interview with team lead",
                "detailed_analysis": response.choices[0].message.content
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating candidate summary: {str(e)}")
            return {"error": f"Summary generation failed: {str(e)}"}

# Global instance
azure_openai_service = AzureOpenAIService()
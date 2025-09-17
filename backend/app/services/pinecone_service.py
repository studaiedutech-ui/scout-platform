"""
Pinecone Vector Database Service for S.C.O.U.T. Platform
Handles vector storage and retrieval for Corporate DNA embeddings
"""

import pinecone
from typing import Dict, List, Any, Optional
import numpy as np
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class PineconeService:
    """Service for interacting with Pinecone vector database"""
    
    def __init__(self):
        """Initialize Pinecone service"""
        if settings.PINECONE_API_KEY and settings.PINECONE_ENVIRONMENT:
            try:
                pinecone.init(
                    api_key=settings.PINECONE_API_KEY,
                    environment=settings.PINECONE_ENVIRONMENT
                )
                
                # Create or connect to index
                index_name = settings.PINECONE_INDEX_NAME
                if index_name not in pinecone.list_indexes():
                    pinecone.create_index(
                        name=index_name,
                        dimension=1536,  # OpenAI embeddings dimension
                        metric="cosine"
                    )
                
                self.index = pinecone.Index(index_name)
                logger.info(f"Connected to Pinecone index: {index_name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone: {str(e)}")
                self.index = None
        else:
            logger.warning("Pinecone not configured")
            self.index = None
    
    def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for text using OpenAI or similar service
        For now, returns dummy embeddings
        """
        # TODO: Implement actual embedding generation using OpenAI or similar
        # This is a placeholder that returns random embeddings
        return np.random.rand(1536).tolist()
    
    async def store_corporate_dna(self, 
                                company_id: str, 
                                corporate_dna: Dict[str, Any]) -> bool:
        """
        Store Corporate DNA as vector embeddings in Pinecone
        """
        if not self.index:
            logger.error("Pinecone index not available")
            return False
        
        try:
            # Convert Corporate DNA to text for embedding
            dna_text = self._corporate_dna_to_text(corporate_dna)
            
            # Generate embeddings
            embeddings = self.generate_embeddings(dna_text)
            
            # Store in Pinecone
            vector_id = f"company_{company_id}_dna"
            metadata = {
                "company_id": company_id,
                "type": "corporate_dna",
                "core_values": corporate_dna.get("core_values", []),
                "culture_type": corporate_dna.get("culture_type", ""),
                "communication_style": corporate_dna.get("communication_style", ""),
                "last_updated": str(np.datetime64('now'))
            }
            
            self.index.upsert(
                vectors=[(vector_id, embeddings, metadata)]
            )
            
            logger.info(f"Stored Corporate DNA for company {company_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing Corporate DNA: {str(e)}")
            return False
    
    async def search_similar_companies(self, 
                                     corporate_dna: Dict[str, Any], 
                                     top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find companies with similar Corporate DNA profiles
        """
        if not self.index:
            return []
        
        try:
            # Convert DNA to embeddings
            dna_text = self._corporate_dna_to_text(corporate_dna)
            embeddings = self.generate_embeddings(dna_text)
            
            # Search for similar vectors
            results = self.index.query(
                vector=embeddings,
                top_k=top_k,
                include_metadata=True,
                filter={"type": "corporate_dna"}
            )
            
            similar_companies = []
            for match in results.matches:
                similar_companies.append({
                    "company_id": match.metadata.get("company_id"),
                    "similarity_score": match.score,
                    "culture_type": match.metadata.get("culture_type"),
                    "core_values": match.metadata.get("core_values", [])
                })
            
            return similar_companies
            
        except Exception as e:
            logger.error(f"Error searching similar companies: {str(e)}")
            return []
    
    async def store_candidate_profile(self, 
                                    candidate_id: str, 
                                    assessment_data: Dict[str, Any]) -> bool:
        """
        Store candidate assessment results as vector embeddings
        """
        if not self.index:
            return False
        
        try:
            # Convert assessment data to text for embedding
            profile_text = self._assessment_to_text(assessment_data)
            embeddings = self.generate_embeddings(profile_text)
            
            vector_id = f"candidate_{candidate_id}_profile"
            metadata = {
                "candidate_id": candidate_id,
                "type": "candidate_profile",
                "cultural_fit_score": assessment_data.get("cultural_fit_score", 0),
                "aptitude_score": assessment_data.get("aptitude_score", 0),
                "technical_score": assessment_data.get("technical_score", 0),
                "overall_score": assessment_data.get("overall_score", 0),
                "job_id": assessment_data.get("job_id", ""),
                "assessed_at": str(np.datetime64('now'))
            }
            
            self.index.upsert(
                vectors=[(vector_id, embeddings, metadata)]
            )
            
            logger.info(f"Stored candidate profile for candidate {candidate_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing candidate profile: {str(e)}")
            return False
    
    async def find_similar_candidates(self, 
                                    company_id: str, 
                                    target_profile: Dict[str, Any], 
                                    top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Find candidates with similar profiles for benchmarking
        """
        if not self.index:
            return []
        
        try:
            profile_text = self._assessment_to_text(target_profile)
            embeddings = self.generate_embeddings(profile_text)
            
            results = self.index.query(
                vector=embeddings,
                top_k=top_k,
                include_metadata=True,
                filter={"type": "candidate_profile"}
            )
            
            similar_candidates = []
            for match in results.matches:
                similar_candidates.append({
                    "candidate_id": match.metadata.get("candidate_id"),
                    "similarity_score": match.score,
                    "overall_score": match.metadata.get("overall_score"),
                    "cultural_fit_score": match.metadata.get("cultural_fit_score"),
                    "job_id": match.metadata.get("job_id")
                })
            
            return similar_candidates
            
        except Exception as e:
            logger.error(f"Error finding similar candidates: {str(e)}")
            return []
    
    async def get_company_benchmarks(self, company_id: str) -> Dict[str, Any]:
        """
        Get performance benchmarks for a company based on historical data
        """
        if not self.index:
            return {}
        
        try:
            # Query all candidates for this company
            # Note: This is a simplified approach; in production, you'd want more sophisticated filtering
            results = self.index.query(
                vector=[0.0] * 1536,  # Dummy vector for metadata-only search
                top_k=1000,
                include_metadata=True,
                filter={
                    "type": "candidate_profile",
                    # "company_id": company_id  # Would need to store company_id in candidate metadata
                }
            )
            
            scores = []
            for match in results.matches:
                if match.metadata.get("overall_score"):
                    scores.append(match.metadata["overall_score"])
            
            if not scores:
                return {}
            
            benchmarks = {
                "average_score": np.mean(scores),
                "median_score": np.median(scores),
                "top_quartile": np.percentile(scores, 75),
                "candidate_count": len(scores),
                "score_distribution": {
                    "0-25": len([s for s in scores if s <= 25]),
                    "26-50": len([s for s in scores if 26 <= s <= 50]),
                    "51-75": len([s for s in scores if 51 <= s <= 75]),
                    "76-100": len([s for s in scores if s >= 76])
                }
            }
            
            return benchmarks
            
        except Exception as e:
            logger.error(f"Error getting company benchmarks: {str(e)}")
            return {}
    
    def _corporate_dna_to_text(self, corporate_dna: Dict[str, Any]) -> str:
        """Convert Corporate DNA dictionary to text for embedding"""
        text_parts = []
        
        if corporate_dna.get("core_values"):
            text_parts.append(f"Core values: {', '.join(corporate_dna['core_values'])}")
        
        if corporate_dna.get("culture_type"):
            text_parts.append(f"Culture type: {corporate_dna['culture_type']}")
        
        if corporate_dna.get("communication_style"):
            text_parts.append(f"Communication style: {corporate_dna['communication_style']}")
        
        if corporate_dna.get("work_environment"):
            text_parts.append(f"Work environment: {corporate_dna['work_environment']}")
        
        if corporate_dna.get("cultural_keywords"):
            text_parts.append(f"Keywords: {', '.join(corporate_dna['cultural_keywords'])}")
        
        return " | ".join(text_parts)
    
    def _assessment_to_text(self, assessment_data: Dict[str, Any]) -> str:
        """Convert assessment data to text for embedding"""
        text_parts = []
        
        scores = [
            f"Cultural fit: {assessment_data.get('cultural_fit_score', 0)}",
            f"Aptitude: {assessment_data.get('aptitude_score', 0)}",
            f"Technical: {assessment_data.get('technical_score', 0)}",
            f"Overall: {assessment_data.get('overall_score', 0)}"
        ]
        text_parts.extend(scores)
        
        if assessment_data.get("strengths"):
            text_parts.append(f"Strengths: {', '.join(assessment_data['strengths'])}")
        
        if assessment_data.get("areas_for_development"):
            text_parts.append(f"Development areas: {', '.join(assessment_data['areas_for_development'])}")
        
        return " | ".join(text_parts)

# Global instance
pinecone_service = PineconeService()
"""
Performance and Load Testing for S.C.O.U.T. Platform
Tests covering response times, throughput, and scalability
"""

import pytest
import time
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import requests
import json
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

class PerformanceTestConfig:
    """Configuration for performance tests"""
    BASE_URL = "http://localhost:8000"
    TEST_DURATION = 30  # seconds
    CONCURRENT_USERS = 10
    MAX_RESPONSE_TIME = 2.0  # seconds
    MIN_THROUGHPUT = 50  # requests per second
    
class PerformanceMetrics:
    """Container for performance metrics"""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_time = None
        self.end_time = None
    
    def add_response_time(self, response_time: float, success: bool = True):
        """Add response time measurement"""
        self.response_times.append(response_time)
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate performance statistics"""
        if not self.response_times:
            return {}
        
        duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        total_requests = self.successful_requests + self.failed_requests
        
        return {
            "total_requests": total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / total_requests * 100 if total_requests > 0 else 0,
            "avg_response_time": statistics.mean(self.response_times),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "p95_response_time": self._percentile(self.response_times, 95),
            "p99_response_time": self._percentile(self.response_times, 99),
            "throughput": total_requests / duration if duration > 0 else 0,
            "duration": duration
        }
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of response times"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

@pytest.fixture(scope="session")
def performance_client():
    """Create performance test client"""
    return TestClient(app)

@pytest.fixture
def auth_token(performance_client):
    """Get authentication token for performance tests"""
    with patch('app.api.endpoints.auth.redis_client'), \
         patch('app.api.endpoints.auth.RateLimiter.check_rate_limit') as mock_rate_limit, \
         patch('app.api.endpoints.auth.check_failed_login_attempts') as mock_check_attempts:
        
        mock_rate_limit.return_value = {"allowed": True, "retry_after": 0}
        mock_check_attempts.return_value = True
        
        # Create test user first (this would be in setup)
        login_data = {
            "email": "perf.test@example.com",
            "password": "PerfTest123!"
        }
        
        response = performance_client.post("/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            return response.json()["access_token"]
        return None

class TestResponseTimePerformance:
    """Test response time performance of individual endpoints"""
    
    def test_health_endpoint_response_time(self, performance_client):
        """Test health endpoint response time"""
        metrics = PerformanceMetrics()
        
        for _ in range(100):
            start_time = time.time()
            response = performance_client.get("/api/v1/health")
            end_time = time.time()
            
            response_time = end_time - start_time
            metrics.add_response_time(response_time, response.status_code == 200)
        
        stats = metrics.get_statistics()
        
        # Assertions
        assert stats["avg_response_time"] < 0.1, f"Average response time too high: {stats['avg_response_time']:.3f}s"
        assert stats["p95_response_time"] < 0.2, f"95th percentile response time too high: {stats['p95_response_time']:.3f}s"
        assert stats["success_rate"] >= 99, f"Success rate too low: {stats['success_rate']:.2f}%"
        
        print(f"Health endpoint performance: {stats}")
    
    def test_database_query_response_time(self, performance_client, auth_token):
        """Test database query response time"""
        if not auth_token:
            pytest.skip("Authentication required for this test")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        metrics = PerformanceMetrics()
        
        for _ in range(50):
            start_time = time.time()
            response = performance_client.get("/api/v1/jobs", headers=headers)
            end_time = time.time()
            
            response_time = end_time - start_time
            metrics.add_response_time(response_time, response.status_code == 200)
        
        stats = metrics.get_statistics()
        
        # Assertions for database queries
        assert stats["avg_response_time"] < 0.5, f"Database query response time too high: {stats['avg_response_time']:.3f}s"
        assert stats["p95_response_time"] < 1.0, f"95th percentile response time too high: {stats['p95_response_time']:.3f}s"
        assert stats["success_rate"] >= 95, f"Success rate too low: {stats['success_rate']:.2f}%"
        
        print(f"Database query performance: {stats}")

class TestConcurrencyPerformance:
    """Test performance under concurrent load"""
    
    def test_concurrent_health_checks(self, performance_client):
        """Test health endpoint under concurrent load"""
        metrics = PerformanceMetrics()
        concurrent_users = 20
        requests_per_user = 50
        
        def make_request():
            response_times = []
            for _ in range(requests_per_user):
                start_time = time.time()
                response = performance_client.get("/api/v1/health")
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times.append((response_time, response.status_code == 200))
            return response_times
        
        metrics.start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrent_users)]
            
            for future in as_completed(futures):
                for response_time, success in future.result():
                    metrics.add_response_time(response_time, success)
        
        metrics.end_time = time.time()
        stats = metrics.get_statistics()
        
        # Assertions for concurrent load
        assert stats["avg_response_time"] < 0.5, f"Average response time under load: {stats['avg_response_time']:.3f}s"
        assert stats["success_rate"] >= 95, f"Success rate under load: {stats['success_rate']:.2f}%"
        assert stats["throughput"] >= 100, f"Throughput too low: {stats['throughput']:.1f} req/s"
        
        print(f"Concurrent load performance: {stats}")
    
    def test_authentication_under_load(self, performance_client):
        """Test authentication endpoint under load"""
        metrics = PerformanceMetrics()
        concurrent_users = 10
        
        login_data = {
            "email": "load.test@example.com",
            "password": "LoadTest123!"
        }
        
        def make_auth_request():
            with patch('app.api.endpoints.auth.redis_client'), \
                 patch('app.api.endpoints.auth.RateLimiter.check_rate_limit') as mock_rate_limit, \
                 patch('app.api.endpoints.auth.check_failed_login_attempts') as mock_check_attempts:
                
                mock_rate_limit.return_value = {"allowed": True, "retry_after": 0}
                mock_check_attempts.return_value = True
                
                start_time = time.time()
                response = performance_client.post("/api/v1/auth/login", json=login_data)
                end_time = time.time()
                
                return end_time - start_time, response.status_code in [200, 401]  # 401 is acceptable
        
        metrics.start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_auth_request) for _ in range(100)]
            
            for future in as_completed(futures):
                response_time, success = future.result()
                metrics.add_response_time(response_time, success)
        
        metrics.end_time = time.time()
        stats = metrics.get_statistics()
        
        # Authentication should handle concurrent requests well
        assert stats["avg_response_time"] < 1.0, f"Auth response time too high: {stats['avg_response_time']:.3f}s"
        assert stats["success_rate"] >= 90, f"Auth success rate too low: {stats['success_rate']:.2f}%"
        
        print(f"Authentication load performance: {stats}")

class TestMemoryAndResourceUsage:
    """Test memory and resource usage patterns"""
    
    def test_memory_usage_stability(self, performance_client):
        """Test memory usage remains stable under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make many requests to test for memory leaks
        for i in range(1000):
            response = performance_client.get("/api/v1/health")
            assert response.status_code == 200
            
            # Check memory every 100 requests
            if i % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                
                # Memory growth should be reasonable (less than 50MB per 100 requests)
                assert memory_growth < 50, f"Excessive memory growth: {memory_growth:.1f}MB after {i} requests"
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        print(f"Memory usage - Initial: {initial_memory:.1f}MB, Final: {final_memory:.1f}MB, Growth: {total_growth:.1f}MB")
        
        # Total memory growth should be reasonable
        assert total_growth < 100, f"Total memory growth too high: {total_growth:.1f}MB"

class TestScalabilityPerformance:
    """Test scalability characteristics"""
    
    def test_response_time_vs_load(self, performance_client):
        """Test how response time scales with load"""
        results = {}
        
        for concurrent_users in [1, 5, 10, 20]:
            metrics = PerformanceMetrics()
            requests_per_user = 20
            
            def make_request():
                response_times = []
                for _ in range(requests_per_user):
                    start_time = time.time()
                    response = performance_client.get("/api/v1/health")
                    end_time = time.time()
                    
                    response_time = end_time - start_time
                    response_times.append((response_time, response.status_code == 200))
                return response_times
            
            metrics.start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(make_request) for _ in range(concurrent_users)]
                
                for future in as_completed(futures):
                    for response_time, success in future.result():
                        metrics.add_response_time(response_time, success)
            
            metrics.end_time = time.time()
            stats = metrics.get_statistics()
            results[concurrent_users] = stats
            
            print(f"Load {concurrent_users} users: {stats['avg_response_time']:.3f}s avg, {stats['throughput']:.1f} req/s")
        
        # Response time should scale reasonably
        baseline_response_time = results[1]["avg_response_time"]
        max_load_response_time = results[20]["avg_response_time"]
        
        # Response time shouldn't increase more than 5x under 20x load
        scaling_factor = max_load_response_time / baseline_response_time
        assert scaling_factor < 5.0, f"Poor response time scaling: {scaling_factor:.1f}x increase"

class TestDatabasePerformance:
    """Test database performance characteristics"""
    
    def test_connection_pool_performance(self, performance_client, auth_token):
        """Test database connection pool performance"""
        if not auth_token:
            pytest.skip("Authentication required for this test")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        metrics = PerformanceMetrics()
        concurrent_users = 15  # More than typical connection pool size
        
        def make_db_request():
            response_times = []
            for _ in range(10):
                start_time = time.time()
                response = performance_client.get("/api/v1/jobs", headers=headers)
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times.append((response_time, response.status_code == 200))
            return response_times
        
        metrics.start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_db_request) for _ in range(concurrent_users)]
            
            for future in as_completed(futures):
                for response_time, success in future.result():
                    metrics.add_response_time(response_time, success)
        
        metrics.end_time = time.time()
        stats = metrics.get_statistics()
        
        # Database queries should remain responsive
        assert stats["avg_response_time"] < 1.0, f"DB response time too high: {stats['avg_response_time']:.3f}s"
        assert stats["success_rate"] >= 95, f"DB success rate too low: {stats['success_rate']:.2f}%"
        
        print(f"Database connection pool performance: {stats}")

class TestAPIEndpointPerformance:
    """Test performance of specific API endpoints"""
    
    def test_job_search_performance(self, performance_client, auth_token):
        """Test job search endpoint performance"""
        if not auth_token:
            pytest.skip("Authentication required for this test")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        search_params = {
            "title": "developer",
            "location": "remote",
            "experience_level": "mid"
        }
        
        metrics = PerformanceMetrics()
        
        for _ in range(50):
            start_time = time.time()
            response = performance_client.get("/api/v1/jobs/search", params=search_params, headers=headers)
            end_time = time.time()
            
            response_time = end_time - start_time
            metrics.add_response_time(response_time, response.status_code == 200)
        
        stats = metrics.get_statistics()
        
        # Search queries should be optimized
        assert stats["avg_response_time"] < 0.8, f"Search response time too high: {stats['avg_response_time']:.3f}s"
        assert stats["p95_response_time"] < 1.5, f"95th percentile search time too high: {stats['p95_response_time']:.3f}s"
        
        print(f"Job search performance: {stats}")
    
    @pytest.mark.skip(reason="Requires AI service setup")
    def test_ai_assessment_performance(self, performance_client, auth_token):
        """Test AI assessment endpoint performance"""
        if not auth_token:
            pytest.skip("Authentication required for this test")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        assessment_data = {
            "job_id": 1,
            "candidate_id": 1
        }
        
        metrics = PerformanceMetrics()
        
        for _ in range(10):  # Fewer requests for AI endpoints
            start_time = time.time()
            response = performance_client.post("/api/v1/assessments", json=assessment_data, headers=headers)
            end_time = time.time()
            
            response_time = end_time - start_time
            metrics.add_response_time(response_time, response.status_code in [200, 201])
        
        stats = metrics.get_statistics()
        
        # AI assessments are expected to be slower but should have reasonable limits
        assert stats["avg_response_time"] < 10.0, f"AI response time too high: {stats['avg_response_time']:.3f}s"
        assert stats["success_rate"] >= 80, f"AI success rate too low: {stats['success_rate']:.2f}%"
        
        print(f"AI assessment performance: {stats}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
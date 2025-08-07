#!/usr/bin/env python3
"""
CryptoRebound Ranking API Test Suite
Tests all backend API endpoints comprehensively
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Get backend URL from environment
BACKEND_URL = "https://1311c9fc-c64d-4cbb-b957-118857469742.preview.emergentagent.com/api"

class CryptoReboundTester:
    def __init__(self):
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_result(self, test_name: str, passed: bool, message: str, response_data: Any = None):
        """Log test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
            
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if response_data and not passed:
            result['response_data'] = str(response_data)[:500]  # Limit response data
            
        self.results.append(result)
        print(f"{status} - {test_name}: {message}")
        
    def test_health_check(self):
        """Test GET /api/ endpoint for basic connectivity"""
        try:
            response = requests.get(f"{BACKEND_URL}/", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'message' in data:
                    self.log_result("Health Check", True, f"API is healthy: {data['message']}")
                    return True
                else:
                    self.log_result("Health Check", False, "Invalid response format", data)
                    return False
            else:
                self.log_result("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Health Check", False, f"Connection error: {str(e)}")
            return False
    
    def test_crypto_ranking_basic(self):
        """Test basic crypto ranking endpoint"""
        try:
            response = requests.get(f"{BACKEND_URL}/cryptos/ranking", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    # Check first crypto object structure
                    crypto = data[0]
                    required_fields = ['symbol', 'name', 'price_usd', 'total_score', 'rank']
                    
                    missing_fields = [field for field in required_fields if field not in crypto]
                    if missing_fields:
                        self.log_result("Crypto Ranking Basic", False, f"Missing fields: {missing_fields}", crypto)
                        return False
                    
                    # Check if rankings are ordered correctly
                    scores = [c.get('total_score', 0) for c in data[:5]]
                    if scores != sorted(scores, reverse=True):
                        self.log_result("Crypto Ranking Basic", False, "Rankings not ordered by total_score", scores)
                        return False
                    
                    self.log_result("Crypto Ranking Basic", True, f"Retrieved {len(data)} cryptos, properly ranked")
                    return True
                else:
                    self.log_result("Crypto Ranking Basic", False, "Empty or invalid response", data)
                    return False
            else:
                self.log_result("Crypto Ranking Basic", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Crypto Ranking Basic", False, f"Error: {str(e)}")
            return False
    
    def test_crypto_ranking_parameters(self):
        """Test crypto ranking with different parameters"""
        test_cases = [
            {'period': '1h', 'limit': 10, 'offset': 0},
            {'period': '24h', 'limit': 50, 'offset': 0},
            {'period': '7d', 'limit': 100, 'offset': 10},
            {'period': '30d', 'limit': 25, 'offset': 5}
        ]
        
        all_passed = True
        
        for params in test_cases:
            try:
                response = requests.get(f"{BACKEND_URL}/cryptos/ranking", params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if isinstance(data, list):
                        expected_length = min(params['limit'], 50)  # API might have limits
                        if len(data) <= expected_length:
                            self.log_result(f"Ranking Parameters {params}", True, f"Got {len(data)} results")
                        else:
                            self.log_result(f"Ranking Parameters {params}", False, f"Too many results: {len(data)} > {expected_length}")
                            all_passed = False
                    else:
                        self.log_result(f"Ranking Parameters {params}", False, "Invalid response format", data)
                        all_passed = False
                else:
                    self.log_result(f"Ranking Parameters {params}", False, f"HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_result(f"Ranking Parameters {params}", False, f"Error: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_scoring_algorithms(self):
        """Test that scoring algorithms produce reasonable values"""
        try:
            response = requests.get(f"{BACKEND_URL}/cryptos/ranking?limit=20", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    issues = []
                    
                    for crypto in data:
                        # Check score ranges (0-100)
                        scores_to_check = ['performance_score', 'drawdown_score', 'rebound_potential_score', 'momentum_score', 'total_score']
                        
                        for score_field in scores_to_check:
                            score = crypto.get(score_field)
                            if score is not None:
                                if not (0 <= score <= 100):
                                    issues.append(f"{crypto['symbol']} {score_field}: {score} (out of 0-100 range)")
                        
                        # Check recovery potential format
                        recovery = crypto.get('recovery_potential_75')
                        if recovery and not (recovery.startswith('+') and '%' in recovery):
                            issues.append(f"{crypto['symbol']} recovery_potential_75: {recovery} (invalid format)")
                    
                    if issues:
                        self.log_result("Scoring Algorithms", False, f"Score validation issues: {issues[:3]}")  # Show first 3
                        return False
                    else:
                        self.log_result("Scoring Algorithms", True, f"All scores within valid ranges for {len(data)} cryptos")
                        return True
                else:
                    self.log_result("Scoring Algorithms", False, "No data to validate")
                    return False
            else:
                self.log_result("Scoring Algorithms", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Scoring Algorithms", False, f"Error: {str(e)}")
            return False
    
    def test_multi_period_analysis(self):
        """Test multi-period analysis endpoint"""
        try:
            params = {
                'limit': 15,
                'short_periods': ['24h', '7d'],
                'long_periods': ['30d']
            }
            
            response = requests.get(f"{BACKEND_URL}/cryptos/multi-period-analysis", params=params, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    crypto = data[0]
                    required_fields = ['symbol', 'name', 'average_score', 'period_scores', 'best_period', 'worst_period', 'consistency_score', 'trend_confirmation', 'rank']
                    
                    missing_fields = [field for field in required_fields if field not in crypto]
                    if missing_fields:
                        self.log_result("Multi-Period Analysis", False, f"Missing fields: {missing_fields}", crypto)
                        return False
                    
                    # Check trend confirmation logic
                    valid_trends = ['Strong', 'Accelerating', 'Cooling', 'Divergent', 'Unknown']
                    trend = crypto.get('trend_confirmation')
                    if trend not in valid_trends:
                        self.log_result("Multi-Period Analysis", False, f"Invalid trend confirmation: {trend}")
                        return False
                    
                    self.log_result("Multi-Period Analysis", True, f"Retrieved {len(data)} multi-period cryptos with trend: {trend}")
                    return True
                else:
                    self.log_result("Multi-Period Analysis", False, "Empty or invalid response", data)
                    return False
            else:
                self.log_result("Multi-Period Analysis", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Multi-Period Analysis", False, f"Error: {str(e)}")
            return False
    
    def test_crypto_summary(self):
        """Test crypto summary endpoint"""
        try:
            response = requests.get(f"{BACKEND_URL}/cryptos/summary", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                required_fields = ['total_cryptos', 'periods', 'last_update', 'top_performers', 'market_sentiment']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result("Crypto Summary", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Validate data types and content
                if not isinstance(data['total_cryptos'], int) or data['total_cryptos'] <= 0:
                    self.log_result("Crypto Summary", False, f"Invalid total_cryptos: {data['total_cryptos']}")
                    return False
                
                if not isinstance(data['top_performers'], list) or len(data['top_performers']) == 0:
                    self.log_result("Crypto Summary", False, f"Invalid top_performers: {data['top_performers']}")
                    return False
                
                valid_sentiments = ['Très Positif', 'Positif', 'Neutre', 'Négatif']
                if data['market_sentiment'] not in valid_sentiments:
                    self.log_result("Crypto Summary", False, f"Invalid sentiment: {data['market_sentiment']}")
                    return False
                
                self.log_result("Crypto Summary", True, f"Summary: {data['total_cryptos']} cryptos, sentiment: {data['market_sentiment']}")
                return True
            else:
                self.log_result("Crypto Summary", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Crypto Summary", False, f"Error: {str(e)}")
            return False
    
    def test_performance(self):
        """Test API response times and performance"""
        endpoints = [
            ("/", "Health Check"),
            ("/cryptos/ranking?limit=50", "Ranking 50"),
            ("/cryptos/ranking?limit=100", "Ranking 100"),
            ("/cryptos/multi-period-analysis?limit=15", "Multi-Period"),
            ("/cryptos/summary", "Summary")
        ]
        
        performance_results = []
        all_passed = True
        
        for endpoint, name in endpoints:
            try:
                start_time = time.time()
                response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=30)
                end_time = time.time()
                
                response_time = end_time - start_time
                performance_results.append((name, response_time, response.status_code))
                
                # Consider anything over 10 seconds as slow
                if response_time > 10:
                    self.log_result(f"Performance {name}", False, f"Slow response: {response_time:.2f}s")
                    all_passed = False
                else:
                    self.log_result(f"Performance {name}", True, f"Response time: {response_time:.2f}s")
                    
            except Exception as e:
                self.log_result(f"Performance {name}", False, f"Error: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def run_all_tests(self):
        """Run all tests and return summary"""
        print("🚀 Starting CryptoRebound API Test Suite")
        print(f"Testing backend at: {BACKEND_URL}")
        print("=" * 60)
        
        # Run all tests
        tests = [
            self.test_health_check,
            self.test_crypto_ranking_basic,
            self.test_crypto_ranking_parameters,
            self.test_scoring_algorithms,
            self.test_multi_period_analysis,
            self.test_crypto_summary,
            self.test_performance
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_result(test.__name__, False, f"Test execution error: {str(e)}")
            print("-" * 40)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Success Rate: {(self.passed_tests/self.total_tests)*100:.1f}%")
        
        if self.failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if "❌ FAIL" in result['status']:
                    print(f"  - {result['test']}: {result['message']}")
        
        return {
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'success_rate': (self.passed_tests/self.total_tests)*100,
            'results': self.results
        }

if __name__ == "__main__":
    tester = CryptoReboundTester()
    summary = tester.run_all_tests()
    
    # Save results to file
    with open('/app/test_results_backend.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: /app/test_results_backend.json")
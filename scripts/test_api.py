#!/usr/bin/env python3
"""
API 테스트 스크립트
전체 인수심사 API 시스템을 검증하는 스크립트
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

import httpx


class APITester:
    """API 테스트 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def test_health_check(self) -> Dict[str, Any]:
        """헬스 체크 테스트"""
        print("🏥 헬스 체크 테스트...")
        
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/health")
            result = {
                "success": response.is_success,
                "status_code": response.status_code,
                "data": response.json() if response.is_success else None
            }
            
            if result["success"]:
                print("✅ 헬스 체크 성공")
            else:
                print(f"❌ 헬스 체크 실패: {response.status_code}")
            
            return result
            
        except Exception as e:
            print(f"❌ 헬스 체크 예외: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_webhook_connection(self) -> Dict[str, Any]:
        """Webhook 연결 테스트"""
        print("🔗 Webhook 연결 테스트...")
        
        webhook_config = {
            "url": "https://httpbin.org/post",  # 테스트용 webhook URL
            "headers": {
                "Content-Type": "application/json"
            },
            "auth_header": None,
            "auth_token": None
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/test-webhook",
                json=webhook_config
            )
            
            result = {
                "success": response.is_success,
                "status_code": response.status_code,
                "data": response.json() if response.is_success else None
            }
            
            if result["success"]:
                print("✅ Webhook 연결 테스트 성공")
            else:
                print(f"❌ Webhook 연결 테스트 실패: {response.status_code}")
            
            return result
            
        except Exception as e:
            print(f"❌ Webhook 테스트 예외: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_underwrite_request(self) -> Dict[str, Any]:
        """인수심사 요청 테스트"""
        print("📋 인수심사 요청 테스트...")
        
        # 테스트용 요청 데이터
        request_data = {
            "request_id": f"test_{int(time.time())}",
            "user_input": "태풍으로 인한 농작물 손실에 대한 파라메트릭 보험상품을 설계해주세요. 풍속 40m/s 이상일 때 보험금이 지급되도록 하고, 보장 금액은 1억원으로 설정해주세요.",
            "callback": {
                "type": "webhook",
                "webhook": {
                    "url": "https://httpbin.org/post",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-Test-Header": "API-Test"
                    }
                }
            },
            "options": {
                "simulation_years": 1000,
                "market_risk_premium": 0.15,
                "debug_mode": False,
                "enable_audit_trail": True
            },
            "priority": "normal"
        }
        
        try:
            # 인수심사 요청 제출
            response = await self.client.post(
                f"{self.base_url}/api/v1/underwrite",
                json=request_data
            )
            
            if not response.is_success:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }
            
            task_data = response.json()
            task_id = task_data["task_id"]
            print(f"✅ 인수심사 요청 제출 성공: {task_id}")
            
            # 작업 완료 대기
            print("⏳ 작업 완료 대기...")
            max_wait = 120  # 최대 2분 대기
            wait_time = 0
            
            while wait_time < max_wait:
                # 작업 상태 확인
                status_response = await self.client.get(
                    f"{self.base_url}/api/v1/tasks/{task_id}"
                )
                
                if status_response.is_success:
                    status_data = status_response.json()
                    current_status = status_data["status"]
                    progress = status_data.get("progress", {}).get("percentage", 0)
                    
                    print(f"📊 작업 상태: {current_status}, 진행률: {progress}%")
                    
                    if current_status in ["completed", "failed"]:
                        break
                
                await asyncio.sleep(5)
                wait_time += 5
            
            # 최종 결과 확인
            final_response = await self.client.get(
                f"{self.base_url}/api/v1/tasks/{task_id}"
            )
            
            result = {
                "success": final_response.is_success,
                "task_id": task_id,
                "final_status": None,
                "result": None
            }
            
            if final_response.is_success:
                final_data = final_response.json()
                result["final_status"] = final_data["status"]
                result["result"] = final_data.get("result")
                
                if final_data["status"] == "completed":
                    print("✅ 인수심사 완료!")
                    if result["result"]:
                        print(f"💰 보험료: {result['result'].get('gross_premium', 'N/A')}")
                        print(f"📈 리스크 레벨: {result['result'].get('risk_level', 'N/A')}")
                else:
                    print(f"❌ 인수심사 실패: {final_data.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            print(f"❌ 인수심사 테스트 예외: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_swagger_docs(self) -> Dict[str, Any]:
        """Swagger 문서 접근 테스트"""
        print("📋 Swagger 문서 접근 테스트...")
        
        try:
            # Swagger UI HTML 접근
            ui_response = await self.client.get(f"{self.base_url.replace('/api/v1', '')}/docs-static/swagger-ui.html")
            
            # Swagger YAML 접근
            yaml_response = await self.client.get(f"{self.base_url.replace('/api/v1', '')}/docs-static/swagger.yaml")
            
            result = {
                "success": ui_response.is_success and yaml_response.is_success,
                "ui_status_code": ui_response.status_code,
                "yaml_status_code": yaml_response.status_code
            }
            
            if result["success"]:
                print("✅ Swagger 문서 접근 성공")
                print(f"   - UI 페이지: {ui_response.status_code}")
                print(f"   - YAML 스펙: {yaml_response.status_code}")
            else:
                print(f"❌ Swagger 문서 접근 실패: UI({ui_response.status_code}), YAML({yaml_response.status_code})")
            
            return result
            
        except Exception as e:
            print(f"❌ Swagger 문서 테스트 예외: {str(e)}")
            return {"success": False, "error": str(e)}

    async def test_notification_stats(self) -> Dict[str, Any]:
        """알림 통계 테스트"""
        print("📊 알림 통계 테스트...")
        
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/notifications/stats")
            
            result = {
                "success": response.is_success,
                "status_code": response.status_code,
                "data": response.json() if response.is_success else None
            }
            
            if result["success"]:
                stats = result["data"]["notification_stats"]
                print(f"✅ 알림 통계 조회 성공:")
                print(f"   - 콜백 설정 작업 수: {stats.get('total_tasks_with_callbacks', 0)}")
                print(f"   - 성공한 콜백: {stats.get('callback_success_count', 0)}")
                print(f"   - 실패한 콜백: {stats.get('callback_failed_count', 0)}")
            else:
                print(f"❌ 알림 통계 조회 실패: {response.status_code}")
            
            return result
            
        except Exception as e:
            print(f"❌ 알림 통계 테스트 예외: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """모든 테스트 실행"""
        print("🚀 API 전체 테스트 시작")
        print(f"🎯 대상 URL: {self.base_url}")
        print("=" * 50)
        
        results = {
            "start_time": datetime.utcnow().isoformat(),
            "tests": {}
        }
        
        # 1. 헬스 체크
        results["tests"]["health_check"] = await self.test_health_check()
        
        # 2. Swagger 문서 접근 테스트
        results["tests"]["swagger_docs"] = await self.test_swagger_docs()
        
        # 3. Webhook 연결 테스트
        results["tests"]["webhook_test"] = await self.test_webhook_connection()
        
        # 4. 인수심사 요청 테스트
        results["tests"]["underwrite_request"] = await self.test_underwrite_request()
        
        # 5. 알림 통계 테스트
        results["tests"]["notification_stats"] = await self.test_notification_stats()
        
        results["end_time"] = datetime.utcnow().isoformat()
        
        # 결과 요약
        print("\n" + "=" * 50)
        print("📋 테스트 결과 요약:")
        
        total_tests = len(results["tests"])
        passed_tests = sum(1 for test_result in results["tests"].values() 
                          if test_result.get("success", False))
        
        print(f"✅ 성공: {passed_tests}/{total_tests}")
        print(f"❌ 실패: {total_tests - passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            print("🎉 모든 테스트 통과!")
        else:
            print("⚠️  일부 테스트 실패")
        
        return results
    
    async def close(self):
        """리소스 정리"""
        await self.client.aclose()


async def main():
    """메인 함수"""
    tester = APITester()
    
    try:
        results = await tester.run_all_tests()
        
        # 결과를 JSON 파일로 저장
        with open("api_test_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📄 상세 결과가 api_test_results.json 파일에 저장되었습니다.")
        
    except KeyboardInterrupt:
        print("\n⚠️  테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 예외 발생: {str(e)}")
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
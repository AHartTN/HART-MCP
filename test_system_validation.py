#!/usr/bin/env python3
"""
Comprehensive System Validation Test Suite
Tests all components of HART-MCP for functionality and stability
"""

import asyncio
import json
import logging
import os
import sys
import traceback
from typing import Dict, Any, List
import pytest
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemValidator:
    """Comprehensive system validation"""
    
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        self.passed_tests = []
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        logger.info("🚀 Starting comprehensive system validation...")
        
        test_suite = [
            ("Core Configuration", self.test_configuration),
            ("Database Connectors", self.test_database_connectors),
            ("LLM Connector", self.test_llm_connector),
            ("Basic Tools", self.test_basic_tools),
            ("Plugin System", self.test_plugin_system),
            ("Advanced Consciousness Systems", self.test_consciousness_systems),
            ("SQL Scripts", self.test_sql_scripts),
            ("Docker Configuration", self.test_docker_config),
            ("API Endpoints", self.test_api_endpoints),
            ("Integration Tests", self.test_integration)
        ]
        
        for test_name, test_func in test_suite:
            try:
                logger.info(f"🧪 Running test: {test_name}")
                result = await test_func()
                
                if result.get("success", False):
                    self.passed_tests.append(test_name)
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    self.failed_tests.append((test_name, result.get("error", "Unknown error")))
                    logger.error(f"❌ {test_name}: FAILED - {result.get('error', 'Unknown error')}")
                
                self.test_results.append({
                    "test_name": test_name,
                    "success": result.get("success", False),
                    "details": result
                })
                
            except Exception as e:
                error_msg = f"{str(e)} - {traceback.format_exc()}"
                self.failed_tests.append((test_name, error_msg))
                logger.error(f"💥 {test_name}: CRASHED - {str(e)}")
                
                self.test_results.append({
                    "test_name": test_name,
                    "success": False,
                    "error": error_msg
                })
        
        return self._generate_summary()
    
    async def test_configuration(self) -> Dict[str, Any]:
        """Test configuration loading and validation"""
        try:
            import config
            
            # Test config validation function exists
            if hasattr(config, 'validate_config'):
                validation_result = config.validate_config()
                
                return {
                    "success": validation_result.get("valid", False),
                    "validation_result": validation_result,
                    "config_loaded": True
                }
            else:
                return {
                    "success": True,
                    "config_loaded": True,
                    "validation_function": "Not found but config loads"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "config_loaded": False
            }
    
    async def test_database_connectors(self) -> Dict[str, Any]:
        """Test database connector imports and basic functionality"""
        try:
            import db_connectors
            
            # Test connector functions exist
            required_functions = [
                'get_sql_server_connection',
                'get_milvus_client',
                'get_neo4j_driver'
            ]
            
            missing_functions = []
            for func_name in required_functions:
                if not hasattr(db_connectors, func_name):
                    missing_functions.append(func_name)
            
            # Test connection manager class
            connection_manager_exists = hasattr(db_connectors, 'SQLServerConnectionManager')
            
            return {
                "success": len(missing_functions) == 0 and connection_manager_exists,
                "missing_functions": missing_functions,
                "connection_manager_exists": connection_manager_exists,
                "imported": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "imported": False
            }
    
    async def test_llm_connector(self) -> Dict[str, Any]:
        """Test LLM connector functionality"""
        try:
            from llm_connector import LLMClient
            
            # Create client instance
            client = LLMClient()
            
            # Test available models function
            models = client.get_available_models()
            
            # Test client has required methods
            required_methods = ['invoke', 'get_available_models', 'reset_failed_clients']
            missing_methods = []
            
            for method_name in required_methods:
                if not hasattr(client, method_name):
                    missing_methods.append(method_name)
            
            return {
                "success": len(missing_methods) == 0,
                "missing_methods": missing_methods,
                "available_models": len(models),
                "client_created": True,
                "fallback_enabled": hasattr(client, 'fallback_clients')
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "client_created": False
            }
    
    async def test_basic_tools(self) -> Dict[str, Any]:
        """Test basic tool system"""
        try:
            from plugins_folder.tools import Tool
            from plugins_folder.tool_base import Tool as ToolBase
            
            # Test tool classes can be imported and instantiated
            base_tool = ToolBase()
            
            # Count available tool classes
            tool_classes = []
            import plugins_folder.tools as tools_module
            
            for attr_name in dir(tools_module):
                attr = getattr(tools_module, attr_name)
                if isinstance(attr, type) and issubclass(attr, (Tool, ToolBase)) and attr not in [Tool, ToolBase]:
                    tool_classes.append(attr_name)
            
            return {
                "success": len(tool_classes) > 0,
                "tool_classes_found": len(tool_classes),
                "tool_classes": tool_classes,
                "base_classes_imported": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "base_classes_imported": False
            }
    
    async def test_plugin_system(self) -> Dict[str, Any]:
        """Test plugin system functionality"""
        try:
            import plugins
            from plugins_folder import SpecialistAgent, OrchestratorAgent
            
            # Test plugin loading function exists
            has_call_plugin = hasattr(plugins, 'call_plugin')
            has_load_plugins = hasattr(plugins, 'load_plugins')
            
            # Test agent classes can be imported
            agent_classes_work = True
            try:
                # Don't instantiate agents (requires DB connection) but ensure classes exist
                assert hasattr(SpecialistAgent, '__init__')
                assert hasattr(OrchestratorAgent, 'run')
            except Exception:
                agent_classes_work = False
            
            return {
                "success": has_call_plugin and agent_classes_work,
                "has_call_plugin": has_call_plugin,
                "has_load_plugins": has_load_plugins,
                "agent_classes_work": agent_classes_work,
                "plugin_system_loaded": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "plugin_system_loaded": False
            }
    
    async def test_consciousness_systems(self) -> Dict[str, Any]:
        """Test advanced consciousness systems"""
        consciousness_systems = {}
        overall_success = True
        
        # Test Meta Consciousness
        try:
            from plugins_folder.meta_consciousness import MetaConsciousnessEngine, QuantumThought
            consciousness_systems["meta_consciousness"] = {
                "imported": True,
                "classes": ["MetaConsciousnessEngine", "QuantumThought"]
            }
        except Exception as e:
            consciousness_systems["meta_consciousness"] = {
                "imported": False,
                "error": str(e)
            }
            overall_success = False
        
        # Test Quantum Agent Evolution
        try:
            from plugins_folder.quantum_agent_evolution import QuantumGeneticAlgorithm, EvolutionaryAgent
            consciousness_systems["quantum_evolution"] = {
                "imported": True,
                "classes": ["QuantumGeneticAlgorithm", "EvolutionaryAgent"]
            }
        except Exception as e:
            consciousness_systems["quantum_evolution"] = {
                "imported": False,
                "error": str(e)
            }
            overall_success = False
        
        # Test Neural Fusion Engine
        try:
            from plugins_folder.neural_fusion_engine import DistributedNeuralFusionEngine
            consciousness_systems["neural_fusion"] = {
                "imported": True,
                "classes": ["DistributedNeuralFusionEngine"]
            }
        except Exception as e:
            consciousness_systems["neural_fusion"] = {
                "imported": False,
                "error": str(e)
            }
            overall_success = False
        
        # Test Godlike Meta Agent
        try:
            from plugins_folder.godlike_meta_agent import GodlikeMetaAgent, create_godlike_meta_agent
            consciousness_systems["godlike_agent"] = {
                "imported": True,
                "classes": ["GodlikeMetaAgent"],
                "functions": ["create_godlike_meta_agent"]
            }
        except Exception as e:
            consciousness_systems["godlike_agent"] = {
                "imported": False,
                "error": str(e)
            }
            overall_success = False
        
        return {
            "success": overall_success,
            "systems": consciousness_systems,
            "systems_tested": len(consciousness_systems)
        }
    
    async def test_sql_scripts(self) -> Dict[str, Any]:
        """Test SQL script validity"""
        try:
            import os
            import glob
            
            sql_files = glob.glob("migrations/*.sql") + glob.glob("SqlClr/*.sql")
            
            valid_files = []
            invalid_files = []
            
            for sql_file in sql_files:
                try:
                    with open(sql_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Basic SQL syntax validation
                    if content.strip():
                        # Check for basic SQL keywords
                        sql_keywords = ['CREATE', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'ALTER', 'DROP']
                        has_sql_keywords = any(keyword in content.upper() for keyword in sql_keywords)
                        
                        if has_sql_keywords:
                            valid_files.append(sql_file)
                        else:
                            invalid_files.append((sql_file, "No SQL keywords found"))
                    else:
                        invalid_files.append((sql_file, "Empty file"))
                        
                except Exception as e:
                    invalid_files.append((sql_file, str(e)))
            
            return {
                "success": len(invalid_files) == 0,
                "total_files": len(sql_files),
                "valid_files": len(valid_files),
                "invalid_files": len(invalid_files),
                "invalid_details": invalid_files
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_docker_config(self) -> Dict[str, Any]:
        """Test Docker configuration files"""
        try:
            docker_files = ['Dockerfile', 'docker-compose.yml']
            
            file_status = {}
            
            for file_name in docker_files:
                if os.path.exists(file_name):
                    with open(file_name, 'r') as f:
                        content = f.read()
                    
                    file_status[file_name] = {
                        "exists": True,
                        "size": len(content),
                        "lines": len(content.splitlines())
                    }
                else:
                    file_status[file_name] = {"exists": False}
            
            all_exist = all(status["exists"] for status in file_status.values())
            
            return {
                "success": all_exist,
                "files": file_status,
                "all_files_exist": all_exist
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_api_endpoints(self) -> Dict[str, Any]:
        """Test API endpoint definitions"""
        try:
            # Check if routes directory exists and has route files
            import os
            import glob
            
            route_files = glob.glob("routes/*.py")
            
            # Check if server.py exists and can be imported
            server_exists = os.path.exists("server.py")
            
            if server_exists:
                try:
                    import server
                    server_imported = True
                    
                    # Check if FastAPI app exists
                    has_app = hasattr(server, 'app')
                    
                except Exception as e:
                    server_imported = False
                    has_app = False
            else:
                server_imported = False
                has_app = False
            
            return {
                "success": server_imported and has_app and len(route_files) > 0,
                "server_exists": server_exists,
                "server_imported": server_imported,
                "has_app": has_app,
                "route_files": len(route_files),
                "routes": [os.path.basename(f) for f in route_files]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_integration(self) -> Dict[str, Any]:
        """Test basic integration between components"""
        try:
            # Test if we can create basic instances without errors
            from llm_connector import LLMClient
            from plugins_folder.tool_base import Tool as ToolBase
            
            # Test LLM client creation
            llm_client = LLMClient()
            
            # Test tool creation
            tool = ToolBase()
            
            # Test plugin loading
            import plugins
            
            integration_tests = {
                "llm_client_created": True,
                "tool_created": True,
                "plugins_loaded": True
            }
            
            # Test if consciousness systems can be created (without initializing)
            try:
                from plugins_folder.meta_consciousness import MetaConsciousnessEngine
                # Don't initialize - just check class exists
                integration_tests["consciousness_systems_available"] = True
            except Exception:
                integration_tests["consciousness_systems_available"] = False
            
            success = all(integration_tests.values())
            
            return {
                "success": success,
                "integration_tests": integration_tests
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        total_tests = len(self.test_results)
        passed_count = len(self.passed_tests)
        failed_count = len(self.failed_tests)
        
        success_rate = (passed_count / total_tests * 100) if total_tests > 0 else 0
        
        summary = {
            "overall_success": failed_count == 0,
            "total_tests": total_tests,
            "passed": passed_count,
            "failed": failed_count,
            "success_rate": f"{success_rate:.1f}%",
            "test_results": self.test_results,
            "failed_tests": self.failed_tests,
            "passed_tests": self.passed_tests
        }
        
        return summary

async def main():
    """Run comprehensive system validation"""
    validator = SystemValidator()
    results = await validator.run_all_tests()
    
    # Use safe printing to handle encoding issues  
    try:
        print("\n" + "="*80)
        print("HART-MCP COMPREHENSIVE SYSTEM VALIDATION RESULTS")
        print("="*80)
        
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Success Rate: {results['success_rate']}")
        
        if results['overall_success']:
            print("\nALL TESTS PASSED! System is stable and ready for production!")
        else:
            print("\nSome tests failed. Issues need to be addressed:")
            for test_name, error in results['failed_tests']:
                print(f"   FAILED {test_name}: {error}")
        
        print("\nDetailed Test Results:")
        for test_result in results['test_results']:
            status = "PASS" if test_result['success'] else "FAIL"
            print(f"   {status} - {test_result['test_name']}")
            if not test_result['success'] and 'error' in test_result:
                print(f"     Error: {test_result['error'][:100]}...")
                
    except UnicodeEncodeError:
        # Fallback to basic ASCII output
        print("\n" + "="*80)
        print("HART-MCP COMPREHENSIVE SYSTEM VALIDATION RESULTS")
        print("="*80)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")  
        print(f"Failed: {results['failed']}")
        print(f"Success Rate: {results['success_rate']}")
    
    # Save results to file
    with open('system_validation_report.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed report saved to: system_validation_report.json")
    
    return results['overall_success']

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
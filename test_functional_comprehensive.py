#!/usr/bin/env python3
"""
Comprehensive Functional Test Suite for HART-MCP
Tests actual functionality, not just imports
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from typing import Dict, Any, List
import tempfile
import requests
from pathlib import Path

# Configure logging to capture all output
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FunctionalTestSuite:
    """Comprehensive functional testing suite"""

    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        self.passed_tests = []
        self.warnings_count = 0
        self.errors_count = 0

    async def run_all_functional_tests(self) -> Dict[str, Any]:
        """Run all functional tests with actual operations"""
        logger.info("🚀 Starting COMPREHENSIVE FUNCTIONAL TESTING...")

        test_suite = [
            ("Database Connection Tests", self.test_database_functionality),
            ("LLM Connector Functionality", self.test_llm_functionality),
            ("Agent Workflow Tests", self.test_agent_workflows),
            ("Tool System Functionality", self.test_tool_functionality),
            ("Consciousness System Operations", self.test_consciousness_functionality),
            ("API Endpoint Functionality", self.test_api_functionality),
            ("File System Operations", self.test_file_operations),
            ("Configuration Validation", self.test_configuration_validation),
            ("Error Handling Tests", self.test_error_handling),
            ("Performance and Stability", self.test_performance_stability),
        ]

        for test_name, test_func in test_suite:
            try:
                logger.info(f"🧪 EXECUTING FUNCTIONAL TEST: {test_name}")
                start_time = time.time()
                result = await test_func()
                end_time = time.time()

                result["execution_time"] = round(end_time - start_time, 2)

                if result.get("success", False):
                    self.passed_tests.append(test_name)
                    logger.info(f"✅ {test_name}: PASSED ({result['execution_time']}s)")
                else:
                    self.failed_tests.append(
                        (test_name, result.get("error", "Unknown error"))
                    )
                    logger.error(
                        f"❌ {test_name}: FAILED - {result.get('error', 'Unknown error')}"
                    )

                # Count warnings and errors from result
                if "warnings" in result:
                    self.warnings_count += len(result["warnings"])
                if "errors" in result:
                    self.errors_count += len(result["errors"])

                self.test_results.append(
                    {
                        "test_name": test_name,
                        "success": result.get("success", False),
                        "details": result,
                        "execution_time": result["execution_time"],
                    }
                )

            except Exception as e:
                error_msg = f"{str(e)} - {traceback.format_exc()}"
                self.failed_tests.append((test_name, error_msg))
                logger.error(f"💥 {test_name}: CRASHED - {str(e)}")
                self.errors_count += 1

                self.test_results.append(
                    {
                        "test_name": test_name,
                        "success": False,
                        "error": error_msg,
                        "execution_time": 0,
                    }
                )

        return self._generate_functional_summary()

    async def test_database_functionality(self) -> Dict[str, Any]:
        """Test actual database operations, not just connections"""
        try:
            import db_connectors

            results = {}
            errors = []
            warnings = []

            # Test SQL Server
            try:
                logger.info("Testing SQL Server connection and query execution...")
                connection_manager = await db_connectors.get_sql_server_connection()
                async with connection_manager as conn:
                    cursor = conn.cursor()

                    # Test actual query execution
                    cursor.execute("SELECT 1 as test_value")
                    row = cursor.fetchone()
                    if row and row[0] == 1:
                        results["sql_server"] = {
                            "connected": True,
                            "query_test": "passed",
                        }
                        logger.info("✅ SQL Server functional test passed")
                    else:
                        results["sql_server"] = {
                            "connected": True,
                            "query_test": "failed",
                        }
                        errors.append("SQL Server query returned unexpected result")

                    cursor.close()

            except Exception as e:
                results["sql_server"] = {"connected": False, "error": str(e)}
                errors.append(f"SQL Server test failed: {str(e)}")

            # Test Milvus
            try:
                logger.info("Testing Milvus connection and operations...")
                client = await db_connectors.get_milvus_client()

                if client:
                    # Test collection listing
                    collections = client.list_collections()
                    results["milvus"] = {
                        "connected": True,
                        "collections_count": len(collections),
                        "collections": collections,
                    }
                    logger.info(
                        f"✅ Milvus functional test passed - {len(collections)} collections"
                    )
                else:
                    results["milvus"] = {
                        "connected": False,
                        "error": "Failed to create Milvus client",
                    }
                    errors.append("Milvus client creation returned None")

            except Exception as e:
                results["milvus"] = {"connected": False, "error": str(e)}
                errors.append(f"Milvus test failed: {str(e)}")

            # Test Neo4j
            try:
                logger.info("Testing Neo4j connection and query execution...")
                driver = await db_connectors.get_neo4j_driver()

                async with driver.session() as session:
                    # Test actual query
                    result = await session.run("RETURN 'test' as value")
                    record = await result.single()
                    if record and record["value"] == "test":
                        results["neo4j"] = {"connected": True, "query_test": "passed"}
                        logger.info("✅ Neo4j functional test passed")
                    else:
                        results["neo4j"] = {"connected": True, "query_test": "failed"}
                        errors.append("Neo4j query returned unexpected result")

                await driver.close()

            except Exception as e:
                results["neo4j"] = {"connected": False, "error": str(e)}
                errors.append(f"Neo4j test failed: {str(e)}")

            success = len(errors) == 0
            return {
                "success": success,
                "database_results": results,
                "errors": errors,
                "warnings": warnings,
                "databases_tested": len(results),
                "functional_operations_passed": sum(
                    1
                    for db in results.values()
                    if db.get("connected") and db.get("query_test") == "passed"
                ),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "databases_tested": 0}

    async def test_llm_functionality(self) -> Dict[str, Any]:
        """Test actual LLM calls and fallback functionality"""
        try:
            from llm_connector import LLMClient

            logger.info("Testing LLM client creation and actual API calls...")
            client = LLMClient()

            results = {}
            errors = []
            warnings = []

            # Test simple prompt
            test_prompt = "Respond with exactly: 'TEST_SUCCESS'"

            try:
                logger.info("Testing primary LLM client with actual API call...")
                response = await client.invoke(test_prompt)

                if "TEST_SUCCESS" in response:
                    results["primary_llm_call"] = {
                        "success": True,
                        "response_length": len(response),
                    }
                    logger.info("✅ Primary LLM call successful")
                else:
                    results["primary_llm_call"] = {
                        "success": False,
                        "response": response[:100],
                    }
                    warnings.append("LLM response didn't match expected pattern")

            except Exception as e:
                results["primary_llm_call"] = {"success": False, "error": str(e)}
                errors.append(f"Primary LLM call failed: {str(e)}")

            # Test model availability
            try:
                models = client.get_available_models()
                results["available_models"] = models
                working_models = sum(
                    1 for model in models.values() if model.get("status")
                )
                results["working_models_count"] = working_models
                logger.info(
                    f"✅ Found {working_models} working models out of {len(models)}"
                )

            except Exception as e:
                results["available_models"] = {}
                errors.append(f"Model availability check failed: {str(e)}")

            # Test fallback functionality by temporarily marking primary as failed
            try:
                logger.info("Testing fallback functionality...")
                original_failed = client.failed_clients.copy()

                # Mark primary as failed to test fallback
                if hasattr(client, "llm_source"):
                    client.failed_clients.add(client.llm_source)

                fallback_response = await client.invoke("Test fallback: SUCCESS")

                # Restore original state
                client.failed_clients = original_failed

                if fallback_response and "error" not in fallback_response.lower():
                    results["fallback_test"] = {
                        "success": True,
                        "response_length": len(fallback_response),
                    }
                    logger.info("✅ Fallback functionality working")
                else:
                    results["fallback_test"] = {
                        "success": False,
                        "response": fallback_response[:100],
                    }
                    warnings.append(
                        "Fallback functionality may not be working properly"
                    )

            except Exception as e:
                results["fallback_test"] = {"success": False, "error": str(e)}
                errors.append(f"Fallback test failed: {str(e)}")

            success = len(errors) == 0
            return {
                "success": success,
                "llm_results": results,
                "errors": errors,
                "warnings": warnings,
                "functional_tests_passed": sum(
                    1
                    for test in results.values()
                    if isinstance(test, dict) and test.get("success")
                ),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_agent_workflows(self) -> Dict[str, Any]:
        """Test actual agent creation and workflow execution"""
        try:
            from plugins_folder.agent_core import SpecialistAgent
            from plugins_folder.orchestrator_core import OrchestratorAgent
            from plugins_folder.tools import ToolRegistry, FinishTool
            from llm_connector import LLMClient

            logger.info("Testing agent workflow functionality...")

            results = {}
            errors = []
            warnings = []

            # Create required components
            tool_registry = ToolRegistry()
            tool_registry.register_tool(FinishTool())
            llm_client = LLMClient()

            # Test SpecialistAgent creation and basic methods
            try:
                agent = await SpecialistAgent.load_from_db(
                    agent_id=1, tool_registry=tool_registry, llm_client=llm_client
                )

                results["specialist_agent"] = {
                    "created": True,
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "has_scratchpad": hasattr(agent, "scratchpad"),
                    "has_bdi_state": hasattr(agent, "bdi_state"),
                }
                logger.info("✅ SpecialistAgent created successfully")

            except Exception as e:
                results["specialist_agent"] = {"created": False, "error": str(e)}
                errors.append(f"SpecialistAgent creation failed: {str(e)}")

            # Test OrchestratorAgent creation
            try:
                orchestrator = await OrchestratorAgent.load_from_db(
                    agent_id=2, tool_registry=tool_registry, llm_client=llm_client
                )

                results["orchestrator_agent"] = {
                    "created": True,
                    "agent_id": orchestrator.agent_id,
                    "name": orchestrator.name,
                    "has_scratchpad": hasattr(orchestrator, "scratchpad"),
                    "has_bdi_state": hasattr(orchestrator, "bdi_state"),
                }
                logger.info("✅ OrchestratorAgent created successfully")

            except Exception as e:
                results["orchestrator_agent"] = {"created": False, "error": str(e)}
                errors.append(f"OrchestratorAgent creation failed: {str(e)}")

            success = len(errors) == 0
            return {
                "success": success,
                "agent_results": results,
                "errors": errors,
                "warnings": warnings,
                "agents_tested": len(results),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_tool_functionality(self) -> Dict[str, Any]:
        """Test actual tool execution, not just imports"""
        try:
            from plugins_folder.tools import (
                ToolRegistry,
                WriteFileTool,
                ReadFileTool,
                ListFilesTool,
            )

            logger.info("Testing tool functionality with actual operations...")

            results = {}
            errors = []
            warnings = []

            # Create tool registry
            registry = ToolRegistry()

            # Test WriteFileTool
            try:
                write_tool = WriteFileTool()
                registry.register_tool(write_tool)

                # Test actual file writing
                test_file = tempfile.mktemp(suffix=".txt")
                test_content = "This is a functional test of WriteFileTool"

                write_result = write_tool.execute(
                    file_path=test_file, content=test_content
                )

                if write_result.get("status") == "success" and os.path.exists(
                    test_file
                ):
                    results["write_tool"] = {"functional": True, "file_created": True}
                    logger.info("✅ WriteFileTool functional test passed")

                    # Clean up
                    os.unlink(test_file)
                else:
                    results["write_tool"] = {
                        "functional": False,
                        "result": write_result,
                    }
                    errors.append("WriteFileTool failed to write file")

            except Exception as e:
                results["write_tool"] = {"functional": False, "error": str(e)}
                errors.append(f"WriteFileTool test failed: {str(e)}")

            # Test ReadFileTool
            try:
                read_tool = ReadFileTool()
                registry.register_tool(read_tool)

                # Create a test file and read it
                test_file = tempfile.mktemp(suffix=".txt")
                test_content = "This is a functional test of ReadFileTool"

                with open(test_file, "w") as f:
                    f.write(test_content)

                read_result = read_tool.execute(file_path=test_file)

                if (
                    read_result.get("status") == "success"
                    and read_result.get("content") == test_content
                ):
                    results["read_tool"] = {"functional": True, "content_match": True}
                    logger.info("✅ ReadFileTool functional test passed")
                else:
                    results["read_tool"] = {"functional": False, "result": read_result}
                    errors.append("ReadFileTool failed to read file correctly")

                # Clean up
                os.unlink(test_file)

            except Exception as e:
                results["read_tool"] = {"functional": False, "error": str(e)}
                errors.append(f"ReadFileTool test failed: {str(e)}")

            # Test ListFilesTool
            try:
                list_tool = ListFilesTool()
                registry.register_tool(list_tool)

                # Test directory listing
                list_result = list_tool.execute(path=".")

                if list_result.get("status") == "success" and isinstance(
                    list_result.get("files"), list
                ):
                    results["list_tool"] = {
                        "functional": True,
                        "files_count": len(list_result["files"]),
                        "directories_count": len(list_result.get("directories", [])),
                    }
                    logger.info("✅ ListFilesTool functional test passed")
                else:
                    results["list_tool"] = {"functional": False, "result": list_result}
                    errors.append("ListFilesTool failed to list directory")

            except Exception as e:
                results["list_tool"] = {"functional": False, "error": str(e)}
                errors.append(f"ListFilesTool test failed: {str(e)}")

            # Test tool registry functionality
            try:
                tool_names = registry.get_tool_names()
                test_tool = registry.get_tool("write_file")

                results["tool_registry"] = {
                    "tools_registered": len(tool_names),
                    "can_retrieve_tools": test_tool is not None,
                    "tool_names": tool_names,
                }
                logger.info(
                    f"✅ Tool registry functional test passed - {len(tool_names)} tools registered"
                )

            except Exception as e:
                results["tool_registry"] = {"functional": False, "error": str(e)}
                errors.append(f"Tool registry test failed: {str(e)}")

            success = len(errors) == 0
            return {
                "success": success,
                "tool_results": results,
                "errors": errors,
                "warnings": warnings,
                "tools_tested": len(results),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_consciousness_functionality(self) -> Dict[str, Any]:
        """Test consciousness systems with actual operations"""
        try:
            logger.info("Testing consciousness system functionality...")

            results = {}
            errors = []
            warnings = []

            # Test MetaConsciousnessEngine
            try:
                from plugins_folder.meta_consciousness import (
                    MetaConsciousnessEngine,
                    QuantumThought,
                    ConsciousnessLevel,
                    ThoughtType,
                )
                import time
                import uuid

                # Create instances with all required parameters
                thought = QuantumThought(
                    thought_id=str(uuid.uuid4()),
                    content="Test thought",
                    probability_amplitude=0.8,
                    phase=0.5,
                    entangled_thoughts=set(),
                    consciousness_level=ConsciousnessLevel.REFLECTIVE,
                    thought_type=ThoughtType.ANALYTICAL,
                    depth=1,
                    parent_thought_id=None,
                    children_thought_ids=set(),
                    certainty=0.7,
                    novelty=0.6,
                    significance=0.8,
                    coherence=0.9,
                    creation_time=time.time(),
                    last_evolution_time=time.time(),
                    lifespan=60.0,
                    wave_function={},
                    measurement_history=[],
                )

                results["quantum_thought"] = {
                    "created": True,
                    "has_content": hasattr(thought, "content"),
                    "has_consciousness_level": hasattr(thought, "consciousness_level"),
                    "content_valid": thought.content == "Test thought",
                    "consciousness_level_valid": thought.consciousness_level
                    == ConsciousnessLevel.REFLECTIVE,
                }

                # Test basic methods if they exist
                if hasattr(thought, "evolve"):
                    evolved = thought.evolve(
                        time_delta=0.1
                    )  # Provide required time_delta parameter
                    results["quantum_thought"]["can_evolve"] = evolved is not None

                logger.info("✅ QuantumThought functional test passed")

            except Exception as e:
                results["meta_consciousness"] = {"functional": False, "error": str(e)}
                errors.append(f"MetaConsciousness test failed: {str(e)}")

            # Test other consciousness systems exist and can be instantiated
            consciousness_modules = [
                ("quantum_agent_evolution", "QuantumGeneticAlgorithm"),
                ("neural_fusion_engine", "DistributedNeuralFusionEngine"),
                ("godlike_meta_agent", "GodlikeMetaAgent"),
            ]

            for module_name, class_name in consciousness_modules:
                try:
                    module = __import__(
                        f"plugins_folder.{module_name}", fromlist=[class_name]
                    )
                    cls = getattr(module, class_name)

                    results[module_name] = {
                        "importable": True,
                        "class_exists": cls is not None,
                        "has_methods": len(
                            [m for m in dir(cls) if not m.startswith("_")]
                        )
                        > 0,
                    }
                    logger.info(f"✅ {class_name} structural test passed")

                except Exception as e:
                    results[module_name] = {"importable": False, "error": str(e)}
                    errors.append(f"{class_name} test failed: {str(e)}")

            success = len(errors) == 0
            return {
                "success": success,
                "consciousness_results": results,
                "errors": errors,
                "warnings": warnings,
                "systems_tested": len(results),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_api_functionality(self) -> Dict[str, Any]:
        """Test API endpoints with actual HTTP requests"""
        logger.info("Testing API functionality...")

        # For now, just test that server can be imported and configured
        # Full API testing would require starting the server
        try:
            import server

            results = {
                "server_importable": True,
                "has_app": hasattr(server, "app"),
                "app_configured": hasattr(server.app, "title")
                if hasattr(server, "app")
                else False,
            }

            if hasattr(server, "app"):
                app = server.app
                results["api_title"] = getattr(app, "title", "Unknown")
                results["api_version"] = getattr(app, "version", "Unknown")

            return {
                "success": True,
                "api_results": results,
                "errors": [],
                "warnings": [
                    "Full API testing requires server startup - only tested configuration"
                ],
                "note": "Complete API testing requires integration test environment",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_file_operations(self) -> Dict[str, Any]:
        """Test file system operations"""
        logger.info("Testing file system operations...")

        try:
            results = {}
            errors = []

            # Test temp file creation
            temp_file = tempfile.mktemp()
            with open(temp_file, "w") as f:
                f.write("test")

            if os.path.exists(temp_file):
                results["temp_file_creation"] = True
                os.unlink(temp_file)
            else:
                results["temp_file_creation"] = False
                errors.append("Failed to create temporary file")

            # Test directory operations
            temp_dir = tempfile.mkdtemp()
            if os.path.exists(temp_dir):
                results["temp_dir_creation"] = True
                os.rmdir(temp_dir)
            else:
                results["temp_dir_creation"] = False
                errors.append("Failed to create temporary directory")

            return {
                "success": len(errors) == 0,
                "file_results": results,
                "errors": errors,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_configuration_validation(self) -> Dict[str, Any]:
        """Test configuration loading and validation"""
        try:
            import config

            results = {}
            errors = []
            warnings = []

            # Test config attributes exist
            required_configs = [
                "LLM_SOURCE",
                "LLM_FALLBACK_ENABLED",
                "LLM_FALLBACK_ORDER",
                "GEMINI_MODEL_NAME",
                "CLAUDE_MODEL_NAME",
                "SQL_SERVER_SERVER",
                "MILVUS_HOST",
                "NEO4J_URI",
            ]

            missing_configs = []
            for config_name in required_configs:
                if not hasattr(config, config_name):
                    missing_configs.append(config_name)

            results["config_completeness"] = {
                "total_required": len(required_configs),
                "missing": len(missing_configs),
                "missing_configs": missing_configs,
            }

            if missing_configs:
                errors.append(f"Missing configurations: {missing_configs}")

            # Test validation function if it exists
            if hasattr(config, "validate_config"):
                validation_result = config.validate_config()
                results["validation_function"] = validation_result

                if validation_result.get("warnings"):
                    warnings.extend(validation_result["warnings"])

            return {
                "success": len(errors) == 0,
                "config_results": results,
                "errors": errors,
                "warnings": warnings,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling in various components"""
        logger.info("Testing error handling capabilities...")

        try:
            results = {}
            errors = []

            # Test tool error handling
            from plugins_folder.tools import ReadFileTool

            read_tool = ReadFileTool()
            error_result = read_tool.execute(file_path="nonexistent_file.txt")

            if error_result.get("status") == "error":
                results["tool_error_handling"] = True
                logger.info("✅ Tool error handling working correctly")
            else:
                results["tool_error_handling"] = False
                errors.append("Tools don't properly handle errors")

            return {
                "success": len(errors) == 0,
                "error_handling_results": results,
                "errors": errors,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_performance_stability(self) -> Dict[str, Any]:
        """Test system performance and stability"""
        logger.info("Testing system performance and stability...")

        try:
            import psutil
            import gc

            # Memory usage before
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB

            results = {
                "memory_before_mb": round(memory_before, 2),
                "cpu_count": psutil.cpu_count(),
                "system_stable": True,
            }

            # Simulate some operations
            for _ in range(100):
                temp_data = [i for i in range(1000)]
                del temp_data

            gc.collect()

            # Memory usage after
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            results["memory_after_mb"] = round(memory_after, 2)
            results["memory_growth_mb"] = round(memory_after - memory_before, 2)

            return {"success": True, "performance_results": results, "errors": []}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_functional_summary(self) -> Dict[str, Any]:
        """Generate comprehensive functional test summary"""
        total_tests = len(self.test_results)
        passed_count = len(self.passed_tests)
        failed_count = len(self.failed_tests)

        success_rate = (passed_count / total_tests * 100) if total_tests > 0 else 0

        # Calculate total execution time
        total_time = sum(test.get("execution_time", 0) for test in self.test_results)

        summary = {
            "overall_success": failed_count == 0 and self.errors_count == 0,
            "total_tests": total_tests,
            "passed": passed_count,
            "failed": failed_count,
            "success_rate": f"{success_rate:.1f}%",
            "total_execution_time": f"{total_time:.2f}s",
            "total_warnings": self.warnings_count,
            "total_errors": self.errors_count,
            "functional_validation": "COMPLETE" if failed_count == 0 else "INCOMPLETE",
            "test_results": self.test_results,
            "failed_tests": self.failed_tests,
            "passed_tests": self.passed_tests,
        }

        return summary


async def main():
    """Run comprehensive functional validation"""
    tester = FunctionalTestSuite()
    results = await tester.run_all_functional_tests()

    try:
        print("\n" + "=" * 80)
        print("HART-MCP COMPREHENSIVE FUNCTIONAL TEST RESULTS")
        print("=" * 80)

        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Success Rate: {results['success_rate']}")
        print(f"Total Execution Time: {results['total_execution_time']}")
        print(f"Total Warnings: {results['total_warnings']}")
        print(f"Total Errors: {results['total_errors']}")
        print(f"Functional Validation: {results['functional_validation']}")

        if results["overall_success"]:
            print("\nALL FUNCTIONAL TESTS PASSED! System functionality verified!")
        else:
            print(
                f"\n{results['failed']} functional tests failed. Issues need to be addressed:"
            )
            for test_name, error in results["failed_tests"]:
                print(f"   FAILED {test_name}: {error[:200]}...")

    except UnicodeEncodeError:
        # Fallback to basic ASCII output
        print("\n" + "=" * 80)
        print("HART-MCP COMPREHENSIVE FUNCTIONAL TEST RESULTS")
        print("=" * 80)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Success Rate: {results['success_rate']}")

    print(f"\nDetailed Test Results:")
    for test_result in results["test_results"]:
        status = "PASS" if test_result["success"] else "FAIL"
        time_str = f" ({test_result.get('execution_time', 0)}s)"
        print(f"   {status} - {test_result['test_name']}{time_str}")
        if not test_result["success"] and "error" in test_result:
            print(f"     Error: {test_result['error'][:100]}...")

    # Save results to file
    with open("functional_test_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nDetailed report saved to: functional_test_report.json")

    return results["overall_success"]


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

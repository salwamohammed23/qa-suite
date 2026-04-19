import docker
import tempfile
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class DockerTestExecutor:
    """Executes test code in isolated Docker containers"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.images = {
            "python": "qa-runner-python:latest",
            "javascript": "qa-runner-js:latest",
            "java": "qa-runner-java:latest",
            "csharp": "qa-runner-csharp:latest"
        }
    
    def execute_test(self, language: str, code: str, test_code: Optional[str] = None) -> Dict[str, Any]:
        """Execute test code in appropriate Docker container"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Create appropriate file structure
            if language == "python":
                tmp_path.joinpath("test_code.py").write_text(code)
                if test_code:
                    tmp_path.joinpath("test_assertions.py").write_text(test_code)
                cmd = ["pytest", "test_code.py", "-v", "--tb=short"]
                
            elif language == "javascript":
                tmp_path.joinpath("test.test.js").write_text(code)
                pkg = {
                    "name": "test-runner",
                    "version": "1.0.0",
                    "scripts": {"test": "jest"},
                    "devDependencies": {"jest": "^29.0.0"}
                }
                tmp_path.joinpath("package.json").write_text(json.dumps(pkg))
                cmd = ["npm", "test", "--", "test.test.js"]
                
            elif language == "java":
                tmp_path.joinpath("TestRunner.java").write_text(code)
                cmd = ["javac", "TestRunner.java", "&&", "java", "TestRunner"]
                
            elif language == "csharp":
                tmp_path.joinpath("Test.cs").write_text(code)
                tmp_path.joinpath("TestProject.csproj").write_text("""
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
    <PackageReference Include="NUnit" Version="4.0.1" />
    <PackageReference Include="NUnit3TestAdapter" Version="4.5.0" />
  </ItemGroup>
</Project>
""")
                cmd = ["dotnet", "test"]
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported language: {language}",
                    "stdout": "",
                    "stderr": ""
                }
            
            try:
                # Run container
                container = self.client.containers.run(
                    image=self.images[language],
                    command=cmd,
                    volumes={str(tmp_path): {"bind": "/workspace", "mode": "rw"}},
                    working_dir="/workspace",
                    remove=True,
                    detach=False,
                    timeout=60
                )
                
                # Parse output
                output = container.decode('utf-8') if isinstance(container, bytes) else str(container)
                
                return {
                    "success": True,
                    "stdout": output,
                    "stderr": "",
                    "error": None
                }
                
            except docker.errors.ContainerError as e:
                return {
                    "success": False,
                    "stdout": e.stdout.decode('utf-8') if e.stdout else "",
                    "stderr": e.stderr.decode('utf-8') if e.stderr else "",
                    "error": str(e)
                }
            except Exception as e:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "error": str(e)
                }
    
    def execute_healing_test(self, language: str, original_code: str, healed_code: str) -> Dict[str, Any]:
        """Execute both original and healed test for comparison"""
        
        original_result = self.execute_test(language, original_code)
        healed_result = self.execute_test(language, healed_code)
        
        return {
            "original": original_result,
            "healed": healed_result,
            "healing_successful": healed_result["success"] and not original_result["success"]
        }

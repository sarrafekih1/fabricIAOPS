"""Pydantic models for agent and system specifications."""
from pydantic import BaseModel
from typing import List, Optional, Any, Dict


class ToolSpec(BaseModel):
    """Specification for a tool used by an agent."""
    name: str
    type: str
    source: Optional[str] = None
    endpoint: Optional[str] = None


class ModelSpec(BaseModel):
    """Specification for the LLM used by an agent."""
    provider: str
    name: str
    temperature: float
    max_tokens: Optional[int] = None


class MemorySpec(BaseModel):
    """Specification for the memory configuration of an agent."""
    type: str
    k: int


class PromptSpec(BaseModel):
    """Specification for system and user prompts."""
    system: str
    user: str


class AgentSpec(BaseModel):
    """Specification for an individual agent."""
    id: str
    role: str
    model: ModelSpec
    memory: MemorySpec
    tools: List[ToolSpec]
    prompt: PromptSpec


class SystemSpec(BaseModel):
    """Overall system specification containing multiple agents."""
    version: str
    metadata: Dict[str, Any]
    agents: List[AgentSpec]
    guardrails: Dict[str, Any]


class PythonBestPractices(BaseModel):
    """Best practices for Python development in the project."""
    style: str
    docstrings: str
    error_handling: str
    typing: str


class TestingBestPractices(BaseModel):
    """Best practices for testing in the project."""
    framework: str
    coverage: str


class BestPracticesSpec(BaseModel):
    """Overall best practices specification."""
    python: PythonBestPractices
    security: List[str]
    testing: TestingBestPractices

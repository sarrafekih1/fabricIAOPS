import json
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class FeatureSpec:
    feature_id: str
    title: str
    user_story: str
    acceptance_criteria: List[str]
    edge_cases: List[str]
    tech_constraints: List[str]

class JSONSpecParser:
    """Parses JSON feature specifications for the agentic workflow."""
    
    @staticmethod
    def parse(file_path: str) -> FeatureSpec:
        """Reads a JSON spec file and returns a validated FeatureSpec object."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Simple validation of required fields
            required_fields = ["feature_id", "title", "user_story", "acceptance_criteria"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field in spec: {field}")
            
            return FeatureSpec(
                feature_id=data.get("feature_id", "UNKNOWN"),
                title=data.get("title", "Untitled Feature"),
                user_story=data.get("user_story", ""),
                acceptance_criteria=data.get("acceptance_criteria", []),
                edge_cases=data.get("edge_cases", []),
                tech_constraints=data.get("tech_constraints", [])
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {file_path}: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing spec file {file_path}: {str(e)}")

    @staticmethod
    def to_prompt_context(spec: FeatureSpec) -> str:
        """Converts the spec object into a text format suitable for the LLM prompt."""
        return f"""
--- FEATURE SPECIFICATION ({spec.feature_id}) ---
Title: {spec.title}
User Story: {spec.user_story}

Acceptance Criteria:
{chr(10).join(['- ' + ac for ac in spec.acceptance_criteria])}

Technical Constraints:
{chr(10).join(['- ' + tc for tc in spec.tech_constraints])}

Edge Cases:
{chr(10).join(['- ' + ec for ec in spec.edge_cases])}
------------------------------------------------
"""

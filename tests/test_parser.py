from parser.spec_parser import load_spec
from parser.models import SystemSpec


def test_load_spec() -> None:
    spec: SystemSpec = load_spec("specs/multi_agent.yaml")
    assert spec.version == "2.0"
    assert len(spec.agents) == 2
    assert spec.agents[0].id == "anomaly_detector"
    assert spec.agents[1].model.provider == "gemini"

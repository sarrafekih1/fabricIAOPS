"""Parsers for system specifications and best practices YAML files."""
import yaml
from parser.models import SystemSpec, BestPracticesSpec


def load_spec(path: str) -> SystemSpec:
    """Loads and validates a system specification from a YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        The validated SystemSpec object.
    """
    # 1️⃣ Lecture YAML
    with open(path, "r") as f:
        raw_yaml = f.read()
    print("\n========== 1️⃣ YAML brut ==========")
    print(raw_yaml)

    # 2️⃣ YAML → dict Python
    data = yaml.safe_load(raw_yaml)
    print("\n========== 2️⃣ YAML → dict Python ==========")
    print(data)
    print("Type :", type(data))

    # 3️⃣ Validation Pydantic
    try:
        spec = SystemSpec(**data)
        print("\n✅ YAML valide selon le contrat Pydantic")
    except Exception as e:
        print("\n❌ Erreur de validation :", e)
        raise e

    # 4️⃣ Objet final
    print("\n========== 3️⃣ Objet Pydantic final ==========")
    print(spec)
    print("Type :", type(spec))

    return spec


if __name__ == "__main__":
    spec = load_spec("specs/multi_agent.yaml")
    print("\n========== Infos des agents ==========")
    for agent in spec.agents:
        print(f"Agent ID: {agent.id}, Role: {agent.role}, Model: {agent.model.name}")


def load_best_practices(path: str) -> BestPracticesSpec:
    """Loads and validates a best practices specification from a YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        The validated BestPracticesSpec object.
    """
    with open(path, "r") as f:
        raw_yaml = f.read()

    data = yaml.safe_load(raw_yaml)

    try:
        spec = BestPracticesSpec(**data)
        print("\n✅ Best Practices YAML valide")
    except Exception as e:
        print("\n❌ Erreur Best Practices :", e)
        raise e

    return spec   
def enforce_best_practices(best_practices):
    import subprocess
    
    # Python style
    if best_practices.python.style == "PEP 8":
        subprocess.run(["flake8", "."])
    if best_practices.python.typing == "Strict type hints required":
        subprocess.run(["mypy", ".", "--strict"])
    if best_practices.python.docstrings == "Google Style":
        subprocess.run(["pydocstyle", ".", "--convention=google"])
    # Testing coverage
    if best_practices.testing.coverage.startswith("Minimum"):
        min_cov = int(best_practices.testing.coverage.split()[1])
        subprocess.run(["pytest", "--cov=.", f"--cov-fail-under={min_cov}"])

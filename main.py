from parser.spec_parser import load_spec, load_best_practices
from api.agent_endpoints import app


import uvicorn

if __name__ == "__main__":
    spec = load_spec("specs/multi_agent.yaml")
    best_practices = load_best_practices("specs/best_practices.yaml")
    # Appliquer automatiquement : marche pas
    # enforce_best_practices(best_practices)

    print("Agents chargés :")
    for agent in spec.agents:
        print(f"- {agent.id} ({agent.role})")
        print("\nBest Practices chargées :")
        print(best_practices)
    # Lancer FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8000)

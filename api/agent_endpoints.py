"""Endpoints for the Agentic AI Platform API."""
from dotenv import load_dotenv
import os
import json
from fastapi import FastAPI, HTTPException
from parser.spec_parser import load_spec
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from typing import Callable, Any, Optional
import httpx
from kubernetes import client, config
from pydantic import SecretStr
from parser.models import AgentSpec


load_dotenv()  # charge .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
app = FastAPI(title="Agentic AI Platform - Phase 2")

# Charger les specs YAML
spec = load_spec("specs/multi_agent.yaml")


@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {
        "message": "Welcome to Agentic AI Platform API",
        "version": "2.0",
        "endpoints": {
            "root": "/",
            "k8s_metrics": "/k8s/metrics",
            "agents": [f"/agents/{agent.id}/query" for agent in spec.agents],
        },
    }


# --- Endpoint pour les métriques réelles de la machine ---
# @app.get("/local/metrics")
# async def get_local_metrics():
#     """Returns real-time CPU, RAM, and Disk metrics from the host machine."""
#     return {
#         "cpu": {
#             "usage_percent": psutil.cpu_percent(interval=None),
#             "count": psutil.cpu_count(),
#             "load_avg": (
#                 psutil.getloadavg() if hasattr(psutil, "getloadavg") else "N/A"
#             )
#         },
#         "memory": {
#             "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
#             "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
#             "usage_percent": psutil.virtual_memory().percent
#         },
#         "disk": {
#             "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
#             "used_gb": round(psutil.disk_usage('/').used / (1024**3), 2),
#             "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
#             "usage_percent": psutil.disk_usage('/').percent
#         }
#     }


# --- Endpoint pour les métriques Kubernetes locales (Minikube) ---
@app.get("/k8s/metrics")
async def get_k8s_metrics():
    """Fetches real node and pod metrics from the local Kubernetes cluster."""
    try:
        # Charge la config locale Minikube
        config.load_kube_config()

        # API pour les Custom Objects (metrics-server)
        api = client.CustomObjectsApi()
        # Récupérer les métriques des noeuds
        node_metrics = api.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes"
        )        
        # Récupérer les métriques des pods
        pod_metrics = api.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="pods"
        )
        # Récupérer les infos détaillées des pods (status, restarts, etc.)
        v1 = client.CoreV1Api()
        all_pods = v1.list_pod_for_all_namespaces()
        pods_info = []
        for pod in all_pods.items:
            pod_status = pod.status.phase
            container_statuses = pod.status.container_statuses
            restarts = (
                sum(cs.restart_count for cs in container_statuses)
                if container_statuses
                else 0
            )
            pods_info.append(
                {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod_status,
                    "restarts": restarts,
                    "node": pod.spec.node_name,
                }
            )

        return {
            "status": "success",
            "cluster_type": "minikube/local",
            "nodes": node_metrics.get("items", []),
            "pods_metrics": pod_metrics.get("items", []),
            "pods_info": pods_info
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erreur de connexion au cluster local : {str(e)}",
            "hint": "Vérifiez que Minikube est démarré (minikube start)"
        }


# Créer dynamiquement un endpoint pour chaque agent
def create_handler(agent_spec: AgentSpec) -> Callable[[str], Any]:

    """Creates a request handler for a specific agent specification.

    Args:
        agent_spec: The specification of the agent.

    Returns:
        A function to handle queries for the agent.
    """
    async def handle_query(query: str, spec_id: Optional[str] = None) -> dict[str, Any]:
        """Executes the agent's prompt via LangChain and Gemini."""
        try:
            # 1️⃣ Créer LLM LangChain selon le provider
            if agent_spec.model.provider.lower() == "gemini":
                llm = ChatGoogleGenerativeAI(
                    model=agent_spec.model.name,
                    temperature=agent_spec.model.temperature,
                    max_output_tokens=agent_spec.model.max_tokens,
                    google_api_key=GEMINI_API_KEY,
                )
            else:
                raise HTTPException(status_code=400, detail="Provider non supporté")

            # 2️⃣ Récupérer le contexte (Outils + Docs + Specs)
            context_parts = []

            # Gestion des Specs JSON (Nouveau)
            if spec_id:
                try:
                    from parser.json_parser import JSONSpecParser

                    # On suppose que les specs sont dans specs/{spec_id}.json
                    spec_path = f"specs/{spec_id}.json"
                    spec_json = JSONSpecParser.parse(spec_path)
                    spec_context = JSONSpecParser.to_prompt_context(spec_json)
                    context_parts.append(spec_context)
                    # On ajuste la question pour inclure l'instruction d'implémentation
                    query = (
                        f"Implement the feature defined in the "
                        f"attached specification ({spec_json.title}).\n{query}"
                    )
                except Exception as e:
                    context_parts.append(f"⚠️ Error loading spec {spec_id}: {str(e)}")

            for tool in agent_spec.tools:
                if tool.type == "retriever":
                    embeddings = GoogleGenerativeAIEmbeddings(
                        model="models/gemini-embedding-001",
                        api_key=SecretStr(GEMINI_API_KEY) if GEMINI_API_KEY else None,
                    )
                    vectordb = Chroma(
                        persist_directory="./vectorstore/chroma_db",
                        embedding_function=embeddings,
                    )
                    docs = vectordb.similarity_search(query, k=3)
                    retriever_context = "\n".join([d.page_content for d in docs])
                    context_parts.append(
                        f"--- Documentation ({tool.name}) ---\n{retriever_context}"
                    )

                elif tool.type == "api" and tool.endpoint:
                    try:
                        async with httpx.AsyncClient() as client:
                            # Note: kubectl proxy permet l'accès sans auth sur
                            # localhost:8001
                            response = await client.get(tool.endpoint, timeout=10.0)
                            response.raise_for_status()
                            api_data = response.text
                            context_parts.append(
                                f"--- Données API ({tool.name}) ---\n{api_data}"
                            )
                    except Exception as e:
                        context_parts.append(
                            f"--- Erreur API ({tool.name}) ---\n"
                            f"Impossible de récupérer les données : {str(e)}"
                        )

            context = "\n\n".join(context_parts)

            # Échapper les accolades dans le prompt système pour éviter que LangChain ne
            # les prenne pour des variables
            # (Surtout maintenant qu'on a du JSON dans le prompt)
            prompt_text = agent_spec.prompt.system.replace("{", "{{").replace("}", "}}")
            if context:
                # Échapper les accolades pour éviter les erreurs de variable LangChain
                # si le contexte contient du JSON
                safe_context = context.replace("{", "{{").replace("}", "}}")
                prompt_text += f"\n\nContexte récupéré :\n{safe_context}"

            prompt = ChatPromptTemplate.from_template(
                f"{prompt_text}\nUser: {{question}}"
            )

            chain = prompt | llm

            # 3️⃣ Exécuter
            result = chain.invoke({"question": query})
            raw_response = result.content

            # 4️⃣ Parser JSON
            # Nettoyer d'éventuels backticks markdown ou texte superflu
            clean_response = raw_response.strip()
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[
                    0
                ].strip()
            elif "```" in clean_response:
                clean_response = clean_response.split("```")[1].split("```")[0].strip()

            try:
                parsed_response = json.loads(clean_response)
            except json.JSONDecodeError:
                parsed_response = {
                    "raw_response": raw_response,
                    "error": "Failed to parse JSON",
                }

            return {
                "agent_id": agent_spec.id,
                "query": query,
                "response": parsed_response,
            }

        except Exception as e:
            import traceback
            print(f"Error in handle_query for agent {agent_spec.id}:")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    return handle_query


for agent in spec.agents:
    route = f"/agents/{agent.id}/query"
    handler = create_handler(agent)
    app.get(route)(handler)

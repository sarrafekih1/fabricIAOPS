"""Endpoints for the Agentic AI Platform API."""
from dotenv import load_dotenv
import os
import json
from fastapi import FastAPI, HTTPException
from parser.spec_parser import load_spec
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from typing import Callable, Any
from pydantic import SecretStr
from parser.models import AgentSpec


load_dotenv()  # charge .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
app = FastAPI(title="Agentic AI Platform - Phase 2")

# Charger les specs YAML
spec = load_spec("specs/multi_agent.yaml")


# Créer dynamiquement un endpoint pour chaque agent
def create_handler(agent_spec: AgentSpec) -> Callable[[str], Any]:
    """Creates a request handler for a specific agent specification.

    Args:
        agent_spec: The specification of the agent.

    Returns:
        A function to handle queries for the agent.
    """
    async def handle_query(query: str) -> dict[str, Any]:
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

            # 2️⃣ Gérer la récupération (RAG) si nécessaire
            context = ""
            for tool in agent_spec.tools:
                if tool.type == "retriever":
                    # Charger le vectorstore
                    embeddings = GoogleGenerativeAIEmbeddings(
                        model="models/gemini-embedding-001",
                        api_key=SecretStr(GEMINI_API_KEY) if GEMINI_API_KEY else None,
                    )
                    vectordb = Chroma(
                        persist_directory="./vectorstore/chroma_db",
                        embedding_function=embeddings,
                    )

                    # Chercher les documents pertinents
                    docs = vectordb.similarity_search(query, k=3)
                    context = "\n".join([d.page_content for d in docs])
                    break

            # 3️⃣ Construire le prompt avec contexte
            prompt_text = agent_spec.prompt.system
            if context:
                prompt_text += f"\n\nContexte récupéré :\n{context}"

            prompt = ChatPromptTemplate.from_template(
                f"{prompt_text}\nUser: {{question}}"
            )

            chain = prompt | llm

            # 4️⃣ Exécuter
            result = chain.invoke({"question": query})
            raw_response = result.content

            # 4️⃣ Nettoyer et parser la string JSON imbriquée
            try:
                # Supprimer les ```json si présents
                if not isinstance(raw_response, str):
                    raw_response = str(raw_response)
                clean_response = (
                    raw_response.replace("```json", "").replace("```", "").strip()
                )

                # Parser la première couche
                parsed_response = json.loads(clean_response)

                # Si c'est encore une string JSON imbriquée, parser à nouveau
                if isinstance(parsed_response, str):
                    parsed_response = json.loads(parsed_response)

            except json.JSONDecodeError:
                # si ce n’est toujours pas du JSON, renvoyer la string brute
                parsed_response = {"raw_response": raw_response}

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

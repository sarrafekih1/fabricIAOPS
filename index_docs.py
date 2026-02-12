from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from pydantic import SecretStr
import os

# 0️⃣ Charger les variables d'environnement (.env)
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ Erreur : GEMINI_API_KEY non trouvée dans le fichier .env")
    exit(1)

# 1️⃣ Chemin vers tes docs
docs_path = "./vectorstore/docs"

# 2️⃣ Lire tous les fichiers
documents = []
for fname in os.listdir(docs_path):
    if fname.endswith(".txt") or fname.endswith(".md"):
        with open(os.path.join(docs_path, fname), "r", encoding="utf-8") as f:
            text = f.read()
            documents.append(text)

if not documents:
    print(f"⚠️ Aucun document trouvé dans {docs_path}")
    exit(0)

# 3️⃣ Découper en morceaux pour les embeddings
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
docs_chunks = []
for doc in documents:
    docs_chunks.extend(text_splitter.split_text(doc))

print(f"📄 {len(docs_chunks)} fragments créés.")

# 4️⃣ Créer les embeddings Gemini
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001", api_key=SecretStr(GEMINI_API_KEY)
)

# 5️⃣ Indexer dans Chroma
print("⏳ Indexation dans Chroma...")
vectordb = Chroma.from_texts(
    texts=docs_chunks, embedding=embeddings, persist_directory="./vectorstore/chroma_db"
)

# Note: In langchain-chroma, persistence is often automatic or handled differently
# than the old .persist() call, but the directory is set.

print("✅ Vector store créé et indexé dans ./vectorstore/chroma_db !")

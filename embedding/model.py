"""
Embedding modeli için TEK doğruluk kaynağı. İndeksleme, API ve test scriptleri
aynı modeli/aynı önekleri kullanmak zorunda; biri değişip diğeri değişmezse
arama sessizce bozulur.
"""
from langchain_huggingface import HuggingFaceEmbeddings

# Retrieval için eğitilmiş çok dilli model (Türkçe destekli).
# Daha iyi ama yavaş seçenek: "intfloat/multilingual-e5-base"
MODEL_NAME = "intfloat/multilingual-e5-small"


def load_embeddings():
    return HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def embed_query(embeddings, text: str):
    # E5 modelleri sorguların başına "query: " bekler
    return embeddings.embed_query("query: " + text)


def embed_passages(embeddings, texts):
    # ... ve doküman parçalarının başına "passage: "
    return embeddings.embed_documents(["passage: " + t for t in texts])
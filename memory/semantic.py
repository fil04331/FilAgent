"""
Mémoire sémantique pour recherche de connaissances à long terme
Utilise FAISS pour l'indexation vectorielle et sentence-transformers pour les embeddings
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: FAISS not installed. Semantic memory will not work.")

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Semantic memory will not work.")


class SemanticMemory:
    """
    Mémoire sémantique avec indexation vectorielle FAISS
    Permet de rechercher des connaissances basées sur la similarité sémantique
    """

    def __init__(
        self,
        index_path: str = "memory/semantic/index.faiss",
        store_path: str = "memory/semantic/store.parquet",
        model_name: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialiser la mémoire sémantique

        Args:
            index_path: Chemin vers l'index FAISS
            store_path: Chemin vers le store Parquet
            model_name: Nom du modèle d'embedding (default: all-MiniLM-L6-v2)
        """
        if not FAISS_AVAILABLE or not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("FAISS or sentence-transformers not installed")

        self.index_path = Path(index_path)
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

        # Modèle d'embedding
        self.embedder = SentenceTransformer(model_name)
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()

        # Index FAISS
        self.index = None
        self.store = []  # Store des passages avec métadonnées

        # Charger l'index existant s'il existe
        self.load_index()

    def load_index(self):
        """Charger l'index FAISS depuis le disque"""
        if self.index_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                # Charger le store (simulé pour l'instant, utiliser pandas parquet en production)
                if self.store_path.exists():
                    import pandas as pd

                    self.store = pd.read_parquet(self.store_path).to_dict("records")
                print(f"✓ Loaded semantic index with {self.index.ntotal} passages")
            except Exception as e:
                print(f"Warning: Could not load index: {e}. Creating new index.")
                self._create_empty_index()
        else:
            self._create_empty_index()

    def _create_empty_index(self):
        """Créer un index FAISS vide"""
        # Index plat avec distance L2
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.store = []

    def add_passage(
        self,
        text: str,
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """
        Ajouter un passage textuel à la mémoire sémantique

        Args:
            text: Texte du passage
            conversation_id: ID de la conversation
            task_id: ID de la tâche
            metadata: Métadonnées additionnelles
        """
        # Générer un embedding
        embedding = self.embedder.encode(text, convert_to_numpy=True).reshape(1, -1)

        # Créer un ID unique
        passage_id = f"passage:{hashlib.sha256(text.encode()).hexdigest()[:8]}"

        # Ajouter à l'index
        self.index.add(embedding)

        # Ajouter au store
        self.store.append(
            {
                "passage_id": passage_id,
                "text": text,
                "conversation_id": conversation_id,
                "task_id": task_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
        )

    def search(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.7
    ) -> List[Dict[str, any]]:
        """
        Rechercher dans la mémoire sémantique

        Args:
            query: Requête de recherche
            top_k: Nombre de résultats à retourner
            similarity_threshold: Seuil de similarité minimal

        Returns:
            Liste de passages pertinents avec scores
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        # Encoder la requête
        query_embedding = self.embedder.encode(query, convert_to_numpy=True).reshape(1, -1)

        # Rechercher dans l'index (distance L2)
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            # Convertir la distance en score de similarité (approximatif)
            similarity = 1.0 / (1.0 + distance)  # Transformation simple

            if similarity >= similarity_threshold:
                passage = self.store[idx]
                results.append({**passage, "score": float(similarity), "rank": i + 1})

        return results

    def cleanup_old_passages(self, ttl_days: int = 30):
        """
        Nettoyer les passages plus anciens que ttl_days

        Args:
            ttl_days: Durée de conservation en jours

        Returns:
            Nombre de passages supprimés
        """
        cutoff_date = datetime.now() - timedelta(days=ttl_days)

        to_keep = []
        indices_to_remove = []

        for i, passage in enumerate(self.store):
            passage_time = datetime.fromisoformat(passage["timestamp"])
            if passage_time >= cutoff_date:
                to_keep.append(passage)
            else:
                indices_to_remove.append(i)

        # Reconstruire l'index sans les anciens passages
        if indices_to_remove:
            # Créer un nouvel index
            new_index = faiss.IndexFlatL2(self.embedding_dim)
            new_store = []

            for passage in to_keep:
                # Reencoder (ou stocker les embeddings)
                embedding = self.embedder.encode(passage["text"], convert_to_numpy=True).reshape(
                    1, -1
                )
                new_index.add(embedding)
                new_store.append(passage)

            self.index = new_index
            self.store = new_store

            return len(indices_to_remove)

        return 0

    def save_index(self):
        """Sauvegarder l'index FAISS et le store sur disque"""
        # Sauvegarder l'index FAISS
        faiss.write_index(self.index, str(self.index_path))

        # Sauvegarder le store (utiliser pandas parquet)
        if self.store:
            import pandas as pd

            df = pd.DataFrame(self.store)
            df.to_parquet(self.store_path, index=False)

        print(f"✓ Saved semantic index with {len(self.store)} passages")

    def rebuild_index(self):
        """
        Reconstruire l'index depuis le store
        Utile si le store est mis à jour manuellement
        """
        if not self.store:
            return

        new_index = faiss.IndexFlatL2(self.embedding_dim)

        for passage in self.store:
            embedding = self.embedder.encode(passage["text"], convert_to_numpy=True).reshape(1, -1)
            new_index.add(embedding)

        self.index = new_index
        print(f"✓ Rebuilt semantic index with {len(self.store)} passages")


# Instance globale
_semantic_memory: Optional[SemanticMemory] = None


def get_semantic_memory() -> SemanticMemory:
    """Récupérer l'instance globale de la mémoire sémantique"""
    global _semantic_memory
    if _semantic_memory is None:
        _semantic_memory = SemanticMemory()
    return _semantic_memory


def init_semantic_memory(**kwargs) -> SemanticMemory:
    """Initialiser la mémoire sémantique"""
    global _semantic_memory
    _semantic_memory = SemanticMemory(**kwargs)
    return _semantic_memory

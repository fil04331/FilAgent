"""
Interface abstraite pour les modèles LLM
Supporte llama.cpp et vLLM (optionnel)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

__all__ = [
    "ModelInterface",
    "LlamaCppInterface",
    "ModelFactory",
    "GenerationConfig",
    "GenerationResult",
    "get_model",
    "init_model",
]


@dataclass
class GenerationConfig:
    """Configuration de génération"""

    temperature: float = 0.2
    top_p: float = 0.95
    max_tokens: int = 800
    seed: int = 42
    top_k: int = 40
    repetition_penalty: float = 1.1


@dataclass
class GenerationResult:
    """Résultat de génération"""

    text: str
    finish_reason: str  # "stop", "length", "tool_calls"
    tokens_generated: int
    prompt_tokens: int
    total_tokens: int
    tool_calls: Optional[List[Dict]] = None  # Pour les appels d'outils


class ModelInterface(ABC):
    """Interface abstraite pour les modèles LLM"""

    @abstractmethod
    def load(self, model_path: str, config: Dict) -> bool:
        """Charger le modèle depuis le chemin spécifié"""
        pass

    @abstractmethod
    def generate(
        self, prompt: str, config: GenerationConfig, system_prompt: Optional[str] = None
    ) -> GenerationResult:
        """Générer du texte à partir d'un prompt"""
        pass

    @abstractmethod
    def unload(self):
        """Décharger le modèle de la mémoire"""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Vérifier si le modèle est chargé"""
        pass


class LlamaCppInterface(ModelInterface):
    """
    Interface pour llama.cpp via llama-cpp-python

    Format requis: modèle GGUF
    """

    def __init__(self):
        self.model = None
        self._loaded = False

    def load(self, model_path: str, config: Dict) -> bool:
        """Charger un modèle GGUF"""
        try:
            from llama_cpp import Llama

            # Vérifier que le fichier existe
            if not Path(model_path).exists():
                print(f"✗ Model file not found: {model_path}")
                # Fallback: essayer avec le modèle par défaut
                fallback_path = "models/weights/base.gguf"
                if fallback_path != model_path and Path(fallback_path).exists():
                    print(f"⚠ Trying fallback: {fallback_path}")
                    model_path = fallback_path
                else:
                    raise FileNotFoundError(f"Model file not found: {model_path}")

            # Paramètres de chargement
            n_ctx = config.get("context_size", 4096)
            n_gpu_layers = config.get("n_gpu_layers", 35)
            use_mmap = True
            use_mlock = False

            # Charger le modèle
            self.model = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                use_mmap=use_mmap,
                use_mlock=use_mlock,
                verbose=False,
            )

            self._loaded = True
            print(f"✓ Model loaded from {model_path}")
            return True

        except ImportError:
            print("✗ llama-cpp-python not installed")
            print("Fallback: Using mock model for testing")
            self._create_mock_model()
            return True
        except Exception as e:
            print(f"✗ Failed to load model: {e}")
            print("Fallback: Using mock model for testing")
            self._create_mock_model()
            return True

    def _create_mock_model(self):
        """Créer un modèle mock pour fallback"""

        class MockModel:
            def __call__(self, *args, **kwargs):
                return {
                    "choices": [
                        {
                            "text": "[Mock Response] The agent is in fallback mode. The real model could not be loaded.",
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"completion_tokens": 20, "total_tokens": 30},
                }

        self.model = MockModel()
        self._loaded = True
        print("⚠ Using mock model (fallback mode)")

    def generate(
        self, prompt: str, config: GenerationConfig, system_prompt: Optional[str] = None
    ) -> GenerationResult:
        """Générer du texte"""
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load() first.")

        # Construire le prompt complet si system_prompt est fourni
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        else:
            full_prompt = prompt

        try:
            # Estimer les tokens du prompt (approximation)
            prompt_tokens = len(full_prompt.split())

            # Générer avec llama.cpp
            response = self.model(
                full_prompt,
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                repeat_penalty=config.repetition_penalty,
                max_tokens=config.max_tokens,
                seed=config.seed,
                stop=["User:", "\n\nUser:", "System:", "</s>"],
                echo=False,  # Ne pas inclure le prompt dans la réponse
            )

            # Extraire le texte généré
            generated_text = response["choices"][0]["text"]

            # Déterminer la raison de fin
            finish_reason = response["choices"][0].get("finish_reason", "stop")

            # Tokens
            tokens_generated = response["usage"]["completion_tokens"]
            total_tokens = response["usage"]["total_tokens"]

            return GenerationResult(
                text=generated_text.strip(),
                finish_reason=finish_reason,
                tokens_generated=tokens_generated,
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens,
            )

        except Exception as e:
            print(f"⚠ Generation failed: {e}")
            # Fallback: retourner une réponse d'erreur
            return GenerationResult(
                text=f"[Error] Generation failed: {str(e)}. Please check your model configuration.",
                finish_reason="error",
                tokens_generated=0,
                prompt_tokens=prompt_tokens,
                total_tokens=prompt_tokens,
            )

    def unload(self):
        """Décharger le modèle"""
        if self.model:
            # llama.cpp Python ne nécessite pas de déchargement explicite
            # mais on peut marquer comme déchargé
            self.model = None
            self._loaded = False
            print("Model unloaded")

    def is_loaded(self) -> bool:
        """Vérifier si le modèle est chargé"""
        return self._loaded


class ModelFactory:
    """Factory pour créer des instances de modèles"""

    @staticmethod
    def create(backend: str) -> ModelInterface:
        """
        Créer une instance de modèle selon le backend

        Args:
            backend: "llama.cpp" ou "vllm"

        Returns:
            Instance de ModelInterface
        """
        if backend == "llama.cpp":
            return LlamaCppInterface()
        elif backend == "vllm":
            # TODO: Implémenter VLLMInterface quand nécessaire
            raise NotImplementedError("vLLM backend not yet implemented")
        else:
            raise ValueError(f"Unknown backend: {backend}")


# Instance globale pour le modèle
_model_instance: Optional[ModelInterface] = None


def get_model() -> ModelInterface:
    """Récupérer l'instance globale du modèle"""
    global _model_instance
    if _model_instance is None:
        raise RuntimeError("Model not initialized. Call init_model() first.")
    return _model_instance


def init_model(backend: str, model_path: str, config: Dict) -> ModelInterface:
    """Initialiser le modèle global"""
    global _model_instance
    _model_instance = ModelFactory.create(backend)

    # Charger le modèle
    success = _model_instance.load(model_path, config)
    if not success:
        raise RuntimeError(f"Failed to load model from {model_path}")

    return _model_instance

"""
Interface abstraite pour les modèles LLM
Supporte llama.cpp et vLLM (optionnel)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ModelInterface",
    "LlamaCppInterface",
    "PerplexityInterface",
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
    max_tokens: int = 2048  # Increased from 800 to allow full responses
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
    def generate(self, prompt: str, config: GenerationConfig, system_prompt: Optional[str] = None) -> GenerationResult:
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
        self._loaded: bool = False

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
                            "text": (
                                "[Mock Response] The agent is in fallback mode. "
                                "The real model could not be loaded."
                            ),
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"completion_tokens": 20, "total_tokens": 30},
                }

        self.model = MockModel()
        self._loaded = True
        print("⚠ Using mock model (fallback mode)")

    def generate(self, prompt: str, config: GenerationConfig, system_prompt: Optional[str] = None) -> GenerationResult:
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


class PerplexityInterface(ModelInterface):
    """
    Interface pour Perplexity API (compatible OpenAI)

    Modèles supportés:
    - llama-3.1-sonar-small-128k-online
    - llama-3.1-sonar-large-128k-online
    - llama-3.1-sonar-huge-128k-online
    - llama-3.1-8b-instruct
    - llama-3.1-70b-instruct

    Nécessite:
    - Variable d'environnement PERPLEXITY_API_KEY
    - Package openai installé
    """

    def __init__(self):
        self.client = None
        self.model_name = None
        self._loaded: bool = False
        self._rate_limiter = None

    def load(self, model_path: str, config: Dict) -> bool:
        """
        Charger le client Perplexity

        Args:
            model_path: Nom du modèle Perplexity (ex: "llama-3.1-sonar-large-128k-online")
            config: Configuration contenant api_key ou utilise PERPLEXITY_API_KEY env var

        Returns:
            True si succès, False sinon
        """
        try:
            from openai import OpenAI
            import os

            # Récupérer la clé API
            api_key = config.get("api_key") or os.getenv("PERPLEXITY_API_KEY")
            if not api_key:
                print("✗ PERPLEXITY_API_KEY not found in environment or config")
                return False

            # Initialiser le client OpenAI avec base URL Perplexity
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.perplexity.ai"
            )

            # Initialize rate limiter for API protection
            from runtime.utils.rate_limiter import get_rate_limiter
            self._rate_limiter = get_rate_limiter(
                requests_per_minute=10,  # Conservative limit
                requests_per_hour=500
            )

            # Sauvegarder le nom du modèle
            self.model_name = model_path

            self._loaded = True
            print(f"✓ Perplexity client initialized with model: {self.model_name}")
            print("✓ Rate limiting enabled (10 req/min, 500 req/hour)")
            return True

        except ImportError:
            print("✗ openai package not installed")
            print("Install with: pdm install --with ml")
            return False
        except Exception as e:
            # Sanitize error message to avoid leaking sensitive information
            error_str = str(e).lower()
            if any(sensitive in error_str for sensitive in ['api', 'key', 'token', 'secret']):
                print("✗ Failed to initialize Perplexity client: Authentication error")
            else:
                print("✗ Failed to initialize Perplexity client: Configuration error")
            return False

    def generate(
        self,
        prompt: str,
        config: GenerationConfig,
        system_prompt: Optional[str] = None
    ) -> GenerationResult:
        """Générer du texte avec Perplexity API"""
        if not self.is_loaded():
            raise RuntimeError("Perplexity client not loaded. Call load() first.")

        try:
            # Construire les messages
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            # Appel API Perplexity with rate limiting
            def api_call():
                return self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    max_tokens=config.max_tokens,
                    # Perplexity ne supporte pas tous les paramètres
                )

            # Use rate limiter if available, otherwise direct call
            if self._rate_limiter:
                response = self._rate_limiter.execute_with_backoff(api_call)
            else:
                response = api_call()

            # Extraire la réponse
            generated_text = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Tokens
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens

            return GenerationResult(
                text=generated_text.strip(),
                finish_reason=finish_reason,
                tokens_generated=completion_tokens,
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens,
            )

        except Exception as e:
            # Sanitize error message to prevent leaking sensitive information
            error_str = str(e).lower()

            # Check for sensitive patterns and provide safe error messages
            # Order matters: check more specific patterns first
            if 'rate' in error_str and 'limit' in error_str:
                safe_error = "Rate limit exceeded. Please wait before retrying."
                print("⚠ Perplexity generation failed: Rate limit exceeded")
            elif 'timeout' in error_str or 'connection' in error_str:
                safe_error = "Connection error. Please check your network."
                print("⚠ Perplexity generation failed: Connection error")
            elif 'model' in error_str or 'not found' in error_str:
                safe_error = "Model not available. Please check the model name."
                print("⚠ Perplexity generation failed: Model error")
            elif any(sensitive in error_str for sensitive in ['api', 'key', 'token', 'secret', 'auth']):
                safe_error = "Authentication or authorization error. Please verify your API credentials."
                print("⚠ Perplexity generation failed: Authentication error")
            else:
                # Generic error without exposing details
                safe_error = "API request failed. Please try again."
                print("⚠ Perplexity generation failed: Request error")

            return GenerationResult(
                text=f"[Error] {safe_error}",
                finish_reason="error",
                tokens_generated=0,
                prompt_tokens=0,
                total_tokens=0,
            )

    def unload(self):
        """Décharger le client (cleanup)"""
        self.client = None
        self.model_name = None
        self._loaded = False
        print("Perplexity client unloaded")

    def is_loaded(self) -> bool:
        """Vérifier si le client est initialisé"""
        return self._loaded


class ModelFactory:
    """Factory pour créer des instances de modèles"""

    @staticmethod
    def create(backend: str) -> ModelInterface:
        """
        Créer une instance de modèle selon le backend

        Args:
            backend: "llama.cpp", "perplexity", ou "vllm"

        Returns:
            Instance de ModelInterface
        """
        if backend == "llama.cpp":
            return LlamaCppInterface()
        elif backend == "perplexity":
            return PerplexityInterface()
        elif backend == "vllm":
            # TODO: Implémenter VLLMInterface quand nécessaire
            raise NotImplementedError("vLLM backend not yet implemented")
        else:
            raise ValueError(f"Unknown backend: {backend}. Supported: llama.cpp, perplexity, vllm")


# Instance globale pour le modèle
_model_instance: Optional[ModelInterface] = None


def get_model() -> ModelInterface:
    """Récupérer l'instance globale du modèle"""
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

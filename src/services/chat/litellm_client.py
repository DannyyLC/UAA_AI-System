"""
Cliente LiteLLM para integración con múltiples proveedores de LLM.

Soporta:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude)
- Google (Gemini)
- Y cualquier otro proveedor compatible con LiteLLM

Features:
- Function calling
- Streaming
- Manejo de contexto
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import litellm
from litellm import acompletion

from src.shared.configuration import settings
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)

# Configurar LiteLLM
litellm.drop_params = True  # Ignorar parámetros no soportados
litellm.set_verbose = settings.debug


class LiteLLMClient:
    """
    Cliente para interactuar con LLMs via LiteLLM.
    
    Simplifica el uso de múltiples proveedores con una API unificada.
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """
        Inicializa el cliente LiteLLM.
        
        Args:
            model: Modelo a usar (default: del settings)
            temperature: Temperatura para generación (0-2)
            max_tokens: Máximo de tokens a generar (None = sin límite)
        """
        self.model = model or settings.llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Configurar API keys
        self._setup_api_keys()
        
        logger.info(f"LiteLLM Client inicializado: model={self.model}")
    
    def _setup_api_keys(self):
        """Configura las API keys según el proveedor."""
        if settings.openai_api_key:
            litellm.openai_key = settings.openai_api_key
        if settings.anthropic_api_key:
            litellm.anthropic_key = settings.anthropic_api_key
        if settings.gemini_api_key:
            litellm.gemini_key = settings.gemini_api_key
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Genera una respuesta completa (sin streaming).
        
        Args:
            messages: Lista de mensajes en formato OpenAI
            tools: Lista de tools disponibles para function calling
            tool_choice: "auto", "none", o {"type": "function", "function": {"name": "..."}}
            temperature: Override de temperatura
            max_tokens: Override de max_tokens
            
        Returns:
            Respuesta del LLM con structure:
            {
                "content": "...",
                "tool_calls": [...] (opcional),
                "finish_reason": "stop" | "tool_calls" | "length",
                "usage": {...}
            }
        """
        try:
            temp = temperature if temperature is not None else self.temperature
            max_tok = max_tokens if max_tokens is not None else self.max_tokens
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temp,
            }
            
            if max_tok is not None:
                kwargs["max_tokens"] = max_tok
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice
            
            logger.debug(f"Llamando a LiteLLM: model={self.model}, messages={len(messages)}")
            
            response = await acompletion(**kwargs)
            
            # Extraer información de la respuesta
            choice = response.choices[0]
            message = choice.message
            
            result = {
                "content": message.content or "",
                "finish_reason": choice.finish_reason,
                "usage": dict(response.usage) if hasattr(response, 'usage') else {}
            }
            
            # Agregar tool_calls si existen
            if hasattr(message, 'tool_calls') and message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            
            logger.info(
                f"LLM completado: finish_reason={result['finish_reason']}, "
                f"tokens={result.get('usage', {}).get('total_tokens', 'N/A')}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error en LiteLLM completion: {e}")
            raise
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Genera una respuesta con streaming.
        
        Args:
            messages: Lista de mensajes en formato OpenAI
            tools: Lista de tools disponibles
            tool_choice: Configuración de tool choice
            temperature: Override de temperatura
            max_tokens: Override de max_tokens
            
        Yields:
            Chunks de la respuesta:
            {
                "type": "content" | "tool_call" | "done",
                "delta": "texto parcial" (si type=content),
                "tool_call": {...} (si type=tool_call),
                "finish_reason": "..." (si type=done)
            }
        """
        try:
            temp = temperature if temperature is not None else self.temperature
            max_tok = max_tokens if max_tokens is not None else self.max_tokens
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temp,
                "stream": True
            }
            
            if max_tok is not None:
                kwargs["max_tokens"] = max_tok
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice
            
            logger.debug(f"Streaming LiteLLM: model={self.model}, messages={len(messages)}")
            
            response = await acompletion(**kwargs)
            
            # Variables para acumular tool calls (pueden venir en múltiples chunks)
            tool_calls_buffer = {}
            
            async for chunk in response:
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason
                
                # Contenido de texto
                if hasattr(delta, 'content') and delta.content:
                    yield {
                        "type": "content",
                        "delta": delta.content
                    }
                
                # Tool calls
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {
                                "id": "",
                                "type": "function",
                                "function": {
                                    "name": "",
                                    "arguments": ""
                                }
                            }
                        
                        if tc_delta.id:
                            tool_calls_buffer[idx]["id"] = tc_delta.id
                        
                        if hasattr(tc_delta, 'function'):
                            if tc_delta.function.name:
                                tool_calls_buffer[idx]["function"]["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls_buffer[idx]["function"]["arguments"] += tc_delta.function.arguments
                
                # Finalización
                if finish_reason:
                    # Enviar tool calls completos si existen
                    if tool_calls_buffer:
                        yield {
                            "type": "tool_call",
                            "tool_calls": list(tool_calls_buffer.values())
                        }
                    
                    # Enviar señal de finalización
                    yield {
                        "type": "done",
                        "finish_reason": finish_reason
                    }
            
            logger.info(f"Streaming completado: finish_reason={finish_reason}")
            
        except Exception as e:
            logger.error(f"Error en LiteLLM streaming: {e}")
            raise
    
    def format_messages(
        self,
        system_message: str,
        conversation_history: List[Dict[str, Any]],
        user_message: str
    ) -> List[Dict[str, Any]]:
        """
        Formatea mensajes para el LLM.
        
        Args:
            system_message: Mensaje del sistema (con temas disponibles)
            conversation_history: Historial de mensajes previos
            user_message: Mensaje actual del usuario
            
        Returns:
            Lista de mensajes en formato OpenAI
        """
        messages = [
            {"role": "system", "content": system_message}
        ]
        
        # Agregar historial
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Agregar mensaje actual
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages

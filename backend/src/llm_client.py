"""
LLM client abstraction supporting both OpenAI and Google Gemini models.
"""
import os
import time
from typing import Optional, Union, List, Dict, Any
from openai import OpenAI
from openai import RateLimitError
from google import genai
from google.genai import types
from .llm_rate_limiter import get_rate_limiter, estimate_tokens


class LLMClient:
    """Unified client for OpenAI and Gemini models."""
    
    def __init__(self, provider: str = "gemini", model: str = "gemini-3-flash-preview"):
        """
        Initialize LLM client.
        
        Args:
            provider: "openai" or "gemini"
            model: Model name (e.g., "gemini-3-flash-preview", "gpt-4o")
        """
        self.provider = provider.lower()
        self.model = model
        
        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.client = OpenAI(api_key=api_key)
        elif self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            self.genai_client = genai.Client(api_key=api_key)
            # Cache original Gemini Content objects so thought_signatures are preserved
            # when replaying conversation history. Maps tool_call_id -> original Content.
            self._gemini_content_cache: Dict[str, types.Content] = {}
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'openai' or 'gemini'")
    
    def chat_completions_create(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> Any:
        """
        Create a chat completion using the configured provider.
        
        Returns a response object compatible with OpenAI's response format.
        """
        if self.provider == "openai":
            return self._openai_chat_completion(messages, tools, tool_choice, temperature, **kwargs)
        elif self.provider == "gemini":
            return self._gemini_chat_completion(messages, tools, tool_choice, temperature, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _openai_chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: Optional[str],
        temperature: float,
        **kwargs
    ):
        """Create OpenAI chat completion with rate limiting and retry logic."""
        response_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if tools:
            response_kwargs["tools"] = tools
            if tool_choice:
                response_kwargs["tool_choice"] = tool_choice
        
        response_kwargs.update(kwargs)
        
        # Estimate tokens for rate limiting
        estimated_tokens = estimate_tokens(messages, self.model)
        if tools:
            # Add overhead for tools
            estimated_tokens += 100
        
        # Get rate limiter and wait if needed
        rate_limiter = get_rate_limiter()
        wait_time = rate_limiter.wait_if_needed(estimated_tokens)
        if wait_time > 0:
            print(f"[RATE_LIMITER] Waited {wait_time:.2f}s to avoid rate limit")
        
        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(**response_kwargs)
                
                # Record successful usage
                if hasattr(response, 'usage') and response.usage:
                    tokens_used = response.usage.total_tokens
                    rate_limiter.record_usage(tokens_used)
                else:
                    # Fallback: use estimate
                    rate_limiter.record_usage(estimated_tokens)
                
                return response
                
            except RateLimitError as e:
                # Extract retry-after from error if available
                retry_after = None
                if hasattr(e, 'response') and e.response:
                    headers = getattr(e.response, 'headers', {})
                    retry_after_header = headers.get('retry-after') or headers.get('Retry-After')
                    if retry_after_header:
                        try:
                            retry_after = float(retry_after_header)
                        except (ValueError, TypeError):
                            pass
                
                # Calculate delay with exponential backoff
                if retry_after:
                    delay = retry_after
                else:
                    delay = base_delay * (2 ** attempt)
                
                if attempt < max_retries - 1:
                    print(f"[RATE_LIMITER] Rate limit hit, waiting {delay:.2f}s before retry {attempt + 1}/{max_retries}")
                    rate_limiter.record_rate_limit_error(retry_after)
                    time.sleep(delay)
                else:
                    # Last attempt failed
                    print(f"[RATE_LIMITER] Rate limit error after {max_retries} attempts")
                    raise
            except Exception as e:
                # For other errors, don't retry
                raise
    
    def _convert_openai_tools_to_gemini(self, tools: List[Dict[str, Any]]) -> List[types.Tool]:
        """Convert OpenAI function-calling tool definitions to Gemini format."""
        function_declarations = []
        for tool_def in tools:
            if tool_def.get("type") != "function":
                continue
            func = tool_def["function"]
            fd = types.FunctionDeclaration(
                name=func["name"],
                description=func.get("description", ""),
                parameters=func.get("parameters"),
            )
            function_declarations.append(fd)
        return [types.Tool(function_declarations=function_declarations)]

    def _convert_messages_for_gemini(self, messages: List[Dict[str, Any]]):
        """Convert OpenAI-format messages to Gemini contents + system_instruction.

        Handles text messages, assistant tool_calls, and tool response messages.
        """
        contents = []
        system_instruction = None

        # We need to group consecutive tool-response messages into a single user turn
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg.get("role", "user")

            if role == "system":
                if system_instruction:
                    system_instruction = system_instruction + "\n\n" + msg.get("content", "")
                else:
                    system_instruction = msg.get("content", "")
                i += 1

            elif role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                # Check if we have the original Gemini Content cached (preserves thought_signatures)
                cached_content = None
                if tool_calls and hasattr(self, '_gemini_content_cache'):
                    first_id = tool_calls[0].get("id", "")
                    cached_content = self._gemini_content_cache.get(first_id)
                if cached_content:
                    contents.append(cached_content)
                else:
                    parts = []
                    content = msg.get("content")
                    if content:
                        parts.append(types.Part(text=content))
                    if tool_calls:
                        for tc in tool_calls:
                            func = tc.get("function", {})
                            args = func.get("arguments", "{}")
                            if isinstance(args, str):
                                import json as _json
                                try:
                                    args = _json.loads(args)
                                except _json.JSONDecodeError:
                                    args = {}
                            parts.append(types.Part(
                                function_call=types.FunctionCall(
                                    name=func.get("name", ""),
                                    args=args,
                                )
                            ))
                    if parts:
                        contents.append(types.Content(role="model", parts=parts))
                i += 1

            elif role == "tool":
                # Collect consecutive tool responses into one user turn
                fn_response_parts = []
                while i < len(messages) and messages[i].get("role") == "tool":
                    tool_msg = messages[i]
                    # Find the function name from the preceding assistant tool_calls
                    fn_name = self._find_function_name_for_tool_call(
                        messages, tool_msg.get("tool_call_id", "")
                    )
                    fn_response_parts.append(types.Part(
                        function_response=types.FunctionResponse(
                            name=fn_name,
                            response={"result": tool_msg.get("content", "")},
                        )
                    ))
                    i += 1
                contents.append(types.Content(role="user", parts=fn_response_parts))

            else:  # user
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=msg.get("content", ""))]
                ))
                i += 1

        return contents, system_instruction

    @staticmethod
    def _find_function_name_for_tool_call(messages: List[Dict[str, Any]], tool_call_id: str) -> str:
        """Find the function name that matches a tool_call_id in prior assistant messages."""
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc.get("id") == tool_call_id:
                        return tc.get("function", {}).get("name", "unknown")
        return "unknown"

    def _gemini_chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: Optional[str],
        temperature: float,
        **kwargs
    ):
        """Create Gemini chat completion with OpenAI-compatible response format."""
        contents, system_instruction = self._convert_messages_for_gemini(messages)

        # Prepare generation config
        config_params = {
            "temperature": temperature,
        }
        if system_instruction:
            config_params["system_instruction"] = system_instruction

        # Convert and attach tools
        if tools:
            config_params["tools"] = self._convert_openai_tools_to_gemini(tools)
            # Map tool_choice to Gemini's FunctionCallingConfig
            if tool_choice == "auto":
                config_params["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="AUTO")
                )
            elif tool_choice == "none":
                config_params["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="NONE")
                )
            elif tool_choice == "required":
                config_params["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="ANY")
                )

        generation_config = types.GenerateContentConfig(**config_params)

        try:
            response = self.genai_client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generation_config,
            )

            # Check if Gemini returned function calls
            function_calls = []
            text_content = None
            original_content = None
            if response.candidates and response.candidates[0].content:
                original_content = response.candidates[0].content
                if original_content.parts:
                    for part in original_content.parts:
                        if part.function_call:
                            function_calls.append(part.function_call)
                        elif part.text and not part.thought:
                            text_content = (text_content or "") + part.text

            if function_calls:
                return self._build_tool_call_response(
                    function_calls, text_content, original_content, self._gemini_content_cache
                )
            else:
                return self._build_text_response(text_content or "", self.model)

        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    @staticmethod
    def _build_tool_call_response(function_calls, text_content, original_content=None, content_cache=None):
        """Build an OpenAI-compatible response containing tool calls."""
        import uuid as _uuid
        import json as _json

        class MockFunction:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = arguments

        class MockToolCall:
            def __init__(self, call_id, function):
                self.id = call_id
                self.type = "function"
                self.function = function

        class MockMessage:
            def __init__(self, content, tool_calls):
                self.content = content
                self.role = "assistant"
                self.tool_calls = tool_calls

        class MockChoice:
            def __init__(self, message):
                self.message = message
                self.finish_reason = "tool_calls"

        class MockResponse:
            def __init__(self, choice, model_name):
                self.choices = [choice]
                self.model = model_name
                self.usage = None

        mock_tool_calls = []
        for fc in function_calls:
            call_id = f"call_{_uuid.uuid4().hex[:24]}"
            args_str = _json.dumps(fc.args) if fc.args else "{}"
            mock_tool_calls.append(
                MockToolCall(call_id, MockFunction(fc.name, args_str))
            )

        # Cache the original Gemini Content so we can replay it with thought_signatures intact
        if original_content is not None and content_cache is not None and mock_tool_calls:
            content_cache[mock_tool_calls[0].id] = original_content

        message = MockMessage(text_content, mock_tool_calls)
        choice = MockChoice(message)
        return MockResponse(choice, "gemini")

    @staticmethod
    def _build_text_response(text, model_name):
        """Build an OpenAI-compatible text-only response."""
        class MockMessage:
            def __init__(self, content):
                self.content = content
                self.role = "assistant"
                self.tool_calls = None

        class MockChoice:
            def __init__(self, message):
                self.message = message
                self.finish_reason = "stop"

        class MockResponse:
            def __init__(self, choice, model_name):
                self.choices = [choice]
                self.model = model_name
                self.usage = None

        return MockResponse(MockChoice(MockMessage(text)), model_name)
    
    def embeddings_create(self, input_text: Union[str, List[str]], model: str = "text-embedding-3-small") -> List[List[float]]:
        """
        Create embeddings. For Gemini, falls back to OpenAI embeddings.
        """
        if self.provider == "openai":
            response = self.client.embeddings.create(
                model=model,
                input=input_text
            )
            if isinstance(input_text, str):
                return [response.data[0].embedding]
            return [item.embedding for item in response.data]
        elif self.provider == "gemini":
            # Gemini doesn't have a direct embeddings API in the same way
            # For now, use OpenAI for embeddings even when using Gemini for chat
            # This could be improved with Gemini's embedding models if available
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError("OpenAI API key required for embeddings when using Gemini")
            temp_client = OpenAI(api_key=openai_key)
            response = temp_client.embeddings.create(
                model=model,
                input=input_text
            )
            if isinstance(input_text, str):
                return [response.data[0].embedding]
            return [item.embedding for item in response.data]
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")


def get_llm_client(model: Optional[str] = None) -> LLMClient:
    """
    Factory function to create an LLM client based on model name or environment.
    
    Args:
        model: Model name (e.g., "gemini-3-flash-preview", "gpt-4o")
               If None, uses LLM_PROVIDER and LLM_MODEL env vars or defaults to OpenAI gpt-4o
    """
    if model:
        # Determine provider from model name
        if model.startswith("gemini"):
            provider = "gemini"
        else:
            provider = "openai"
    else:
        # Use environment variables
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        model = os.getenv("LLM_MODEL", "gemini-3-flash-preview")
    
    return LLMClient(provider=provider, model=model)


"""
configure generator models for haystack
wrap ollama and openai for text generation
provide dynamic model selection
custom models use same haystack generators
"""

import httpx


# ==================== GENERATOR FACTORY ====================

def get_generator(config, model_id: str = None):
    # create generator for model id
    from backend.helpers.persist.model_registry_helpers import get_model_config

    # set default model id
    if not model_id:
        model_id = config.DEFAULT_OLLAMA_MODEL

    # load model config
    model_config = get_model_config(model_id)
    if not model_config:
        raise ValueError(f"model config not found for id '{model_id}'")

    # read provider id
    provider = model_config.get("provider", "ollama")
    actual_model_id = model_config.get("model_id", model_id)

    # route generator by provider
    if provider == "ollama":
        return _create_ollama_generator(config, actual_model_id, model_config)
    if provider == "openai":
        return _create_openai_generator(config, model_config)
    if provider == "anthropic":
        return _create_anthropic_generator(config, model_config)

    raise ValueError(f"unknown provider '{provider}' for model '{model_id}'")


# ==================== OLLAMA GENERATOR ====================

def _create_ollama_generator(config, model_id: str, model_config: dict = None):
    # create haystack ollama generator
    from haystack_integrations.components.generators.ollama import OllamaGenerator

    # set default model id
    if not model_id:
        model_id = config.DEFAULT_OLLAMA_MODEL

    # read base url
    base_url = model_config.get("base_url") if model_config else None
    if not base_url:
        base_url = config.OLLAMA_HOST

    # print selected model
    print(f"[GENERATOR] Using Ollama model: {model_id}")
    print(f"[GENERATOR] Ollama host: {base_url}")

    # build base generator
    base_gen = OllamaGenerator(
        model=model_id,
        url=base_url,
        generation_kwargs={
            "num_predict": config.LLM_NUM_PREDICT,
            "temperature": config.LLM_TEMPERATURE,
            "top_p": config.LLM_TOP_P
        },
        timeout=config.LLM_TIMEOUT
    )

    class OllamaWrapper:
        def __init__(self, base, defaults):
            # store base generator
            self.base = base

            # store default kwargs
            self.defaults = defaults or {}

        def warm_up(self):
            # forward warm up call
            if hasattr(self.base, "warm_up"):
                return self.base.warm_up()
            return None

        def run(self, prompt: str = "", generation_kwargs: dict = None, timeout: int = None, **kwargs):
            # merge defaults and overrides
            gen_kwargs = dict(self.defaults)
            if isinstance(generation_kwargs, dict):
                gen_kwargs.update(generation_kwargs)

            # map max_tokens to num_predict
            if kwargs.get("max_tokens"):
                gen_kwargs["num_predict"] = int(kwargs.get("max_tokens"))

            # run generator
            return self.base.run(prompt=prompt, generation_kwargs=gen_kwargs)

    # build default kwarg map
    defaults = {
        "num_predict": config.LLM_NUM_PREDICT,
        "temperature": config.LLM_TEMPERATURE,
        "top_p": config.LLM_TOP_P
    }

    return OllamaWrapper(base_gen, defaults)


# ==================== OPENAI GENERATOR ====================

def _create_openai_generator(config, model_config: dict):
    # create haystack openai generator
    from haystack.components.generators import OpenAIGenerator

    # read model fields
    model_id = model_config.get("model_id") or config.DEFAULT_OPENAI_MODEL
    api_key = model_config.get("api_key") or config.OPENAI_API_KEY
    base_url = model_config.get("base_url")

    # print selected model
    print(f"[GENERATOR] Using OpenAI model: {model_id}")
    if base_url:
        print(f"[GENERATOR] OpenAI base URL: {base_url}")

    class _SecretAdapter:
        def __init__(self, val):
            # store secret value
            self._val = val

        def resolve_value(self):
            # return secret value
            return self._val

    # build generator kwargs
    generator_kwargs = {
        "model": model_id,
        "api_key": _SecretAdapter(api_key),
        "generation_kwargs": {
            "max_tokens": config.LLM_NUM_PREDICT,
            "temperature": config.LLM_TEMPERATURE,
            "top_p": config.LLM_TOP_P
        }
    }

    # set custom base url
    if base_url:
        generator_kwargs["api_base_url"] = base_url

    # build base generator
    base_gen = OpenAIGenerator(**generator_kwargs)

    class OpenAIWrapper:
        def __init__(self, base, defaults):
            # store base generator
            self.base = base

            # store default kwargs
            self.defaults = defaults or {}

        def warm_up(self):
            # forward warm up call
            if hasattr(self.base, "warm_up"):
                return self.base.warm_up()
            return None

        def run(self, prompt: str = "", generation_kwargs: dict = None, timeout: int = None, **kwargs):
            # merge defaults and overrides
            gen_kwargs = dict(self.defaults)
            if isinstance(generation_kwargs, dict):
                gen_kwargs.update(generation_kwargs)

            # map generic tokens
            if kwargs.get("max_tokens") is not None:
                gen_kwargs["max_tokens"] = int(kwargs.get("max_tokens"))
            if kwargs.get("num_predict") is not None:
                gen_kwargs["max_tokens"] = int(kwargs.get("num_predict"))

            # run generator
            return self.base.run(prompt=prompt, generation_kwargs=gen_kwargs)

    # read default generation kwargs
    defaults = generator_kwargs.get("generation_kwargs", {})
    return OpenAIWrapper(base_gen, defaults)


# ==================== ANTHROPIC GENERATOR ====================

class AnthropicGenerator:

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        timeout: int,
        api_version: str,
        max_keepalive: int,
        max_connections: int,
    ):
        # store client fields
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.timeout = timeout
        self.api_version = api_version
        self.max_keepalive = int(max_keepalive)
        self.max_connections = int(max_connections)

    def warm_up(self):
        # no warm up request
        return

    def run(self, prompt: str, generation_kwargs: dict = None, timeout: int = None):
        # call anthropic messages api
        if not prompt:
            return {"replies": [""]}

        # build request url
        url = f"{self.base_url}/messages"

        # read token override
        gen_kwargs = generation_kwargs or {}
        if gen_kwargs.get("max_tokens") is not None:
            max_tokens = int(gen_kwargs.get("max_tokens"))
        elif gen_kwargs.get("num_predict") is not None:
            max_tokens = int(gen_kwargs.get("num_predict"))
        else:
            max_tokens = int(self.max_tokens)

        # build request payload
        payload = {
            "model": self.model,
            "max_tokens": int(max_tokens),
            "temperature": float(self.temperature),
            "top_p": float(self.top_p),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        # build request headers
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json"
        }

        # run http client
        with httpx.Client(
            timeout=self.timeout,
            limits=httpx.Limits(
                max_keepalive_connections=self.max_keepalive,
                max_connections=self.max_connections,
            )
        ) as client:
            response = client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            # print error summary
            text = response.text[:500]
            print(f"[GENERATOR] Anthropic error {response.status_code}: {text}")
            return {"replies": [""]}

        # parse response json
        data = response.json()

        # read content blocks
        content_list = data.get("content") or []
        text_blocks = []
        for block in content_list:
            # select text blocks
            if isinstance(block, dict) and block.get("type") == "text":
                block_text = block.get("text") or ""
                if block_text:
                    text_blocks.append(block_text)

        # join reply blocks
        reply_text = "\n".join(text_blocks).strip()

        return {"replies": [reply_text]}


def _create_anthropic_generator(config, model_config: dict):
    # create anthropic wrapper
    model_id = model_config.get("model_id") or config.DEFAULT_ANTHROPIC_MODEL
    api_key = model_config.get("api_key") or config.ANTHROPIC_API_KEY
    base_url = model_config.get("base_url") or "https://api.anthropic.com/v1"
    api_version = config.ANTHROPIC_API_VERSION

    # print selected model
    print(f"[GENERATOR] Using Anthropic model: {model_id}")
    print(f"[GENERATOR] Anthropic base URL: {base_url}")
    print(f"[GENERATOR] Anthropic API version: {api_version}")

    # build base client
    base_gen = AnthropicGenerator(
        model=model_id,
        api_key=api_key,
        base_url=base_url,
        max_tokens=config.LLM_NUM_PREDICT,
        temperature=config.LLM_TEMPERATURE,
        top_p=config.LLM_TOP_P,
        timeout=config.LLM_TIMEOUT,
        api_version=api_version,
        max_keepalive=config.HTTP_MAX_KEEPALIVE_CONNECTIONS,
        max_connections=config.HTTP_MAX_CONNECTIONS,
    )

    class AnthropicWrapper:
        def __init__(self, base, defaults):
            # store base client
            self.base = base

            # store default kwargs
            self.defaults = defaults or {}

        def warm_up(self):
            # forward warm up call
            if hasattr(self.base, "warm_up"):
                return self.base.warm_up()
            return None

        def run(self, prompt: str = "", generation_kwargs: dict = None, timeout: int = None, **kwargs):
            # merge defaults and overrides
            gen_kwargs = dict(self.defaults)
            if isinstance(generation_kwargs, dict):
                gen_kwargs.update(generation_kwargs)

            # map generic tokens
            if kwargs.get("max_tokens") is not None:
                gen_kwargs["max_tokens"] = int(kwargs.get("max_tokens"))
            if kwargs.get("num_predict") is not None:
                gen_kwargs["max_tokens"] = int(kwargs.get("num_predict"))

            # run generator
            return self.base.run(prompt=prompt, generation_kwargs=gen_kwargs, timeout=timeout)

    # build default kwarg map
    defaults = {
        "max_tokens": config.LLM_NUM_PREDICT,
        "temperature": config.LLM_TEMPERATURE,
        "top_p": config.LLM_TOP_P
    }

    return AnthropicWrapper(base_gen, defaults)
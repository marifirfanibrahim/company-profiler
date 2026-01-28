"""
model providers map
default model registry
static model entries
"""

# ==================== MODEL PROVIDERS ====================

PROVIDERS = {
    'ollama': {
        'name': 'Ollama',
        'type': 'local',
        'requires_api_key': False,
        'base_url': 'http://localhost:11434'
    },
    'openai': {
        'name': 'OpenAI',
        'type': 'api',
        'requires_api_key': True,
        'base_url': 'https://api.openai.com/v1'
    },
    'anthropic': {
        'name': 'Anthropic',
        'type': 'api',
        'requires_api_key': True,
        'base_url': 'https://api.anthropic.com/v1'
    }
}


# ==================== DEFAULT MODELS ====================

DEFAULT_MODELS = {
    'llama3.2:3b': {
        'name': 'Llama 3.2 3B',
        'provider': 'ollama',
        'model_id': 'llama3.2:3b',
        'description': 'fast lightweight local model',
        'enabled': True
    },
    'llama3:8b': {
        'name': 'Llama 3 8B',
        'provider': 'ollama',
        'model_id': 'llama3:8b',
        'description': 'balanced local model',
        'enabled': True
    },
    'gpt-4o-mini': {
        'name': 'GPT-4o Mini',
        'provider': 'openai',
        'model_id': 'gpt-4o-mini',
        'description': 'fast affordable openai model',
        'enabled': True
    },
    'gpt-4o': {
        'name': 'GPT-4o',
        'provider': 'openai',
        'model_id': 'gpt-4o',
        'description': 'most capable openai model',
        'enabled': True
    },
    'claude-3-sonnet': {
        'name': 'Claude 3 Sonnet',
        'provider': 'anthropic',
        'model_id': 'claude-3-sonnet-20240229',
        'description': 'balanced anthropic claude model',
        'enabled': True
    }
}
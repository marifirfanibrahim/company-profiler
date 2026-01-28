"""
manage model registry
load custom models
save custom models
"""

from backend.configuration.paths import CUSTOM_MODELS_PATH
from backend.configuration.models import DEFAULT_MODELS, PROVIDERS
from backend.helpers.persist.json_utils import load_json, save_json


# ==================== LOAD ====================

def get_all_models():
    # combine default and custom models
    all_models = dict(DEFAULT_MODELS)

    # read custom models file
    if CUSTOM_MODELS_PATH.exists():
        custom = load_json(CUSTOM_MODELS_PATH, default={})
        if isinstance(custom, dict):
            for model_id, model_config in custom.items():
                # skip disabled models
                if model_config.get('enabled', True):
                    all_models[model_id] = model_config

    return all_models


def get_model_config(model_id):
    # get configuration for model id
    all_models = get_all_models()
    return all_models.get(model_id)


def get_provider_config(provider_id):
    # get provider configuration
    return PROVIDERS.get(provider_id)


def get_custom_models():
    # get only custom models
    if not CUSTOM_MODELS_PATH.exists():
        return {}

    data = load_json(CUSTOM_MODELS_PATH, default={})
    if isinstance(data, dict):
        return data

    return {}


# ==================== WRITE ====================

def save_custom_model(model_id, model_config):
    # save custom model to file
    if CUSTOM_MODELS_PATH.exists():
        custom_models = load_json(CUSTOM_MODELS_PATH, default={})
        if not isinstance(custom_models, dict):
            custom_models = {}
    else:
        custom_models = {}

    # store model config
    custom_models[model_id] = model_config

    # write json file
    ok = save_json(CUSTOM_MODELS_PATH, custom_models)
    return bool(ok)


def delete_custom_model(model_id):
    # delete custom model from file
    if not CUSTOM_MODELS_PATH.exists():
        return False

    custom_models = load_json(CUSTOM_MODELS_PATH, default={})
    if not isinstance(custom_models, dict):
        return False

    # drop model id
    if model_id in custom_models:
        del custom_models[model_id]
        ok = save_json(CUSTOM_MODELS_PATH, custom_models)
        return bool(ok)

    return False
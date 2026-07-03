"""
main application routes
serve html pages
provide health check
provide system statistics
provide model definitions
"""

from flask import Blueprint, render_template, jsonify, current_app, request

from backend.configuration.config import Config
from backend.configuration.models import PROVIDERS, DEFAULT_MODELS
from backend.helpers.persist.model_registry_helpers import (
    get_all_models,
    get_custom_models,
    save_custom_model,
    delete_custom_model,
)


# create main blueprint
main_bp = Blueprint("main", __name__)


# ================ PAGES ================

@main_bp.route("/")
def index():
    # serve search page
    return render_template("index.html")


# ================ API ================

@main_bp.route("/health", methods=["GET"])
def health():
    # check component health status
    components = current_app.components

    # return health status
    return jsonify(
        {
            "status": "ok",
            "components": {
                "config": components.get("config") is not None,
                "doc_store": components.get("doc_store") is not None,
                "pipeline": components.get("pipeline") is not None,
                "profiles_db": components.get("profiles_db") is not None,
            },
        }
    )


@main_bp.route("/api/models", methods=["GET"])
def get_models():
    # return all model definitions
    app_config = current_app.components.get("config")
    default_model_id = app_config.DEFAULT_OLLAMA_MODEL

    # load model map
    all_models = get_all_models()

    # build model list
    models_list = [
        {
            "id": model_id,
            "name": cfg.get("name", model_id),
            "provider": cfg.get("provider", "ollama"),
            "description": cfg.get("description", ""),
            "is_custom": model_id not in DEFAULT_MODELS,
        }
        for model_id, cfg in all_models.items()
        if cfg.get("enabled", True)
    ]

    # store default ids
    default_ids = list(DEFAULT_MODELS.keys())

    def sort_key(m):
        # sort models by default and name
        if default_model_id and m["id"] == default_model_id:
            return (0, m["name"])
        if m["id"] in default_ids:
            return (1, m["name"])
        return (2, m["name"])

    # sort models list
    models_list.sort(key=sort_key)

    # return json list
    return jsonify(models_list)


@main_bp.route("/api/models/providers", methods=["GET"])
def get_providers():
    # return available providers
    providers_list = [
        {
            "id": provider_id,
            "name": config.get("name", provider_id),
            "type": config.get("type", "api"),
            "requires_api_key": config.get("requires_api_key", True),
        }
        for provider_id, config in PROVIDERS.items()
    ]

    # return json list
    return jsonify(providers_list)


@main_bp.route("/api/custom-models", methods=["GET", "POST"])
def manage_custom_models():
    # handle custom model routes
    if request.method == "GET":
        # return custom models map
        return jsonify(get_custom_models())

    # read request data
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "invalid json payload"}), 400

    # read model id
    model_id = data.get("model_id")
    if not model_id:
        return jsonify({"error": "model_id is required"}), 400

    # build config payload
    model_config = {
        "name": data.get("name", model_id),
        "provider": data.get("provider", "ollama"),
        "model_id": data.get("actual_model_id", model_id),
        "description": data.get("description", ""),
        "enabled": data.get("enabled", True),
    }

    # add api key
    if data.get("api_key"):
        model_config["api_key"] = data.get("api_key")

    # add base url
    if data.get("base_url"):
        model_config["base_url"] = data.get("base_url")

    # persist model
    if save_custom_model(model_id, model_config):
        return jsonify({"message": "model saved", "id": model_id}), 200

    return jsonify({"error": "failed to save model"}), 500


@main_bp.route("/api/custom-models/<model_id>", methods=["DELETE"])
def delete_custom_model_route(model_id):
    # delete custom model
    if delete_custom_model(model_id):
        return jsonify({"message": "model deleted"}), 200
    return jsonify({"error": "not found"}), 404


@main_bp.route("/api/profiles", methods=["GET"])
def list_profiles_route():
    # list recent profiles from sqlite
    db = current_app.components.get("profiles_db")
    if not db:
        return jsonify({"error": "profiles db not initialized"}), 503

    # read config
    app_config = current_app.components.get("config")
    default_limit = int(app_config.PROFILES_API_DEFAULT_LIMIT)

    # parse limit
    limit_raw = request.args.get("limit")
    if limit_raw is None:
        limit = default_limit
    else:
        raw = str(limit_raw).strip()
        if not raw.isdigit():
            return jsonify({"error": "limit must be integer"}), 400
        limit = int(raw)

    # fetch profiles
    profiles = db.fetch_recent_profiles(limit=limit)
    return jsonify(profiles)


@main_bp.route("/api/profiles/<int:profile_id>", methods=["GET"])
def get_profile_route(profile_id):
    # fetch single profile from sqlite
    db = current_app.components.get("profiles_db")
    if not db:
        return jsonify({"error": "profiles db not initialized"}), 503

    # fetch record
    item = db.fetch_profile_by_id(profile_id)
    if not item:
        return jsonify({"error": "not found"}), 404

    # build response
    response = {
        "query": item.get("company") or "",
        "search_time": 0.0,
        "timestamp": item.get("created_at"),
        "profile_id": item.get("profile_id"),
        "snapshot": item.get("snapshot") or "",
        "customer": item.get("customer") or {},
        "corporate_guarantor": item.get("corporate_guarantor") or {},
        "high_risk_entities": item.get("high_risk_entities") or [],
        "confidence_score": float(item.get("confidence") or 0.0),
        "documents": item.get("documents") or [],
        "model_id": "",
        "fact_check_score": None,
    }

    # return json response
    return jsonify(response)


@main_bp.route("/api/profiles/<int:profile_id>", methods=["DELETE"])
def delete_profile_route(profile_id):
    # delete single profile from sqlite by id
    db = current_app.components.get("profiles_db")
    if not db:
        return jsonify({"error": "profiles db not initialized"}), 503

    # delete record
    deleted = db.delete_profile_by_id(profile_id)
    if deleted:
        return jsonify({"deleted": deleted}), 200
    return jsonify({"error": "not found"}), 404


@main_bp.route("/about")
def about():
    # return app information
    return jsonify(
        {
            "name": "company_profiler",
            "version": f"{Config.APP_VERSION}",
            "description": "business intelligence reports based on open source data",
        }
    )
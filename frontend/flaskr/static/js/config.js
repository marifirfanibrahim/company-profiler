/*
configuration ui logic
manage custom models
*/


/* ==================== STATE ==================== */

// track model being edited
let editingModelId = null;

// cache available models for badges
window.availableModels = [];


/* ==================== CUSTOM MODELS ==================== */

function openModelModal() {
    // open model modal and load data
    loadCustomModelsForModal();
    const modal = document.getElementById('modelModal');
    if (modal) {
        modal.style.display = 'block';
    }
    openAddModelForm();
}

function closeModelModal() {
    // close model modal
    const modal = document.getElementById('modelModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function openAddModelForm() {
    // reset form for new model
    editingModelId = null;

    // read dom nodes
    const titleEl = document.getElementById('modelFormTitle');
    const idEl = document.getElementById('m_id');
    const nameEl = document.getElementById('m_name');
    const providerEl = document.getElementById('m_provider');
    const actualIdEl = document.getElementById('m_actual_id');
    const apiKeyEl = document.getElementById('m_api_key');
    const baseUrlEl = document.getElementById('m_base_url');
    const descEl = document.getElementById('m_desc');
    const saveBtn = document.getElementById('saveModelBtn');
    const cancelBtn = document.getElementById('cancelModelEditBtn');

    // reset dom values
    if (titleEl) titleEl.textContent = 'Add New Model';
    if (idEl) {
        idEl.value = '';
        idEl.readOnly = false;
    }
    if (nameEl) nameEl.value = '';
    if (providerEl) providerEl.value = 'ollama';
    if (actualIdEl) actualIdEl.value = '';
    if (apiKeyEl) apiKeyEl.value = '';
    if (baseUrlEl) baseUrlEl.value = '';
    if (descEl) descEl.value = '';
    if (saveBtn) saveBtn.textContent = 'Save Model';
    if (cancelBtn) cancelBtn.style.display = 'none';

    // update field visibility
    updateApiKeyVisibility();
}

function updateApiKeyVisibility() {
    // show or hide api key field based on provider
    const providerEl = document.getElementById('m_provider');
    const apiKeyContainer = document.getElementById('apiKeyContainer');

    // stop on missing dom
    if (!providerEl || !apiKeyContainer) return;

    // read provider
    const provider = providerEl.value;
    if (provider === 'ollama') {
        apiKeyContainer.style.display = 'none';
    } else {
        apiKeyContainer.style.display = 'block';
    }
}

async function loadCustomModelsForModal() {
    // fetch and display custom models
    const container = document.getElementById('customModelListContainer');
    if (!container) return;

    // fetch custom models
    const response = await fetch('/api/custom-models');
    if (!response.ok) {
        container.innerHTML = '<p style="text-align:center; color:#999;">failed to load models</p>';
        return;
    }

    const models = await response.json();

    // reset container
    container.innerHTML = '';

    // read keys
    const keys = Object.keys(models || {});
    if (keys.length === 0) {
        container.innerHTML = '<p style="text-align:center; color:#999;">No custom models created yet.</p>';
        return;
    }

    for (const [id, m] of Object.entries(models)) {
        // build item node
        const item = document.createElement('div');
        item.className = 'custom-model-item';

        // build provider label
        let providerLabel = 'Ollama';
        if (m.provider === 'openai') providerLabel = 'OpenAI';
        else if (m.provider === 'anthropic') providerLabel = 'Anthropic';

        // set item html
        item.innerHTML = `
            <div class="custom-model-header">
                <div class="custom-model-info">
                    <strong>${escapeHtml(m.name || id)}</strong>
                    <span class="provider-label">(${providerLabel})</span>
                </div>
                <div class="custom-model-actions">
                    <button class="btn btn-secondary btn-small" onclick="openEditModelForm('${id}')">Edit</button>
                    <button class="btn btn-danger btn-small" onclick="deleteCustomModel('${id}')">Delete</button>
                </div>
            </div>
            <div class="custom-model-details">
                <small>Model ID: ${escapeHtml(m.model_id || id)}</small>
            </div>
        `;

        // append item
        container.appendChild(item);
    }
}

async function saveCustomModel() {
    // save new or updated model
    const isNew = !editingModelId;

    // read dom nodes
    const idEl = document.getElementById('m_id');
    const nameEl = document.getElementById('m_name');
    const providerEl = document.getElementById('m_provider');
    const actualIdEl = document.getElementById('m_actual_id');
    const apiKeyEl = document.getElementById('m_api_key');
    const baseUrlEl = document.getElementById('m_base_url');
    const descEl = document.getElementById('m_desc');

    // read model id
    const m_id = (idEl && idEl.value.trim()) || '';
    if (!m_id) {
        showNotification('Model ID is required.', 'error');
        return;
    }

    // build payload
    const payload = {
        model_id: m_id,
        name: (nameEl && nameEl.value.trim()) || '',
        provider: (providerEl && providerEl.value) || 'ollama',
        actual_model_id: (actualIdEl && actualIdEl.value.trim()) || '',
        api_key: (apiKeyEl && apiKeyEl.value.trim()) || '',
        base_url: (baseUrlEl && baseUrlEl.value.trim()) || '',
        description: (descEl && descEl.value.trim()) || '',
        is_new: isNew
    };

    // validate name
    if (!payload.name) {
        showNotification('Display Name is required.', 'error');
        return;
    }

    // validate actual id
    if (!payload.actual_model_id) {
        showNotification('Actual Model ID is required.', 'error');
        return;
    }

    // send request
    const response = await fetch('/api/custom-models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    // parse json
    const result = await response.json();

    // handle response
    if (!response.ok) {
        showNotification(result.error || 'save failed', 'error');
        return;
    }

    // show message
    showNotification(isNew ? 'Model added!' : 'Model updated!', 'success');

    // reset form
    openAddModelForm();

    // refresh list
    loadCustomModelsForModal();

    // refresh dropdown
    loadAndPopulateModels(document.getElementById('modelSelector'));
}

async function openEditModelForm(id) {
    // load model data for editing
    const response = await fetch('/api/custom-models');
    if (!response.ok) {
        showNotification('failed to load models', 'error');
        return;
    }

    const models = await response.json();
    const m = models[id];

    // validate model id
    if (!m) {
        showNotification('Model not found for editing.', 'error');
        return;
    }

    // set edit state
    editingModelId = id;

    // read dom nodes
    const titleEl = document.getElementById('modelFormTitle');
    const idEl = document.getElementById('m_id');
    const nameEl = document.getElementById('m_name');
    const providerEl = document.getElementById('m_provider');
    const actualIdEl = document.getElementById('m_actual_id');
    const apiKeyEl = document.getElementById('m_api_key');
    const baseUrlEl = document.getElementById('m_base_url');
    const descEl = document.getElementById('m_desc');
    const saveBtn = document.getElementById('saveModelBtn');
    const cancelBtn = document.getElementById('cancelModelEditBtn');

    // set dom values
    if (titleEl) titleEl.textContent = 'Edit Model';
    if (idEl) {
        idEl.value = id;
        idEl.readOnly = true;
    }
    if (nameEl) nameEl.value = m.name || '';
    if (providerEl) providerEl.value = m.provider || 'ollama';
    if (actualIdEl) actualIdEl.value = m.model_id || '';
    if (apiKeyEl) apiKeyEl.value = '';
    if (baseUrlEl) baseUrlEl.value = m.base_url || '';
    if (descEl) descEl.value = m.description || '';
    if (saveBtn) saveBtn.textContent = 'Update Model';
    if (cancelBtn) cancelBtn.style.display = 'inline-block';

    // update field visibility
    updateApiKeyVisibility();
}

async function deleteCustomModel(id) {
    // delete custom model
    if (!confirm(`Are you sure you want to delete the model '${id}'?`)) return;

    // send delete request
    const response = await fetch(`/api/custom-models/${id}`, { method: 'DELETE' });

    // parse json
    const result = await response.json();

    // handle response
    if (!response.ok) {
        showNotification(result.error || 'delete failed', 'error');
        return;
    }

    // show message
    showNotification('Model deleted.', 'success');

    // refresh list
    loadCustomModelsForModal();

    // refresh dropdown
    loadAndPopulateModels(document.getElementById('modelSelector'));
}

async function loadAndPopulateModels(selector) {
    // fetch models from api and populate dropdown
    if (!selector) return;

    // fetch models
    const response = await fetch('/api/models');

    // stop on error
    if (!response.ok) {
        return;
    }

    // parse json
    const models = await response.json();

    // store cache
    window.availableModels = models;

    // snapshot current selection
    const currentVal = selector.value;

    // reset dropdown
    selector.innerHTML = '';

    models.forEach(m => {
        // create option node
        const option = document.createElement('option');

        // set option values
        option.value = m.id;
        option.textContent = m.name;

        // mark custom models
        if (m.is_custom) option.textContent += ' ✦';

        // append option
        selector.appendChild(option);
    });

    // restore selection
    if (Array.from(selector.options).some(opt => opt.value === currentVal)) {
        selector.value = currentVal;
    }
}


/* ==================== INITIALIZATION ==================== */

document.addEventListener('DOMContentLoaded', function() {
    const manageModelsBtn = document.getElementById('manageModelsBtn');
    if (manageModelsBtn) {
        manageModelsBtn.addEventListener('click', openModelModal);
    }
    const closeModelBtn = document.getElementById('closeModelModal');
    if (closeModelBtn) {
        closeModelBtn.addEventListener('click', closeModelModal);
    }
    const saveModelBtn = document.getElementById('saveModelBtn');
    if (saveModelBtn) {
        saveModelBtn.addEventListener('click', saveCustomModel);
    }
    const cancelEditModelBtn = document.getElementById('cancelModelEditBtn');
    if (cancelEditModelBtn) {
        cancelEditModelBtn.addEventListener('click', openAddModelForm);
    }
    const providerSelect = document.getElementById('m_provider');
    if (providerSelect) {
        providerSelect.addEventListener('change', updateApiKeyVisibility);
    }

    window.addEventListener('click', function(e) {
        const modelModal = document.getElementById('modelModal');
        if (e.target === modelModal) closeModelModal();
    });
});
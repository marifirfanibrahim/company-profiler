/*
search logic module
handle queries and results
manage recent searches
*/

/* ==================== STATE ==================== */

// store current search results
let currentResults = null;

// controller for aborting requests
let searchAbortController = null;

// server profile cache
let serverProfiles = [];


/* ==================== CACHE HELPERS ==================== */

const RESULT_CACHE_KEY = 'searchResultCache';

function saveSearchResultToCache(data) {
    // save single result under unique id
    const raw = localStorage.getItem(RESULT_CACHE_KEY) || '{}';
    let cache = JSON.parse(raw);
    if (!cache || typeof cache !== 'object') cache = {};

    // build cache id
    const resultId = Date.now().toString() + '_' + Math.random().toString(36).slice(2, 8);
    cache[resultId] = data;

    // compute allowed ids
    const recent = getRecentSearches();
    const allowed = new Set();

    // keep recent cache ids
    recent.forEach(item => {
        if (item && item.cache_id) {
            allowed.add(item.cache_id);
        }
    });

    // keep current cache id
    allowed.add(resultId);

    // prune cache map
    const pruned = {};
    Object.keys(cache).forEach(key => {
        if (allowed.has(key)) {
            pruned[key] = cache[key];
        }
    });

    // store pruned cache
    localStorage.setItem(RESULT_CACHE_KEY, JSON.stringify(pruned));
    return resultId;
}

function loadSearchResultFromCacheById(resultId) {
    // load cached result by id
    if (!resultId) return null;

    const raw = localStorage.getItem(RESULT_CACHE_KEY);
    if (!raw) return null;

    const cache = JSON.parse(raw);
    if (!cache || typeof cache !== 'object') return null;

    return cache[resultId] || null;
}


/* ==================== PENDING SEARCH HELPERS ==================== */

function savePendingSearch(query, modelId) {
    // save pending search
    const payload = {
        query: query || '',
        model_id: modelId || ''
    };
    sessionStorage.setItem('pendingSearch', JSON.stringify(payload));
}

function loadPendingSearch() {
    // load pending search
    const raw = sessionStorage.getItem('pendingSearch');
    if (!raw) return null;
    return JSON.parse(raw);
}

function clearPendingSearch() {
    // clear pending search
    sessionStorage.removeItem('pendingSearch');
}


/* ==================== RECENT SEARCHES (LOCAL) ==================== */

function getRecentSearches() {
    // get recent list
    return JSON.parse(localStorage.getItem('recentSearches') || '[]');
}

function saveRecentSearchFromResult(data, cacheId) {
    // save completed search into local recent list
    const query = (data.query || '').trim();
    const model = data.model_id || '';
    const ts = data.timestamp || new Date().toISOString();
    const profileId = data.profile_id || null;

    if (!query) return;

    // load local list
    let recent = JSON.parse(localStorage.getItem('recentSearches') || '[]');

    // append new row
    recent.unshift({
        query: query,
        model: model,
        timestamp: ts,
        profile_id: profileId,
        cache_id: cacheId || null
    });

    // store local list
    localStorage.setItem('recentSearches', JSON.stringify(recent));
}


/* ==================== RECENT SEARCHES (SERVER) ==================== */

async function loadServerProfiles(limit) {
    // load recent profiles from server
    const cap = typeof limit === 'number' && limit > 0 ? limit : getUiConfigValue('SIDEBAR_PROFILES_LIMIT');
    const response = await fetch(`/api/profiles?limit=${cap}`);
    if (!response.ok) {
        serverProfiles = [];
        return;
    }
    const items = await response.json();
    serverProfiles = Array.isArray(items) ? items : [];
}

function mergeServerProfilesWithLocalCache(serverList, localList) {
    // merge cache ids into server rows
    const locals = Array.isArray(localList) ? localList : [];
    const byProfileId = {};
    locals.forEach(item => {
        if (!item) return;
        const pid = item.profile_id;
        if (!pid) return;
        byProfileId[String(pid)] = item;
    });

    // build merged list
    const out = [];
    (serverList || []).forEach(p => {
        if (!p) return;

        const pid = p.profile_id;
        const key = pid ? String(pid) : '';
        const local = key ? byProfileId[key] : null;

        out.push({
            query: p.company || '',
            model: (local && local.model) ? local.model : '',
            timestamp: p.created_at || '',
            profile_id: pid || null,
            cache_id: (local && local.cache_id) ? local.cache_id : null
        });
    });

    return out;
}

async function refreshSidebarFromServer() {
    // refresh sidebar list from server
    const limit = getUiConfigValue('SIDEBAR_PROFILES_LIMIT');
    await loadServerProfiles(limit);
    renderSidebarRecentSearches();
}


/* ==================== SIDEBAR RENDER ==================== */

function selectRecentSearch(query, model) {
    // set query and model into controls
    document.getElementById('searchQuery').value = query || '';

    const modelSelector = document.getElementById('modelSelector');
    if (model && modelSelector) {
        modelSelector.value = model;
    }
}

async function deleteProfileEntry(entry, event) {
    // delete profile entry from server and local
    event.stopPropagation();

    // read profile id
    const pid = entry && entry.profile_id;
    if (pid) {
        await fetch(`/api/profiles/${pid}`, { method: 'DELETE' });
    }

    // prune local cache list
    let recent = JSON.parse(localStorage.getItem('recentSearches') || '[]');
    recent = recent.filter(x => !(x && x.profile_id && String(x.profile_id) === String(pid)));
    localStorage.setItem('recentSearches', JSON.stringify(recent));

    // refresh server list
    await refreshSidebarFromServer();
}

function renderSidebarRecentSearches() {
    // render sidebar list
    const container = document.getElementById('sidebarRecentSearches');
    if (!container) return;

    // read lists
    const localRecent = getRecentSearches();
    const merged = mergeServerProfilesWithLocalCache(serverProfiles, localRecent);

    if (!merged.length) {
        container.innerHTML = '<p class="sidebar-recent-empty">no recent searches</p>';
        return;
    }

    // reset container
    container.innerHTML = '';

    merged.forEach((item) => {
        // build wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'sidebar-recent-item';

        // build header
        const header = document.createElement('div');
        header.className = 'sidebar-recent-header';

        // build query label
        const qSpan = document.createElement('span');
        qSpan.className = 'sidebar-recent-query';
        qSpan.textContent = item.query || '';

        // build time label
        const tSpan = document.createElement('span');
        tSpan.className = 'sidebar-recent-time';
        tSpan.textContent = getTimeAgo(new Date(item.timestamp || new Date().toISOString()));

        // build delete button
        const delBtn = document.createElement('button');
        delBtn.className = 'sidebar-recent-delete';
        delBtn.type = 'button';
        delBtn.textContent = '×';
        delBtn.addEventListener('click', function (e) {
            deleteProfileEntry(item, e);
        });

        // append header children
        header.appendChild(qSpan);
        header.appendChild(tSpan);
        header.appendChild(delBtn);

        // append wrapper children
        wrapper.appendChild(header);

        // bind click handler
        wrapper.addEventListener('click', function (e) {
            if (e.target === delBtn) return;
            openSavedSearchEntry(item);
        });

        // append wrapper
        container.appendChild(wrapper);
    });
}

async function openSavedSearchEntry(entry) {
    // load cached search or server profile and display it
    if (!entry) return;

    // read entry fields
    const query = entry.query || '';
    const model = entry.model || '';
    const cacheId = entry.cache_id || null;
    const profileId = entry.profile_id || null;

    // sync ui controls
    selectRecentSearch(query, model);

    // load cached result
    const cached = loadSearchResultFromCacheById(cacheId);
    if (cached) {
        hideLoading();
        displayResultsProgressive(cached);
        document.getElementById('searchBtn').style.display = 'inline-block';
        document.getElementById('cancelBtn').style.display = 'none';
        searchAbortController = null;
        return;
    }

    // load server profile
    if (profileId) {
        showLoading();
        const response = await fetch(`/api/profiles/${profileId}`);
        hideLoading();

        if (!response.ok) {
            showNotification('saved profile not found on server', 'error');
            document.getElementById('searchBtn').style.display = 'inline-block';
            document.getElementById('cancelBtn').style.display = 'none';
            searchAbortController = null;
            return;
        }

        const data = await response.json();
        displayResultsProgressive(data);
        document.getElementById('searchBtn').style.display = 'inline-block';
        document.getElementById('cancelBtn').style.display = 'none';
        searchAbortController = null;
        return;
    }

    // show missing result
    hideLoading();
    showNotification('saved result not found for this search', 'error');
    document.getElementById('searchBtn').style.display = 'inline-block';
    document.getElementById('cancelBtn').style.display = 'none';
    searchAbortController = null;
}


/* ==================== SEARCH LOGIC ==================== */

async function performSearch() {
    // execute main search
    const query = document.getElementById('searchQuery').value.trim();
    const modelId = document.getElementById('modelSelector').value;

    // validate query
    if (!query) {
        showError('please enter query');
        return;
    }

    // clear last results
    sessionStorage.removeItem('lastSearchResults');

    // store pending search
    savePendingSearch(query, modelId);

    // show loading state
    showLoading();

    // toggle action buttons
    document.getElementById('searchBtn').style.display = 'none';
    document.getElementById('cancelBtn').style.display = 'inline-block';

    // init abort controller
    searchAbortController = new AbortController();

    // send request
    const response = await fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({
            query: query,
            model_id: modelId
        }),
        signal: searchAbortController.signal
    });

    if (!response.ok) {
        clearPendingSearch();
        const errorData = await response.json();
        const message = errorData.summary || errorData.error || 'server error';
        hideLoading();
        showError(message);
        document.getElementById('searchBtn').style.display = 'inline-block';
        document.getElementById('cancelBtn').style.display = 'none';
        searchAbortController = null;
        return;
    }

    // parse response
    const data = await response.json();

    // handle empty output
    if (
        data.error &&
        !data.snapshot &&
        !data.customer &&
        !data.corporate_guarantor &&
        (!data.high_risk_entities || data.high_risk_entities.length === 0)
    ) {
        clearPendingSearch();
        hideLoading();
        showError(data.error);
        document.getElementById('searchBtn').style.display = 'inline-block';
        document.getElementById('cancelBtn').style.display = 'none';
        searchAbortController = null;
        return;
    }

    // clear pending
    clearPendingSearch();

    // hide loading state
    hideLoading();

    // store cache row
    const cacheId = saveSearchResultToCache(data);

    // render output
    displayResultsProgressive(data);

    // store recent row
    saveRecentSearchFromResult(data, cacheId);

    // refresh sidebar
    await refreshSidebarFromServer();

    // toggle action buttons
    document.getElementById('searchBtn').style.display = 'inline-block';
    document.getElementById('cancelBtn').style.display = 'none';
    searchAbortController = null;
}

function cancelSearch() {
    // abort current search
    if (searchAbortController) {
        searchAbortController.abort();
    }
    clearPendingSearch();
    hideLoading();
    document.getElementById('searchBtn').style.display = 'inline-block';
    document.getElementById('cancelBtn').style.display = 'none';
}


/* ==================== STATUS DISPLAY ==================== */

function showLoading() {
    // show spinner
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'none';
}

function hideLoading() {
    // hide spinner
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    // show error section
    const errorDiv = document.getElementById('error');
    document.getElementById('errorMessage').textContent = message;
    errorDiv.style.display = 'block';
    document.getElementById('results').style.display = 'none';
    document.getElementById('loading').style.display = 'none';
}


/* ==================== BADGES ==================== */

function displayModelBadge(modelId) {
    // show model badge
    const badge = document.getElementById('modelBadge');
    if (modelId) {
        const model = (window.availableModels || []).find(m => m.id === modelId);
        const modelName = model ? model.name : modelId;
        badge.textContent = modelName;
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }
}

function displayConfidenceBadge(confidenceScore) {
    // show confidence badge
    const badge = document.getElementById('confidenceBadge');

    if (typeof confidenceScore !== 'number') {
        badge.style.display = 'none';
        return;
    }

    const score = Math.max(0, Math.min(1, confidenceScore));

    badge.style.display = 'inline-block';
    badge.textContent = `${(score * 100).toFixed(0)}%`;
    badge.className = 'confidence-badge';

    if (score >= 0.7) {
        badge.classList.add('high');
    } else if (score >= 0.4) {
        badge.classList.add('medium');
    } else {
        badge.classList.add('low');
    }
}


/* ==================== DISPLAY ==================== */

function displayResultsProgressive(data) {
    // render search output
    currentResults = data;
    sessionStorage.setItem('lastSearchResults', JSON.stringify(data));

    document.getElementById('results').style.display = 'block';
    document.getElementById('error').style.display = 'none';

    displayModelBadge(data.model_id);
    displayConfidenceBadge(data.confidence_score);
    displaySearchTime(data);

    displaySnapshot(data.snapshot, data.documents);
    displayCustomer(data.customer, data.documents);
    displayCorporateGuarantor(data.corporate_guarantor, data.documents);
    displayHighRiskEntities(data.high_risk_entities, data.documents);
}

function displaySearchTime(data) {
    // show search time
    const badge = document.getElementById('searchTimeBadge');
    if (data.search_time !== undefined) {
        badge.textContent = `${data.search_time}s`;
        badge.className = 'search-time-badge';
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }
}

function displaySnapshot(snapshot, documents) {
    // show snapshot text and sources
    const container = document.getElementById('snapshotContainer');
    container.innerHTML = '';

    const text = (snapshot || '').trim();
    if (!text) {
        container.innerHTML = '<p>No snapshot could be generated from the available sources.</p>';
    } else {
        const p = document.createElement('p');
        p.textContent = text;
        container.appendChild(p);
    }

    renderSnapshotSourcesFromDocuments(text, documents);
}

function displayCustomer(customer, documents) {
    // show customer card and sources
    const nameEl = document.getElementById('customerName');
    const ratingEl = document.getElementById('customerRating');
    const esgEl = document.getElementById('customerEsg');
    const dirEl = document.getElementById('customerNewDirector');
    const dateEl = document.getElementById('customerAppointmentDate');

    const data = customer || {};

    const nameRaw = (data.name || '').trim();
    const displayName = nameRaw || 'Not identified';

    const rating = (data.rating || '').trim();
    const esg = (data.esg_scorecard || '').trim();
    const newDirector = (data.new_director || '').trim();
    const appointmentDate = (data.appointment_date || '').trim();

    nameEl.textContent = displayName;
    ratingEl.textContent = rating || '-';
    esgEl.textContent = esg || 'No ESG information identified in the available sources.';

    if (newDirector) {
        dirEl.textContent = newDirector;
        dateEl.textContent = appointmentDate ? `Appointment date: ${appointmentDate}` : '';
    } else {
        dirEl.textContent = 'No new director appointment identified in the available sources.';
        dateEl.textContent = '';
    }

    renderCustomerSourcesFromProfile(data, documents);
}

function displayCorporateGuarantor(corporateGuarantor, documents) {
    // show guarantor card and sources
    const nameEl = document.getElementById('guarantorName');
    const ratingEl = document.getElementById('guarantorRating');
    const esgEl = document.getElementById('guarantorEsg');
    const dirEl = document.getElementById('guarantorNewDirector');
    const dateEl = document.getElementById('guarantorAppointmentDate');

    const data = corporateGuarantor || {};

    const nameRaw = (data.name || '').trim();
    const rating = (data.rating || '').trim();
    const esg = (data.esg_scorecard || '').trim();
    const newDirector = (data.new_director || '').trim();
    const appointmentDate = (data.appointment_date || '').trim();

    const displayName = nameRaw || 'Not identified';

    nameEl.textContent = displayName;
    ratingEl.textContent = rating || '-';
    esgEl.textContent = esg || 'No ESG information identified for the guarantor in the available sources.';

    if (newDirector) {
        dirEl.textContent = newDirector;
        dateEl.textContent = appointmentDate ? `Appointment date: ${appointmentDate}` : '';
    } else {
        dirEl.textContent = 'No new director appointment identified for the guarantor.';
        dateEl.textContent = '';
    }

    renderGuarantorSourcesFromProfile(data, documents);
}

function displayHighRiskEntities(highRiskEntities, documents) {
    // show high risk table and sources
    const container = document.getElementById('highRiskTableContainer');
    container.innerHTML = '';

    const list = Array.isArray(highRiskEntities) ? highRiskEntities : [];

    let html = '<table class="cases-table">';
    html += '<thead><tr>';
    html += '<th>Name</th>';
    html += '<th>Position</th>';
    html += '<th>Status / Relationship</th>';
    html += '</tr></thead><tbody>';

    if (list.length === 0) {
        html += '<tr><td colspan="3">No high risk entities or individuals were identified in the available sources.</td></tr>';
    } else {
        list.forEach(item => {
            if (!item) return;
            const name = escapeHtml(item.name || '');
            const position = escapeHtml(item.position || '');
            const relationship = escapeHtml(item.relationship || '');
            html += `<tr><td>${name || '-'}</td><td>${position || '-'}</td><td>${relationship || '-'}</td></tr>`;
        });
    }

    html += '</tbody></table>';
    container.innerHTML = html;

    renderHighRiskSourcesFromEntities(list, documents);
}


/* ==================== EXPORT ==================== */

function exportResults(format) {
    // export search results
    if (!currentResults) {
        alert('no results to export');
        return;
    }

    const rawQuery = typeof currentResults.query === 'string' ? currentResults.query.trim() : '';
    const baseName = rawQuery || 'search';
    const safeQuery = baseName.replace(/[^\w\-]+/g, '_').slice(0, 50) || 'search';
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filenameBase = `bzint3_${safeQuery}_${timestamp}`;

    if (format === 'txt') {
        const content = formatAsText(currentResults);
        downloadFile(content, `${filenameBase}.txt`, 'text/plain');
    } else if (format === 'doc') {
        const html = formatAsHtmlDoc(currentResults);
        downloadFile(html, `${filenameBase}.doc`, 'application/msword');
    } else if (format === 'pdf') {
        exportPdfWithTable(currentResults, filenameBase);
    }
}


/* ==================== UTILS ==================== */

function getTimeAgo(date) {
    // compute time ago
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

async function restoreOnLoad() {
    // refresh behaviour: do not auto-search
    const pending = loadPendingSearch();
    if (pending && pending.query) {
        const searchInput = document.getElementById('searchQuery');
        if (searchInput) searchInput.value = pending.query;
        const modelSelector = document.getElementById('modelSelector');
        if (modelSelector && pending.model_id) modelSelector.value = pending.model_id;
        clearPendingSearch();
    } else {
        clearPendingSearch();
    }

    // no pending search
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    hideLoading();
}


/* ==================== INITIALIZATION ==================== */

document.addEventListener('DOMContentLoaded', async function() {
    loadDarkModePreference();
    initializeDarkModeToggle();
    initializeSidebar();

    const searchInput = document.getElementById('searchQuery');
    if (searchInput) {
        // run search on enter
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') performSearch();
        });
    }

    await loadAndPopulateModels(document.getElementById('modelSelector'));

    await restoreOnLoad();

    await refreshSidebarFromServer();
});
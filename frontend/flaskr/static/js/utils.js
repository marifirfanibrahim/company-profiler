/*
shared utility functions
manage dark mode preferences
handle notifications
format and export data
display summary with profile fields
*/


// ==================== DARK MODE ====================

function toggleDarkMode() {
    // toggle dark mode class
    const body = document.body;
    body.classList.toggle('dark-mode');

    // store preference
    const isDark = body.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDark ? 'enabled' : 'disabled');

    // update button icons
    const toggleButtons = document.querySelectorAll('.dark-mode-toggle');
    toggleButtons.forEach(btn => {
        btn.textContent = isDark ? '☀️' : '🌙';
    });
}

function loadDarkModePreference() {
    // load dark mode from storage
    if (localStorage.getItem('darkMode') === 'enabled') {
        document.body.classList.add('dark-mode');
    }
}

function initializeDarkModeToggle() {
    // create toggle button
    const existingToggle = document.getElementById('darkModeToggle');
    if (existingToggle) return;

    // build button node
    const darkModeBtn = document.createElement('button');
    darkModeBtn.className = 'dark-mode-toggle';
    darkModeBtn.id = 'darkModeToggle';

    // bind toggle handler
    darkModeBtn.onclick = toggleDarkMode;

    // set initial icon
    darkModeBtn.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';

    // append button
    document.body.appendChild(darkModeBtn);
}


// ==================== NOTIFICATIONS ====================

function showNotification(message, type = 'info', duration = 4000) {
    // show floating notification
    const existing = document.querySelector('.floating-notification');
    if (existing) existing.remove();

    // build notification node
    const notification = document.createElement('div');
    notification.className = `floating-notification ${type}`;
    notification.textContent = message;

    // append notification
    document.body.appendChild(notification);

    // schedule removal
    setTimeout(() => {
        if (notification) {
            notification.style.animation = 'slideOutRight 0.3s ease-in forwards';
            setTimeout(() => notification.remove(), 300);
        }
    }, duration);
}


// ==================== UI CONFIG ====================

function getUiConfigValue(key) {
    // read ui config value
    const cfg = window.UI_CONFIG || {};
    return cfg[key];
}


// ==================== TEXT NORMALIZATION ====================

function normalizeForSearch(text) {
    // normalize text for search
    if (!text) return '';
    return String(text)
        .toLowerCase()
        .replace(/\s+/g, ' ')
        .trim();
}

function stripUrlsFromText(text) {
    // remove embedded urls from string
    if (!text) return '';
    return String(text)
        .replace(/https?:\/\/\S+/gi, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function isMeaningfulFieldValue(value) {
    // check placeholder values
    const s = String(value || '').trim();
    if (!s) return false;

    // normalize value
    const lower = s.toLowerCase();

    // define placeholders
    const placeholders = [
        '-',
        'n/a',
        'na',
        'none',
        'null',
        'not identified',
        'unknown'
    ];

    // block placeholder values
    if (placeholders.includes(lower)) return false;

    // block direct no
    if (lower === 'no') return false;

    // block short strings
    if (s.length < 3) return false;

    return true;
}

function getDocCitationFromMeta(doc) {
    // build citation from meta
    if (!doc || !doc.meta) {
        return { title: '', url: '', date: '' };
    }

    // read meta fields
    const meta = doc.meta;
    const url = typeof meta.url === 'string' ? meta.url : '';
    const rawTitle = meta.title || '';
    const rawSnippet = meta.snippet || '';
    const date = meta.source_date || '';

    let title = '';

    // detect url-like strings
    const looksLikeUrl = (s) => /^https?:\/\//i.test(String(s || '').trim());

    // prefer title over snippet
    if (rawTitle && !looksLikeUrl(rawTitle)) {
        title = String(rawTitle).trim();
    } else if (rawSnippet) {
        title = String(rawSnippet).trim();
    } else if (rawTitle) {
        title = String(rawTitle).trim();
    } else if (url) {
        title = String(url).trim();
    }

    // strip embedded urls
    title = stripUrlsFromText(title);

    return {
        title: title,
        url: url,
        date: date
    };
}

function findDocsForText(text, documents, maxCount) {
    // find docs containing text
    const docs = Array.isArray(documents) ? documents : [];
    const limit = typeof maxCount === 'number' && maxCount > 0 ? maxCount : docs.length;

    // normalize target text
    let normText = normalizeForSearch(text);
    if (!normText) return [];

    // clamp text size
    if (normText.length > 200) {
        normText = normText.slice(0, 200);
    }

    const matches = [];

    for (let i = 0; i < docs.length; i++) {
        // stop on limit
        if (matches.length >= limit) break;

        // read doc fields
        const doc = docs[i] || {};
        const content = stripUrlsFromText(doc.content || '');
        const meta = doc.meta || {};
        const title = stripUrlsFromText(meta.title || '');
        const snippet = stripUrlsFromText(meta.snippet || '');

        // build search haystack
        const hay = normalizeForSearch(content + ' ' + title + ' ' + snippet);
        if (!hay) continue;

        // match normalized text
        if (hay.indexOf(normText) !== -1) {
            matches.push(i);
        }
    }

    return matches;
}

function docCitationsFromIndices(documents, indices) {
    // map indices to unique citations
    const docs = Array.isArray(documents) ? documents : [];
    const seen = new Set();
    const citations = [];

    (indices || []).forEach(idx => {
        // validate index
        if (idx < 0 || idx >= docs.length) return;

        // build citation
        const doc = docs[idx] || {};
        const c = getDocCitationFromMeta(doc);

        // validate title
        const title = String(c.title || '').trim();
        if (!title) return;

        // build dedupe key
        const key = `${title.toLowerCase()}|${c.url || ''}|${c.date || ''}`;
        if (seen.has(key)) return;

        // store key and row
        seen.add(key);
        citations.push({
            title: title,
            url: c.url || '',
            date: c.date || ''
        });
    });

    return citations;
}


// ==================== SOURCES COMPUTATION ====================

function computeSnapshotSources(documents) {
    // compute snapshot sources from all documents
    const docs = Array.isArray(documents) ? documents : [];
    if (!docs.length) return [];

    // build index list
    const indices = [];
    for (let i = 0; i < docs.length; i++) {
        indices.push(i);
    }

    // map citations
    return docCitationsFromIndices(docs, indices);
}

function computeProfileFieldSources(profile, documents) {
    // compute sources per profile field
    const data = profile || {};
    const fields = {};

    // read profile fields
    const name = (data.name || '').trim();
    const rating = (data.rating || '').trim();
    const esg = (data.esg_scorecard || '').trim();
    const director = (data.new_director || '').trim();
    const apptDate = (data.appointment_date || '').trim();

    // compute name citations
    if (isMeaningfulFieldValue(name) && name.toLowerCase() !== 'not identified') {
        const idxs = findDocsForText(name, documents, 5);
        const cites = docCitationsFromIndices(documents, idxs);
        if (cites.length) fields.name = cites;
    }

    // compute rating citations
    if (isMeaningfulFieldValue(rating)) {
        const idxs = findDocsForText(rating, documents, 5);
        const cites = docCitationsFromIndices(documents, idxs);
        if (cites.length) fields.rating = cites;
    }

    // compute esg citations
    if (isMeaningfulFieldValue(esg)) {
        const idxs = findDocsForText(esg, documents, 5);
        const cites = docCitationsFromIndices(documents, idxs);
        if (cites.length) fields.esg_scorecard = cites;
    }

    // compute director citations
    if (isMeaningfulFieldValue(director)) {
        const idxs = findDocsForText(director, documents, 5);
        const cites = docCitationsFromIndices(documents, idxs);
        if (cites.length) fields.new_director = cites;
    }

    // compute appointment date citations
    if (isMeaningfulFieldValue(apptDate)) {
        const idxs = findDocsForText(apptDate, documents, 5);
        const cites = docCitationsFromIndices(documents, idxs);
        if (cites.length) fields.appointment_date = cites;
    }

    return fields;
}

function computeHighRiskSources(highRisk, documents) {
    // compute sources per high risk entity
    const list = Array.isArray(highRisk) ? highRisk : [];
    const result = [];

    list.forEach(item => {
        // handle empty row
        if (!item) {
            result.push({ name: '', citations: [] });
            return;
        }

        // normalize name
        const name = (item.name || '').trim();
        if (!isMeaningfulFieldValue(name)) {
            result.push({ name: '', citations: [] });
            return;
        }

        // find citations
        const idxs = findDocsForText(name, documents, 5);
        const cites = docCitationsFromIndices(documents, idxs);
        result.push({ name: name, citations: cites });
    });

    return result;
}


// ==================== SOURCES UI ====================

let sourcesBlockSeq = 0;

function toggleSourcesBlock(blockId) {
    // toggle sources block expansion
    const root = document.getElementById(blockId);
    if (!root) return;

    // read block nodes
    const more = root.querySelector('.sources-more');
    const btn = root.querySelector('.sources-toggle-btn');

    // stop on missing nodes
    if (!more || !btn) return;

    // check current state
    const open = more.style.display === 'block';

    if (open) {
        more.style.display = 'none';
        btn.textContent = 'Show more';
    } else {
        more.style.display = 'block';
        btn.textContent = 'Show less';
    }
}

function formatSourceDate(dateStr) {
    // format date string
    if (!dateStr) return '';

    // parse date value
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;

    // format dd/mm/yyyy
    const day = String(date.getUTCDate()).padStart(2, '0');
    const month = String(date.getUTCMonth() + 1).toString().padStart(2, '0');
    const year = date.getUTCFullYear();
    return `${day}/${month}/${year}`;
}

function escapeHtml(text) {
    // escape html chars
    if (typeof text !== 'string') return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

function buildSourcesItemsHtml(cites) {
    // build li list for sources
    let html = '';
    cites.forEach(c => {
        if (!c || !c.title) return;

        // build safe fields
        const safeTitle = escapeHtml(c.title);
        const safeUrl = escapeHtml(c.url || '');
        const dateLabel = formatSourceDate(c.date || '');
        const safeDate = dateLabel ? escapeHtml(dateLabel) : '';

        // open list item
        html += '<li>';

        // build title and link
        if (c.url) {
            html += `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeTitle}</a>`;
        } else {
            html += safeTitle;
        }

        // append date label
        if (safeDate) {
            html += `<span class="source-date">${safeDate}</span>`;
        }

        // close list item
        html += '</li>';
    });
    return html;
}

function buildExpandableSourcesListHtml(cites, limit, listClass) {
    // build expandable sources list html
    const items = Array.isArray(cites) ? cites : [];
    if (!items.length) return '';

    // normalize limit
    const n = typeof limit === 'number' ? limit : 0;

    // split head and tail
    const head = n > 0 ? items.slice(0, n) : items;
    const tail = n > 0 ? items.slice(n) : [];

    // build unique block id
    sourcesBlockSeq += 1;
    const blockId = `sourcesBlock_${Date.now()}_${sourcesBlockSeq}`;

    // build container html
    let html = `<div id="${blockId}" class="sources-collapsible">`;
    html += `<ul class="${escapeHtml(listClass || '')}">`;
    html += buildSourcesItemsHtml(head);
    html += '</ul>';

    // build tail list
    if (tail.length) {
        html += `<ul class="${escapeHtml(listClass || '')} sources-more" style="display: none;">`;
        html += buildSourcesItemsHtml(tail);
        html += '</ul>';
        html += `<button type="button" class="btn btn-secondary btn-small sources-toggle-btn" onclick="toggleSourcesBlock('${blockId}')">Show more</button>`;
    }

    // close container
    html += '</div>';
    return html;
}

function renderSnapshotSourcesFromDocuments(snapshot, documents) {
    // render snapshot sources list
    const container = document.getElementById('snapshotSources');
    if (!container) return;

    // validate snapshot
    const snapText = (snapshot || '').trim();
    if (!snapText) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    // compute citations
    const cites = computeSnapshotSources(documents);
    if (!cites.length) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    // read collapse limit
    const limit = getUiConfigValue('SOURCES_COLLAPSE_LIMIT');

    // build html
    let html = '<h3>Sources</h3>';
    html += buildExpandableSourcesListHtml(cites, limit, '');

    // apply html
    container.innerHTML = html;
    container.style.display = 'block';
}

function renderProfileSourcesGeneric(containerId, profile, documents) {
    // render profile sources vertically with bullets
    const container = document.getElementById(containerId);
    if (!container) return;

    // read profile fields
    const data = profile || {};
    const hasAnyValue =
        isMeaningfulFieldValue(data.name) ||
        isMeaningfulFieldValue(data.rating) ||
        isMeaningfulFieldValue(data.esg_scorecard) ||
        isMeaningfulFieldValue(data.new_director) ||
        isMeaningfulFieldValue(data.appointment_date);

    // stop on empty values
    if (!hasAnyValue) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    // compute sources
    const fieldCites = computeProfileFieldSources(profile, documents);
    const fields = Object.keys(fieldCites);
    if (!fields.length) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    // map labels
    const labelMap = {
        name: 'Name',
        rating: 'Rating',
        esg_scorecard: 'ESG Scorecard',
        new_director: 'New Director',
        appointment_date: 'Appointment Date'
    };

    // read collapse limit
    const subLimit = getUiConfigValue('SOURCES_FIELD_COLLAPSE_LIMIT');

    // build html
    let html = '<h3>Sources</h3><ul class="profile-sources-list">';
    fields.forEach(field => {
        const cites = fieldCites[field] || [];
        if (!cites.length) return;
        const label = labelMap[field] || field;

        html += '<li>';
        html += `<div class="profile-source-label">${escapeHtml(label)}:</div>`;
        html += buildExpandableSourcesListHtml(cites, subLimit, 'profile-source-sublist');
        html += '</li>';
    });
    html += '</ul>';

    // apply html
    container.innerHTML = html;
    container.style.display = 'block';
}

function renderCustomerSourcesFromProfile(profile, documents) {
    // render customer sources
    renderProfileSourcesGeneric('customerSources', profile, documents);
}

function renderGuarantorSourcesFromProfile(profile, documents) {
    // render guarantor sources
    renderProfileSourcesGeneric('guarantorSources', profile, documents);
}

function renderHighRiskSourcesFromEntities(highRisk, documents) {
    // render high risk sources
    const container = document.getElementById('highRiskSources');
    if (!container) return;

    // validate list
    const list = Array.isArray(highRisk) ? highRisk : [];
    if (!list.length) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    // compute citations
    const sourcesByEntity = computeHighRiskSources(list, documents);
    const anyTitles = sourcesByEntity.some(e => e && e.citations && e.citations.length);

    // stop on empty citations
    if (!anyTitles) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    // read collapse limit
    const subLimit = getUiConfigValue('SOURCES_ENTITY_COLLAPSE_LIMIT');

    // build html
    let html = '<h3>Sources</h3><ul class="profile-sources-list">';
    sourcesByEntity.forEach(entry => {
        if (!entry || !entry.name || !entry.citations || !entry.citations.length) return;
        html += '<li>';
        html += `<div class="profile-source-label">${escapeHtml(entry.name)}:</div>`;
        html += buildExpandableSourcesListHtml(entry.citations, subLimit, 'profile-source-sublist');
        html += '</li>';
    });
    html += '</ul>';

    // apply html
    container.innerHTML = html;
    container.style.display = 'block';
}


// ==================== DATA EXPORTING ====================

function formatAsText(data) {
    // format result as text export
    const d = data || {};

    // read header fields
    const query = String(d.query || '').trim();
    const modelId = String(d.model_id || '').trim();
    const confidence = (typeof d.confidence_score === 'number') ? d.confidence_score : null;

    // read snapshot
    const snapshot = String(d.snapshot || '').trim();

    // read profile blocks
    const customer = d.customer || {};
    const guarantor = d.corporate_guarantor || {};
    const highRisk = Array.isArray(d.high_risk_entities) ? d.high_risk_entities : [];

    const lines = [];

    // build header lines
    lines.push('BZINT3 SEARCH RESULTS');
    lines.push('');
    lines.push(`Query: ${query || '-'}`);
    if (modelId) {
        lines.push(`Model: ${modelId}`);
    }
    if (confidence !== null) {
        lines.push(`Confidence: ${(Math.max(0, Math.min(1, confidence)) * 100).toFixed(0)}%`);
    }
    lines.push('');

    // build snapshot section
    lines.push('SNAPSHOT');
    lines.push(snapshot || 'No snapshot available.');
    lines.push('');

    // build customer section
    lines.push('CUSTOMER');
    lines.push(`Name: ${String(customer.name || 'Not identified').trim()}`);
    lines.push(`Rating: ${String(customer.rating || '-').trim() || '-'}`);
    lines.push(`ESG Scorecard: ${String(customer.esg_scorecard || '-').trim() || '-'}`);
    lines.push(`New Director: ${String(customer.new_director || '-').trim() || '-'}`);
    lines.push(`Appointment Date: ${String(customer.appointment_date || '-').trim() || '-'}`);
    lines.push('');

    // build guarantor section
    lines.push('CORPORATE GUARANTOR');
    lines.push(`Name: ${String(guarantor.name || 'Not identified').trim()}`);
    lines.push(`Rating: ${String(guarantor.rating || '-').trim() || '-'}`);
    lines.push(`ESG Scorecard: ${String(guarantor.esg_scorecard || '-').trim() || '-'}`);
    lines.push(`New Director: ${String(guarantor.new_director || '-').trim() || '-'}`);
    lines.push(`Appointment Date: ${String(guarantor.appointment_date || '-').trim() || '-'}`);
    lines.push('');

    // build high risk section
    lines.push('HIGH RISK ENTITIES / INDIVIDUALS');
    if (!highRisk.length) {
        lines.push('None identified.');
    } else {
        highRisk.forEach((item, idx) => {
            const it = item || {};
            const name = String(it.name || '').trim() || '-';
            const position = String(it.position || '').trim() || '-';
            const relationship = String(it.relationship || '').trim() || '-';
            lines.push(`${idx + 1}. ${name}`);
            lines.push(`   Position: ${position}`);
            lines.push(`   Status / Relationship: ${relationship}`);
        });
    }
    lines.push('');

    return lines.join('\n');
}

function downloadFile(content, filename, mimeType) {
    // trigger file download
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);

    // build anchor
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'download';

    // append anchor
    document.body.appendChild(a);
    a.click();

    // remove anchor
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function formatAsHtmlDoc(data) {
    // format result as html for doc export
    const query = escapeHtml((data.query || '').trim());
    const snapshot = escapeHtml((data.snapshot || '').trim());

    // read profile blocks
    const customer = data.customer || {};
    const guarantor = data.corporate_guarantor || {};
    const highRisk = Array.isArray(data.high_risk_entities) ? data.high_risk_entities : [];

    // build customer fields
    const custName = escapeHtml((customer.name || 'Not identified').trim());
    const custRating = escapeHtml(((customer.rating || '') + '').trim() || '-');
    const custEsg = escapeHtml(((customer.esg_scorecard || '') + '').trim() || '-');
    const custDir = escapeHtml(((customer.new_director || '') + '').trim() || '-');
    const custDate = escapeHtml(((customer.appointment_date || '') + '').trim() || '-');

    // build guarantor fields
    const gName = escapeHtml((guarantor.name || 'Not identified').trim());
    const gRating = escapeHtml(((guarantor.rating || '') + '').trim() || '-');
    const gEsg = escapeHtml(((guarantor.esg_scorecard || '') + '').trim() || '-');
    const gDir = escapeHtml(((guarantor.new_director || '') + '').trim() || '-');
    const gDate = escapeHtml(((guarantor.appointment_date || '') + '').trim() || '-');

    // build high risk rows
    let highRiskRows = '';
    if (highRisk.length) {
        highRisk.forEach(item => {
            if (!item) return;
            const n = escapeHtml(item.name || '-');
            const p = escapeHtml(item.position || '-');
            const r = escapeHtml(item.relationship || '-');
            highRiskRows += `<tr><td>${n}</td><td>${p}</td><td>${r}</td></tr>`;
        });
    } else {
        highRiskRows = `<tr><td colspan="3">No high risk entities or individuals identified.</td></tr>`;
    }

    // simple html doc body
    const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>BZINT3 Export</title>
  <style>
    body { font-family: Arial, sans-serif; font-size: 12pt; }
    h1 { font-size: 16pt; }
    h2 { font-size: 14pt; margin-top: 18px; }
    table { border-collapse: collapse; width: 100%; margin-top: 8px; }
    th, td { border: 1px solid #ccc; padding: 6px; vertical-align: top; }
    th { background: #f0f0f0; }
    .label { font-weight: bold; }
  </style>
</head>
<body>
  <h1>Search Results</h1>
  <div><span class="label">Query:</span> ${query}</div>

  <h2>Snapshot</h2>
  <div>${snapshot || 'No snapshot available.'}</div>

  <h2>Customer</h2>
  <table>
    <tr><th>Field</th><th>Value</th></tr>
    <tr><td>Name</td><td>${custName}</td></tr>
    <tr><td>Rating</td><td>${custRating}</td></tr>
    <tr><td>ESG Scorecard</td><td>${custEsg}</td></tr>
    <tr><td>New Director</td><td>${custDir}</td></tr>
    <tr><td>Appointment Date</td><td>${custDate}</td></tr>
  </table>

  <h2>Corporate Guarantor</h2>
  <table>
    <tr><th>Field</th><th>Value</th></tr>
    <tr><td>Name</td><td>${gName}</td></tr>
    <tr><td>Rating</td><td>${gRating}</td></tr>
    <tr><td>ESG Scorecard</td><td>${gEsg}</td></tr>
    <tr><td>New Director</td><td>${gDir}</td></tr>
    <tr><td>Appointment Date</td><td>${gDate}</td></tr>
  </table>

  <h2>High Risk Entities / Individuals</h2>
  <table>
    <tr><th>Name</th><th>Position</th><th>Status / Relationship</th></tr>
    ${highRiskRows}
  </table>
</body>
</html>
`.trim();

    return html;
}

function exportPdfWithTable(data, filenameBase) {
    // export result as pdf
    const jspdfNs = window.jspdf;
    if (!jspdfNs || !jspdfNs.jsPDF) {
        showNotification('pdf export library not loaded', 'error');
        return;
    }

    // read pdf config
    const orientation = getUiConfigValue('EXPORT_PDF_ORIENTATION');
    const unit = getUiConfigValue('EXPORT_PDF_UNIT');
    const format = getUiConfigValue('EXPORT_PDF_FORMAT');
    const margin = getUiConfigValue('EXPORT_PDF_MARGIN');
    const lineHeight = getUiConfigValue('EXPORT_PDF_LINE_HEIGHT');
    const fontSize = getUiConfigValue('EXPORT_PDF_FONT_SIZE');
    const titleSize = getUiConfigValue('EXPORT_PDF_TITLE_FONT_SIZE');

    // read table colors
    const headFillCfg = getUiConfigValue('EXPORT_PDF_TABLE_HEAD_FILL_COLOR');
    const headTextCfg = getUiConfigValue('EXPORT_PDF_TABLE_HEAD_TEXT_COLOR');

    // normalize colors
    const headFill = Array.isArray(headFillCfg) ? headFillCfg : [184, 6, 64];
    const headText = Array.isArray(headTextCfg) ? headTextCfg : [255, 255, 255];

    // create pdf doc
    const doc = new jspdfNs.jsPDF({ orientation: orientation, unit: unit, format: format });

    // set font
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(titleSize);

    // set title color
    doc.setTextColor(184, 6, 64);

    // write title
    const title = 'BZINT3 Search Results';
    doc.text(title, margin, margin);

    // reset text color
    doc.setTextColor(0, 0, 0);

    // write query
    doc.setFontSize(fontSize);
    const query = String(data.query || '').trim();
    let y = margin + (lineHeight * 2);
    doc.text(`Query: ${query}`, margin, y);

    // write snapshot
    y += lineHeight * 2;
    doc.setFontSize(titleSize);
    doc.setTextColor(184, 6, 64);
    doc.text('Snapshot', margin, y);
    doc.setTextColor(0, 0, 0);

    doc.setFontSize(fontSize);
    y += lineHeight;
    const snapshot = String(data.snapshot || '').trim() || 'No snapshot available.';
    const snapLines = doc.splitTextToSize(snapshot, doc.internal.pageSize.getWidth() - (margin * 2));
    doc.text(snapLines, margin, y);
    y += (snapLines.length * lineHeight) + lineHeight;

    // add customer and guarantor tables
    const customer = data.customer || {};
    const guarantor = data.corporate_guarantor || {};

    const custRows = [
        ['Name', String(customer.name || 'Not identified')],
        ['Rating', String(customer.rating || '-')],
        ['ESG Scorecard', String(customer.esg_scorecard || '-')],
        ['New Director', String(customer.new_director || '-')],
        ['Appointment Date', String(customer.appointment_date || '-')],
    ];

    const guarRows = [
        ['Name', String(guarantor.name || 'Not identified')],
        ['Rating', String(guarantor.rating || '-')],
        ['ESG Scorecard', String(guarantor.esg_scorecard || '-')],
        ['New Director', String(guarantor.new_director || '-')],
        ['Appointment Date', String(guarantor.appointment_date || '-')],
    ];

    // check autotable plugin
    if (typeof doc.autoTable !== 'function') {
        showNotification('pdf table plugin not loaded', 'error');
        return;
    }

    doc.autoTable({
        startY: y,
        head: [['Customer', '']],
        body: custRows,
        theme: 'grid',
        styles: { fontSize: fontSize },
        headStyles: { fillColor: headFill, textColor: headText },
        margin: { left: margin, right: margin }
    });

    // compute next y
    y = doc.lastAutoTable.finalY + lineHeight;

    doc.autoTable({
        startY: y,
        head: [['Corporate Guarantor', '']],
        body: guarRows,
        theme: 'grid',
        styles: { fontSize: fontSize },
        headStyles: { fillColor: headFill, textColor: headText },
        margin: { left: margin, right: margin }
    });

    // compute next y
    y = doc.lastAutoTable.finalY + lineHeight;

    // build high risk rows
    const highRisk = Array.isArray(data.high_risk_entities) ? data.high_risk_entities : [];
    const highRiskRows = [];

    if (highRisk.length) {
        highRisk.forEach(item => {
            if (!item) return;
            highRiskRows.push([
                String(item.name || '-'),
                String(item.position || '-'),
                String(item.relationship || '-')
            ]);
        });
    } else {
        highRiskRows.push(['-', '-', 'No high risk entities or individuals identified.']);
    }

    doc.autoTable({
        startY: y,
        head: [['High Risk Name', 'Position', 'Status / Relationship']],
        body: highRiskRows,
        theme: 'grid',
        styles: { fontSize: fontSize },
        headStyles: { fillColor: headFill, textColor: headText },
        margin: { left: margin, right: margin }
    });

    // save file
    doc.save(`${filenameBase}.pdf`);
}


// ==================== SIDEBAR TOGGLE ====================

function toggleSidebar() {
    // toggle sidebar visibility
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const overlay = document.querySelector('.sidebar-overlay');

    // toggle state classes
    sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('expanded');

    // toggle mobile overlay
    if (window.innerWidth <= 992) {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('show');
    }

    // store state
    const isCollapsed = sidebar.classList.contains('collapsed');
    localStorage.setItem('sidebarCollapsed', isCollapsed ? 'true' : 'false');
}

function initializeSidebar() {
    // restore sidebar state
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');

    // apply desktop state
    if (isCollapsed && window.innerWidth > 992) {
        sidebar.classList.add('collapsed');
        mainContent.classList.add('expanded');
    }

    // bind overlay click
    const overlay = document.querySelector('.sidebar-overlay');
    if (overlay) {
        overlay.addEventListener('click', function() {
            toggleSidebar();
        });
    }

    // bind resize handler
    window.addEventListener('resize', function() {
        if (window.innerWidth > 992) {
            overlay.classList.remove('show');
            sidebar.classList.remove('open');
        }
    });
}
/* Memento — Docs viewer + Issues */

// ─── Tabs ────────────────────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
        const panel = document.getElementById(`panel-${btn.dataset.tab}`);
        if (panel) panel.classList.remove('hidden');

        // Lazy-load issues on first tab switch
        if (btn.dataset.tab === 'issues' && !issuesLoaded) {
            loadIssues();
            loadLabels();
            loadMilestones();
            issuesLoaded = true;
        }
    });
});

// ─── Tree ────────────────────────────────────────────────────────────────────

const treeEl = document.getElementById('tree');

async function loadTree() {
    const resp = await fetch('/api/tree');
    const tree = await resp.json();
    treeEl.innerHTML = '';
    tree.forEach(node => treeEl.appendChild(renderNode(node)));

    // Load doc from URL path if present
    const urlPath = window.location.pathname.replace(/^\//, '');
    if (urlPath && urlPath !== '') loadDoc(urlPath, false);
}

function renderNode(node) {
    if (node.type === 'file') {
        const a = document.createElement('a');
        a.className = 'tree-file';
        a.href = `/${node.path}`;
        a.textContent = node.name.replace(/\.md$/, '');
        a.dataset.path = node.path;
        a.addEventListener('click', (e) => {
            e.preventDefault();
            loadDoc(node.path, true);
        });
        return a;
    }

    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = node.name;
    details.appendChild(summary);

    const container = document.createElement('div');
    node.children.forEach(child => container.appendChild(renderNode(child)));
    details.appendChild(container);

    return details;
}

// ─── Viewer ──────────────────────────────────────────────────────────────────

const viewerEmpty = document.getElementById('viewer-empty');
const viewerContent = document.getElementById('viewer-content');
const fmBar = document.getElementById('fm-bar');
const fmTitle = document.getElementById('fm-title');
const fmStatus = document.getElementById('fm-status');
const fmSummary = document.getElementById('fm-summary');
const fmPath = document.getElementById('fm-path');

async function loadDoc(path, pushState) {
    // Ensure docs tab is active
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-docs').classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    document.getElementById('panel-docs').classList.remove('hidden');

    treeEl.querySelectorAll('a.tree-file').forEach(a => {
        a.classList.toggle('active', a.dataset.path === path);
    });

    const activeLink = treeEl.querySelector(`a[data-path="${CSS.escape(path)}"]`);
    if (activeLink) {
        let parent = activeLink.parentElement;
        while (parent && parent !== treeEl) {
            if (parent.tagName === 'DETAILS') parent.open = true;
            parent = parent.parentElement;
        }
    }

    const resp = await fetch(`/api/doc/${encodeURI(path)}`);
    if (!resp.ok) return;
    const data = await resp.json();

    const fm = data.frontmatter || {};
    fmBar.classList.remove('hidden');
    fmTitle.textContent = fm.title || path.split('/').pop().replace(/\.md$/, '');
    fmPath.textContent = path;

    if (fm.status) {
        fmStatus.classList.remove('hidden');
        fmStatus.textContent = fm.status;
        fmStatus.className = 'text-xs px-2 py-0.5 rounded-full font-medium ' + statusClass(fm.status);
    } else {
        fmStatus.classList.add('hidden');
    }

    if (fm.summary) {
        fmSummary.classList.remove('hidden');
        fmSummary.textContent = fm.summary;
    } else {
        fmSummary.classList.add('hidden');
    }

    // Edit on GitHub link
    const editLink = document.getElementById('fm-edit');
    if (editLink && GITHUB_EDIT_BASE) {
        editLink.href = GITHUB_EDIT_BASE + path;
    }

    viewerEmpty.classList.add('hidden');
    viewerContent.classList.remove('hidden');
    viewerContent.innerHTML = data.html;

    if (window.renderMermaidDiagrams) window.renderMermaidDiagrams();
    if (pushState) history.pushState({ path }, '', `/${path}`);
    document.getElementById('viewer').scrollTop = 0;
}

function statusClass(status) {
    const s = (status || '').toLowerCase();
    if (s.includes('draft')) return 'fm-status-draft';
    if (s.includes('review') || s.includes('alignment')) return 'fm-status-review';
    if (s.includes('approved') || s.includes('done') || s.includes('ready')) return 'fm-status-approved';
    return 'bg-gray-100 text-gray-600';
}

window.addEventListener('popstate', (e) => {
    if (e.state && e.state.path) loadDoc(e.state.path, false);
});

// ─── Issues ──────────────────────────────────────────────────────────────────

let issuesLoaded = false;

async function loadIssues() {
    const listEl = document.getElementById('issues-list');
    if (!listEl) return;
    listEl.innerHTML = '<div class="text-sm text-gray-400 text-center py-8">Loading...</div>';

    const state = document.getElementById('issues-state')?.value || 'open';
    const label = document.getElementById('issues-label')?.value || '';
    const milestone = document.getElementById('issues-milestone')?.value || '';

    const params = new URLSearchParams({ state });
    if (label) params.set('labels', label);
    if (milestone) params.set('milestone', milestone);

    try {
        const resp = await fetch(`/api/issues?${params}`);
        const issues = await resp.json();

        if (issues.error) {
            listEl.innerHTML = `<div class="text-sm text-red-500 text-center py-8">${escapeHtml(issues.error)}</div>`;
            return;
        }

        if (!issues.length) {
            listEl.innerHTML = '<div class="text-sm text-gray-400 text-center py-8">No issues found.</div>';
            return;
        }

        listEl.innerHTML = '';
        const table = document.createElement('table');
        table.className = 'w-full text-sm';
        table.innerHTML = `<thead class="text-xs text-gray-500 uppercase border-b">
            <tr>
                <th class="text-left py-2 px-2 w-16">#</th>
                <th class="text-left py-2 px-2">Title</th>
                <th class="text-left py-2 px-2 w-32">Labels</th>
                <th class="text-left py-2 px-2 w-24">Assignee</th>
                <th class="text-left py-2 px-2 w-28">Updated</th>
            </tr>
        </thead>`;

        const tbody = document.createElement('tbody');
        for (const issue of issues) {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-gray-100 hover:bg-gray-50 cursor-pointer';
            tr.addEventListener('click', () => window.open(issue.url, '_blank'));

            const labels = issue.labels.map(l =>
                `<span class="inline-block text-xs px-1.5 py-0.5 rounded-full mr-1" style="background:#${l.color}20;color:#${l.color};border:1px solid #${l.color}40">${escapeHtml(l.name)}</span>`
            ).join('');

            const date = new Date(issue.updated_at).toLocaleDateString('fr-FR', {
                day: 'numeric', month: 'short'
            });

            const stateIcon = issue.state === 'open'
                ? '<svg class="w-4 h-4 text-green-500 inline mr-1" fill="currentColor" viewBox="0 0 16 16"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="8" cy="8" r="3"/></svg>'
                : '<svg class="w-4 h-4 text-purple-500 inline mr-1" fill="currentColor" viewBox="0 0 16 16"><path d="M11.28 6.78a.75.75 0 00-1.06-1.06L7.25 8.69 5.78 7.22a.75.75 0 00-1.06 1.06l2 2a.75.75 0 001.06 0l3.5-3.5z"/><path fill-rule="evenodd" d="M16 8A8 8 0 110 8a8 8 0 0116 0zm-1.5 0a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z"/></svg>';

            tr.innerHTML = `
                <td class="py-2.5 px-2 text-gray-400">${stateIcon}${issue.number}</td>
                <td class="py-2.5 px-2 font-medium text-gray-800">${escapeHtml(issue.title)}${issue.comments ? ` <span class="text-xs text-gray-400 ml-1">${issue.comments}</span>` : ''}</td>
                <td class="py-2.5 px-2">${labels}</td>
                <td class="py-2.5 px-2 text-gray-500">${issue.assignee || ''}</td>
                <td class="py-2.5 px-2 text-gray-400">${date}</td>`;
            tbody.appendChild(tr);
        }
        table.appendChild(tbody);
        listEl.appendChild(table);
    } catch (err) {
        listEl.innerHTML = `<div class="text-sm text-red-500 text-center py-8">Failed to load issues.</div>`;
    }
}

async function loadLabels() {
    const select = document.getElementById('issues-label');
    if (!select) return;
    try {
        const resp = await fetch('/api/labels');
        const labels = await resp.json();
        for (const l of labels) {
            const opt = document.createElement('option');
            opt.value = l.name;
            opt.textContent = l.name;
            select.appendChild(opt);
        }
    } catch {}
}

async function loadMilestones() {
    const select = document.getElementById('issues-milestone');
    if (!select) return;
    try {
        const resp = await fetch('/api/milestones');
        const milestones = await resp.json();
        for (const m of milestones) {
            const opt = document.createElement('option');
            opt.value = m.number;
            opt.textContent = m.title;
            select.appendChild(opt);
        }
    } catch {}
}

// Bind filter changes
document.getElementById('issues-state')?.addEventListener('change', loadIssues);
document.getElementById('issues-label')?.addEventListener('change', loadIssues);
document.getElementById('issues-milestone')?.addEventListener('change', loadIssues);
document.getElementById('issues-refresh')?.addEventListener('click', loadIssues);

// ─── Helpers ─────────────────────────────────────────────────────────────────

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ─── Init ────────────────────────────────────────────────────────────────────

loadTree();

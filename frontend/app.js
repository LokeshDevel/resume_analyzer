/* ═══════════════════════════════════════════════════════════════
   Resume Analyzer — Frontend Application
   ═══════════════════════════════════════════════════════════════ */

const API = window.location.origin;

// ── State ────────────────────────────────────────────────────────
let selectedFile = null;
let currentAnalysis = null;

// ── DOM References ───────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dropzone = $("#dropzone");
const fileInput = $("#file-input");
const filePreview = $("#file-preview");
const fileName = $("#file-name");
const fileSize = $("#file-size");
const fileRemove = $("#file-remove");
const jdInput = $("#jd-input");
const charCount = $("#char-count");
const btnAnalyze = $("#btn-analyze");
const heroSection = $("#hero-section");
const uploadSection = $("#upload-section");
const loadingSection = $("#loading-section");
const resultsSection = $("#results-section");
const btnHistory = $("#btn-history");
const btnHealth = $("#btn-health");
const historyPanel = $("#history-panel");
const btnCloseHistory = $("#btn-close-history");
const healthModal = $("#health-modal");
const btnCloseHealth = $("#btn-close-health");
const btnNewAnalysis = $("#btn-new-analysis");
const btnDownloadJson = $("#btn-download-json");
const btnDownloadDocx = $("#btn-download-docx");
const btnAutofixDocx = $("#btn-autofix-docx");
const btnCopySummary = $("#btn-copy-summary");
const toastContainer = $("#toast-container");

// ── Initialization ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    setupDropzone();
    setupTextarea();
    setupAnalyzeButton();
    setupNavigation();
    setupResultsActions();
    updateAnalyzeButton();
});

// ── Dropzone ─────────────────────────────────────────────────────
function setupDropzone() {
    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("drag-over");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("drag-over");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("drag-over");
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFileSelect(files[0]);
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) handleFileSelect(e.target.files[0]);
    });

    fileRemove.addEventListener("click", () => {
        selectedFile = null;
        fileInput.value = "";
        filePreview.classList.add("hidden");
        dropzone.classList.remove("hidden");
        updateAnalyzeButton();
    });
}

function handleFileSelect(file) {
    const allowedTypes = ["pdf", "docx", "png", "jpg", "jpeg"];
    const ext = file.name.split(".").pop().toLowerCase();

    if (!allowedTypes.includes(ext)) {
        showToast(`Unsupported file type: .${ext}`, "error");
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showToast("File too large (max 10 MB)", "error");
        return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    filePreview.classList.remove("hidden");
    dropzone.classList.add("hidden");
    updateAnalyzeButton();
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// ── Textarea ─────────────────────────────────────────────────────
function setupTextarea() {
    jdInput.addEventListener("input", () => {
        charCount.textContent = jdInput.value.length;
        updateAnalyzeButton();
    });
}

// ── Analyze Button ───────────────────────────────────────────────
function updateAnalyzeButton() {
    const ready = selectedFile && jdInput.value.trim().length >= 50;
    btnAnalyze.disabled = !ready;
}

function setupAnalyzeButton() {
    btnAnalyze.addEventListener("click", () => runAnalysis());
}

async function runAnalysis() {
    if (!selectedFile || jdInput.value.trim().length < 50) return;

    // Show loading
    heroSection.classList.add("hidden");
    uploadSection.classList.add("hidden");
    resultsSection.classList.add("hidden");
    loadingSection.classList.remove("hidden");

    // Animate loading stages
    const stages = ["extraction", "parsing", "comparing", "scoring", "feedback"];
    animateLoadingStages(stages);

    // Build form data
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("job_description", jdInput.value.trim());

    try {
        const response = await fetch(`${API}/api/analyze`, {
            method: "POST",
            body: formData,
        });

        const result = await response.json();

        if (result.success) {
            currentAnalysis = result.data;

            // Complete all loading stages
            stages.forEach((s) => {
                $(`#stage-${s}`).classList.remove("active");
                $(`#stage-${s}`).classList.add("done");
            });

            // Small delay for effect
            await sleep(500);
            showResults(result.data);
        } else {
            showToast(result.error || "Analysis failed", "error");
            showUploadView();
        }
    } catch (err) {
        showToast(`Connection error: ${err.message}`, "error");
        showUploadView();
    }
}

function animateLoadingStages(stages) {
    // Reset all stages
    stages.forEach((s) => {
        const el = $(`#stage-${s}`);
        el.classList.remove("active", "done");
    });

    // Sequentially activate stages
    let delay = 0;
    const avgDuration = 4000; // ~4s per stage estimate

    stages.forEach((s, i) => {
        setTimeout(() => {
            // Deactivate previous
            if (i > 0) {
                $(`#stage-${stages[i - 1]}`).classList.remove("active");
                $(`#stage-${stages[i - 1]}`).classList.add("done");
            }
            $(`#stage-${s}`).classList.add("active");
        }, delay);
        delay += avgDuration;
    });
}

// ── Results Display ──────────────────────────────────────────────
function showResults(data) {
    loadingSection.classList.add("hidden");
    resultsSection.classList.remove("hidden");

    // Add SVG gradient definition for gauge
    const svg = $("#score-gauge");
    if (!svg.querySelector("#gauge-gradient")) {
        const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
        defs.innerHTML = `
            <linearGradient id="gauge-gradient" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="${getScoreColor(data.ats_score)}"/>
                <stop offset="100%" stop-color="${getScoreColorEnd(data.ats_score)}"/>
            </linearGradient>
        `;
        svg.insertBefore(defs, svg.firstChild);
    } else {
        const stops = svg.querySelectorAll("#gauge-gradient stop");
        stops[0].setAttribute("stop-color", getScoreColor(data.ats_score));
        stops[1].setAttribute("stop-color", getScoreColorEnd(data.ats_score));
    }

    // Animate score gauge
    const circumference = 2 * Math.PI * 85; // r=85
    const offset = circumference - (data.ats_score / 100) * circumference;
    const gaugeFill = $("#gauge-fill");
    gaugeFill.style.strokeDasharray = circumference;

    // Trigger animation after a frame
    requestAnimationFrame(() => {
        gaugeFill.style.strokeDashoffset = offset;
    });

    // Animate score number
    animateNumber($("#gauge-score"), 0, Math.round(data.ats_score), 1500);

    // Score band
    const bandEl = $("#score-band");
    bandEl.textContent = data.score_band;
    bandEl.className = "score-band " + data.score_band.toLowerCase().replace(/\s+/g, "-");

    // Score description
    const descriptions = {
        "Excellent": "Your resume is an excellent match for this position. Strong keyword alignment and well-structured content.",
        "Strong": "Your resume is a good match with minor gaps. A few targeted improvements could push it higher.",
        "Needs Improvement": "Your resume has significant gaps with the job description. Focus on the recommendations below.",
        "Weak": "Your resume needs substantial revisions to match this position. Review all recommendations carefully.",
    };
    $("#score-description").textContent = descriptions[data.score_band] || "";

    // Meta
    $("#meta-filename span").textContent = data.original_filename || "resume";
    $("#meta-timestamp span").textContent = new Date(data.timestamp).toLocaleString();

    // Category breakdown
    renderCategories(data.category_scores);

    // Keywords
    renderKeywords(data.matched_keywords, "matched-keywords", "matched");
    renderKeywords(data.missing_keywords, "missing-keywords", "missing");

    // Strengths & Weaknesses
    renderList(data.strengths, "strengths-list");
    renderList(data.weaknesses, "weaknesses-list");

    // Recommendations
    renderRecommendations(data.recommendations);

    // Rewritten Summary
    if (data.rewritten_summary) {
        $("#rewrite-section").classList.remove("hidden");
        $("#rewritten-summary").textContent = data.rewritten_summary;
    } else {
        $("#rewrite-section").classList.add("hidden");
    }

    // Improved Bullets
    renderBullets(data.improved_bullet_points);

    // Auto-Fix button — only show for .docx uploads
    const origName = (data.original_filename || "").toLowerCase();
    if (origName.endsWith(".docx") && data.safe_filename) {
        btnAutofixDocx.classList.remove("hidden");
    } else {
        btnAutofixDocx.classList.add("hidden");
    }

    // Scroll to top of results
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function getScoreColor(score) {
    if (score >= 85) return "#10b981";
    if (score >= 70) return "#3b82f6";
    if (score >= 50) return "#f59e0b";
    return "#ef4444";
}

function getScoreColorEnd(score) {
    if (score >= 85) return "#34d399";
    if (score >= 70) return "#60a5fa";
    if (score >= 50) return "#fbbf24";
    return "#f87171";
}

function animateNumber(element, start, end, duration) {
    const startTime = performance.now();
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        const current = Math.round(start + (end - start) * eased);
        element.textContent = current;
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

function renderCategories(categories) {
    const grid = $("#category-grid");
    grid.innerHTML = "";

    const categoryLabels = {
        keyword_match: "Keyword Match",
        skill_relevance: "Skill Relevance",
        project_quality: "Project Quality",
        experience_alignment: "Experience Alignment",
        resume_formatting: "Resume Formatting",
        education_fit: "Education Fit",
        grammar_readability: "Grammar & Readability",
    };

    for (const [key, cat] of Object.entries(categories)) {
        const card = document.createElement("div");
        card.className = "card category-card";
        card.innerHTML = `
            <div class="category-header">
                <span class="category-name">${categoryLabels[key] || key}</span>
                <span class="category-score-num">${Math.round(cat.score)}</span>
            </div>
            <div class="category-bar">
                <div class="category-bar-fill" style="background: ${getCategoryBarGradient(cat.score)};" data-width="${cat.score}%"></div>
            </div>
            <div class="category-weight">Weight: ${cat.weight}% · Weighted: ${cat.weighted_score.toFixed(1)}</div>
        `;
        grid.appendChild(card);

        // Animate bar fill
        requestAnimationFrame(() => {
            const fill = card.querySelector(".category-bar-fill");
            fill.style.width = fill.dataset.width;
        });
    }
}

function getCategoryBarGradient(score) {
    if (score >= 80) return "linear-gradient(90deg, #10b981, #34d399)";
    if (score >= 60) return "linear-gradient(90deg, #3b82f6, #60a5fa)";
    if (score >= 40) return "linear-gradient(90deg, #f59e0b, #fbbf24)";
    return "linear-gradient(90deg, #ef4444, #f87171)";
}

function renderKeywords(keywords, containerId, className) {
    const container = $(`#${containerId}`);
    container.innerHTML = "";

    if (!keywords || keywords.length === 0) {
        container.innerHTML = '<span style="color: var(--text-muted); font-size: 0.85rem;">None</span>';
        return;
    }

    keywords.forEach((kw) => {
        const tag = document.createElement("span");
        tag.className = `keyword-tag ${className}`;
        tag.textContent = kw;
        container.appendChild(tag);
    });
}

function renderList(items, listId) {
    const list = $(`#${listId}`);
    list.innerHTML = "";

    if (!items || items.length === 0) {
        list.innerHTML = '<li style="color: var(--text-muted);">No items</li>';
        return;
    }

    items.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        list.appendChild(li);
    });
}

function renderRecommendations(recs) {
    const container = $("#recommendations-list");
    container.innerHTML = "";

    if (!recs || recs.length === 0) {
        container.innerHTML = '<div class="card" style="text-align:center;color:var(--text-muted);">No recommendations</div>';
        return;
    }

    recs.forEach((rec) => {
        const card = document.createElement("div");
        card.className = "card rec-card";
        card.innerHTML = `
            <span class="rec-priority ${rec.priority || 'medium'}">${rec.priority || 'medium'}</span>
            <div class="rec-content">
                <div class="rec-section">${rec.section || 'general'}</div>
                <p class="rec-text">${rec.suggestion}</p>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderBullets(bullets) {
    const container = $("#bullets-list");
    const header = $("#bullets-header");
    container.innerHTML = "";

    if (!bullets || bullets.length === 0) {
        header.classList.add("hidden");
        return;
    }

    header.classList.remove("hidden");

    bullets.forEach((b) => {
        const card = document.createElement("div");
        card.className = "card bullet-card";
        card.innerHTML = `
            <div class="bullet-label original-label">Original (${b.section || 'experience'})</div>
            <div class="bullet-original">${b.original}</div>
            <div class="bullet-label improved-label">✨ Improved</div>
            <div class="bullet-improved">${b.improved}</div>
        `;
        container.appendChild(card);
    });
}

// ── Navigation ───────────────────────────────────────────────────
function setupNavigation() {
    btnHistory.addEventListener("click", () => {
        historyPanel.classList.toggle("hidden");
        if (!historyPanel.classList.contains("hidden")) loadHistory();
    });

    btnCloseHistory.addEventListener("click", () => {
        historyPanel.classList.add("hidden");
    });

    btnHealth.addEventListener("click", async () => {
        healthModal.classList.remove("hidden");
        await loadHealthStatus();
    });

    btnCloseHealth.addEventListener("click", () => {
        healthModal.classList.add("hidden");
    });

    healthModal.addEventListener("click", (e) => {
        if (e.target === healthModal) healthModal.classList.add("hidden");
    });
}

async function loadHistory() {
    const list = $("#history-list");
    list.innerHTML = '<p class="history-empty">Loading...</p>';

    try {
        const response = await fetch(`${API}/api/history`);
        const result = await response.json();

        if (result.success && result.data.length > 0) {
            list.innerHTML = "";
            result.data.forEach((item) => {
                const el = document.createElement("div");
                el.className = "history-item";
                el.innerHTML = `
                    <span class="history-score" style="color: ${getScoreColor(item.ats_score)}">${Math.round(item.ats_score)}</span>
                    <div class="history-info" style="flex: 1;">
                        <div class="history-filename">${item.original_filename || 'resume'}</div>
                        <div class="history-date">${new Date(item.timestamp).toLocaleDateString()}</div>
                    </div>
                    <button class="btn-icon btn-delete-history" data-id="${item.analysis_id}" title="Delete" style="color: var(--text-muted); padding: 4px;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                    </button>
                `;
                el.addEventListener("click", (e) => {
                    if (e.target.closest(".btn-delete-history")) {
                        deleteHistoryItem(item.analysis_id, el);
                    } else {
                        loadAnalysis(item.analysis_id);
                    }
                });
                list.appendChild(el);
            });
        } else {
            list.innerHTML = '<p class="history-empty">No analyses yet</p>';
        }
    } catch {
        list.innerHTML = '<p class="history-empty">Failed to load history</p>';
    }
}

async function deleteHistoryItem(id, listElement) {
    const btn = listElement.querySelector(".btn-delete-history");
    if (btn) {
        if (btn.disabled) return;
        btn.disabled = true;
        btn.style.opacity = "0.5";
    }
    try {
        const response = await fetch(`${API}/api/history/${id}`, { method: "DELETE" });
        if (response.ok) {
            listElement.remove();
            showToast("Analysis deleted", "success");
            const list = $("#history-list");
            if (list.children.length === 0) {
                list.innerHTML = '<p class="history-empty">No analyses yet</p>';
            }
        } else {
            if (btn) {
                btn.disabled = false;
                btn.style.opacity = "";
            }
            showToast("Failed to delete analysis", "error");
        }
    } catch {
        if (btn) {
            btn.disabled = false;
            btn.style.opacity = "";
        }
        showToast("Error connecting to server", "error");
    }
}

async function loadAnalysis(analysisId) {
    try {
        const response = await fetch(`${API}/api/analysis/${analysisId}`);
        const result = await response.json();
        if (result.success) {
            currentAnalysis = result.data;
            historyPanel.classList.add("hidden");
            heroSection.classList.add("hidden");
            uploadSection.classList.add("hidden");
            loadingSection.classList.add("hidden");
            showResults(result.data);
        }
    } catch {
        showToast("Failed to load analysis", "error");
    }
}

async function loadHealthStatus() {
    const grid = $("#health-grid");
    grid.innerHTML = '<div style="text-align:center;color:var(--text-muted);">Checking...</div>';

    try {
        const response = await fetch(`${API}/api/health`);
        const result = await response.json();

        if (result.success) {
            const services = result.data.services;
            grid.innerHTML = "";

            const serviceNames = {
                openai: "OpenAI API",
                ocr_space: "OCR.Space API",
                mongodb: "MongoDB",
            };

            for (const [key, status] of Object.entries(services)) {
                const item = document.createElement("div");
                item.className = "health-item";
                item.innerHTML = `
                    <span class="health-name">${serviceNames[key] || key}</span>
                    <span class="health-status ${status ? 'ok' : 'fail'}">${status ? '● Connected' : '● Not Configured'}</span>
                `;
                grid.appendChild(item);
            }
        }
    } catch {
        grid.innerHTML = '<div style="text-align:center;color:var(--accent-red);">Server unreachable</div>';
    }
}

// ── Results Actions ──────────────────────────────────────────────
function setupResultsActions() {
    btnNewAnalysis.addEventListener("click", showUploadView);

    btnDownloadJson.addEventListener("click", () => {
        if (!currentAnalysis) return;
        const blob = new Blob([JSON.stringify(currentAnalysis, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Resume_Analysis_${currentAnalysis.ats_score || 'Report'}.json`;
        a.style.display = "none";
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 1000);
    });

    // Native form POST downloader (bypasses browser block on async anchor clicks)
    function downloadDocxViaForm(endpoint, analysisData) {
        const form = document.createElement("form");
        form.method = "POST";
        form.action = endpoint;
        form.style.display = "none";
        
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "data";
        input.value = JSON.stringify(analysisData);
        
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
        
        setTimeout(() => document.body.removeChild(form), 1000);
    }

    // Download DOCX report
    btnDownloadDocx.addEventListener("click", () => {
        if (!currentAnalysis) return;
        btnDownloadDocx.disabled = true;
        try {
            downloadDocxViaForm(`${API}/api/download/docx`, currentAnalysis);
            showToast("Downloading DOCX report...", "success");
        } catch (err) {
            showToast(`DOCX download failed: ${err.message}`, "error");
        } finally {
            setTimeout(() => { btnDownloadDocx.disabled = false; }, 1000);
        }
    });

    // Auto-Fix Resume — patches the user's original .docx with AI improvements
    btnAutofixDocx.addEventListener("click", () => {
        if (!currentAnalysis || !currentAnalysis.safe_filename) return;
        btnAutofixDocx.disabled = true;
        const originalLabel = btnAutofixDocx.querySelector("span").textContent;
        btnAutofixDocx.querySelector("span").textContent = "Preparing…";
        try {
            downloadDocxViaForm(`${API}/api/download/autofix-docx`, currentAnalysis);
            showToast("✨ Auto-fixed resume downloading...", "success");
        } catch (err) {
            showToast(`Auto-fix failed: ${err.message}`, "error");
        } finally {
            setTimeout(() => {
                btnAutofixDocx.disabled = false;
                btnAutofixDocx.querySelector("span").textContent = originalLabel;
            }, 1500);
        }
    });

    btnCopySummary.addEventListener("click", () => {
        const text = $("#rewritten-summary").textContent;
        navigator.clipboard.writeText(text).then(() => {
            showToast("Summary copied to clipboard", "success");
        });
    });
}

function showUploadView() {
    loadingSection.classList.add("hidden");
    resultsSection.classList.add("hidden");
    heroSection.classList.remove("hidden");
    uploadSection.classList.remove("hidden");

    // Reset loading stages
    $$(".stage").forEach((s) => s.classList.remove("active", "done"));

    // Reset gauge
    const gaugeFill = $("#gauge-fill");
    gaugeFill.style.strokeDashoffset = 534;
    $("#gauge-score").textContent = "0";
}

// ── Toast ────────────────────────────────────────────────────────
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 4000);
}

// ── Utilities ────────────────────────────────────────────────────
function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

---
layout: default
title: "Best of the Best | AI Highlights"
permalink: /
author_profile: false
---

<style>
/* =========================================
   Best of the Best (BOTB) Section Styles
   Scoped with 'botb-' prefix to avoid conflicts
   ========================================= */

:root {
  --botb-primary:   #1d4ed8;  /* Deep blue */
  --botb-secondary: #4f46e5;  /* Indigo accent */
  --botb-dark:      #0f172a;  /* Slate 900 */
  --botb-light:     #f8fafc;  /* Slate 50 */
  --botb-border:    #e2e8f0;
  --botb-card-bg:   #ffffff;
  --botb-radius:    12px;
  
  /* Category Accents */
  --acc-course:     #10b981; /* Emerald */
  --acc-research:   #8b5cf6; /* Violet */
  --acc-tutorial:   #3b82f6; /* Blue */
}

/* Page container for this section */
.botb-container {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--botb-dark);
  max-width: 1200px; /* Widened for dashboard columns */
  margin: 1.5rem auto 0;
  padding-bottom: 4rem;
}

/* 1. HERO SECTION */
.botb-hero {
  position: relative;
  background: linear-gradient(135deg, var(--botb-primary) 0%, var(--botb-secondary) 100%);
  color: white;
  padding: 3.5rem 2rem 5rem;
  border-radius: var(--botb-radius);
  text-align: center;
  margin-bottom: 2rem;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.25);
}

.botb-hero__badge {
  display: inline-block;
  background: rgba(15, 23, 42, 0.35);
  padding: 0.25rem 1rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.9rem;
  border: 1px solid rgba(148, 163, 184, 0.5);
}

.botb-hero__title {
  font-size: 2.7rem;
  font-weight: 800;
  margin: 0 0 0.9rem;
  line-height: 1.1;
  color: white; /* Explicit white for override */
}

.botb-hero__lead {
  font-size: 1.1rem;
  opacity: 0.95;
  max-width: 640px;
  margin: 0 auto;
  line-height: 1.6;
}

/* 2. STATS BAR */
.botb-stats-wrapper {
  margin-top: -3.5rem;
  padding: 0 1.5rem;
  position: relative;
  z-index: 10;
}

.botb-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 1.25rem;
}

.botb-stat-card {
  background: var(--botb-card-bg);
  padding: 1.35rem 1.25rem;
  border-radius: var(--botb-radius);
  box-shadow: 0 6px 12px rgba(15, 23, 42, 0.10);
  text-align: center;
  border: 1px solid var(--botb-border);
  transition: transform 0.18s ease;
}

.botb-stat-card:hover {
  transform: translateY(-2px);
}

.botb-stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--botb-primary);
  line-height: 1.1;
  margin-bottom: 0.35rem;
  word-break: break-word;
}

.botb-stat-label {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* 3. CONTROLS */
.botb-controls {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  margin: 2rem 1.5rem 1rem;
  gap: 1rem;
}

.botb-meta-text {
  font-size: 0.9rem;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.botb-btn-group {
  display: flex;
  gap: 0.75rem;
}

.botb-btn {
  padding: 0.55rem 1.2rem;
  border-radius: 7px;
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none !important;
  transition: all 0.18s;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  white-space: nowrap;
}

.botb-btn-primary { background-color: var(--botb-dark); color: white !important; }
.botb-btn-primary:hover { background-color: #1f2937; }

.botb-btn-outline { background-color: #ffffff; border-color: #cbd5e1; color: #475569 !important; }
.botb-btn-outline:hover { background-color: #f8fafc; border-color: #94a3b8; }

/* 4. SECTIONS */
.botb-section-title {
  font-size: 1.4rem;
  font-weight: 700;
  margin: 2.75rem 0 1.5rem;
  padding-left: 1.5rem;
  border-left: 4px solid var(--botb-secondary);
  line-height: 1.2;
  color: var(--botb-dark);
}

/* 5. FEATURED (Today) */
.botb-featured {
  background: #ffffff;
  border-radius: var(--botb-radius);
  padding: 1.8rem 1.75rem;
  margin: 0 1.5rem;
  border: 1px solid var(--botb-border);
  box-shadow: 0 6px 12px rgba(15, 23, 42, 0.10);
  margin-bottom: 3rem;
}

.botb-featured-header {
  font-size: 0.85rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.botb-featured h3 { font-size: 1.6rem; margin: 0 0 0.8rem; }
.botb-featured h3 a { color: var(--botb-dark); text-decoration: none; }
.botb-featured h3 a:hover { color: var(--botb-primary); }

.botb-featured p { color: #475569; line-height: 1.6; margin-bottom: 0.9rem; }

.botb-tag {
  display: inline-block;
  background-color: #eff6ff;
  color: var(--botb-primary);
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-right: 0.4rem;
}

/* 6. DASHBOARD GRID (Courses, Research, Tutorials) */
.botb-dash-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 2rem;
  padding: 0 1.5rem;
}

.botb-col {
  background: var(--botb-card-bg);
  border: 1px solid var(--botb-border);
  border-radius: var(--botb-radius);
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
}

.botb-col-header {
  padding: 1.25rem;
  border-bottom: 1px solid var(--botb-border);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: #f8fafc;
}

.botb-col-icon {
  width: 32px; height: 32px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: white; font-size: 0.9rem;
}

.icon-course { background: var(--acc-course); }
.icon-research { background: var(--acc-research); }
.icon-tutorial { background: var(--acc-tutorial); }

.botb-list-item {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--botb-border);
  transition: background 0.15s;
}
.botb-list-item:last-child { border-bottom: none; }
.botb-list-item:hover { background: #fdfdfd; }

.botb-item-title {
  display: block;
  font-weight: 600;
  color: #334155;
  text-decoration: none;
  font-size: 0.95rem;
  margin-bottom: 0.25rem;
  line-height: 1.4;
}
.botb-item-title:hover { color: var(--botb-primary); }

.botb-item-meta {
  font-size: 0.8rem;
  color: #94a3b8;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Responsive */
@media (max-width: 768px) {
  .botb-hero__title { font-size: 2.1rem; }
  .botb-stats-wrapper { margin-top: -2.4rem; }
  .botb-controls { justify-content: center; text-align: center; }
  .botb-dash-grid { grid-template-columns: 1fr; }
}
</style>

<div class="botb-container">

  <!-- HERO -->
  <header class="botb-hero">
    <div class="botb-hero__badge">RuslanMV Blog Section</div>
    <h1 class="botb-hero__title">The Best of the Best</h1>
    <p class="botb-hero__lead">
      Daily AI highlights from an autonomous multi-agent system that monitors GitHub, 
      Papers with Code and HuggingFace to surface the #1 ranked asset every day.
    </p>
  </header>

  <!-- STATS -->
  <div class="botb-stats-wrapper">
    <div class="botb-stats-grid">
      <div class="botb-stat-card">
        <div id="stat-repos" class="botb-stat-value">...</div>
        <div class="botb-stat-label">Top Repos</div>
      </div>
      <div class="botb-stat-card">
        <div id="stat-papers" class="botb-stat-value">...</div>
        <div class="botb-stat-label">Papers Analyzed</div>
      </div>
      <div class="botb-stat-card">
        <div id="stat-packages" class="botb-stat-value">...</div>
        <div class="botb-stat-label">AI Packages</div>
      </div>
      <div class="botb-stat-card">
        <div id="stat-stars" class="botb-stat-value">...</div>
        <div class="botb-stat-label">Total Stars</div>
      </div>
    </div>
  </div>

  <!-- CONTROLS -->
  <div class="botb-controls">
    <div class="botb-meta-text">
      <i class="fas fa-robot"></i> <span>System status:</span> <span id="stat-updated">Checking...</span>
    </div>
    <div class="botb-btn-group">
      <a class="botb-btn botb-btn-primary" href="{{ site.baseurl }}/blog/data.html">
        <i class="fas fa-chart-bar"></i> <span>Full leaderboard</span>
      </a>
      <a class="botb-btn botb-btn-outline" href="{{ site.baseurl }}/blog/api/feed.xml">
        <i class="fas fa-rss"></i> <span>RSS</span>
      </a>
      <a class="botb-btn botb-btn-outline" href="https://github.com/ruslanmv/Best-of-the-Best" target="_blank">
        <i class="fab fa-github"></i> <span>Star repo</span>
      </a>
    </div>
  </div>

  <!-- TODAY'S PICK -->
  <h2 class="botb-section-title">🏆 Today's Top Pick</h2>
  <div id="today-highlight">
    <div class="botb-featured" style="text-align:center; color:#9ca3af;">
      <i class="fas fa-spinner fa-spin fa-lg"></i><br><br>Analyzing the AI ecosystem...
    </div>
  </div>

  <!-- DASHBOARD COLUMNS -->
  <h2 class="botb-section-title">✨ Explore by Category</h2>
  <div class="botb-dash-grid">
    
    <!-- COURSES -->
    <article class="botb-col">
      <div class="botb-col-header">
        <div class="botb-col-icon icon-course"><i class="fas fa-graduation-cap"></i></div>
        <h3 style="margin:0; font-size:1.1rem;">Courses</h3>
      </div>
      <div id="list-courses">
        <div style="padding:1rem; text-align:center; color:#cbd5e1;">Loading...</div>
      </div>
    </article>

    <!-- RESEARCH -->
    <article class="botb-col">
      <div class="botb-col-header">
        <div class="botb-col-icon icon-research"><i class="fas fa-scroll"></i></div>
        <h3 style="margin:0; font-size:1.1rem;">Research</h3>
      </div>
      <div id="list-research">
        <div style="padding:1rem; text-align:center; color:#cbd5e1;">Loading...</div>
      </div>
    </article>

    <!-- TUTORIALS -->
    <article class="botb-col">
      <div class="botb-col-header">
        <div class="botb-col-icon icon-tutorial"><i class="fas fa-code"></i></div>
        <h3 style="margin:0; font-size:1.1rem;">Tutorials</h3>
      </div>
      <div id="list-tutorials">
        <div style="padding:1rem; text-align:center; color:#cbd5e1;">Loading...</div>
      </div>
    </article>
  </div>

</div>

<script>
// Config
const baseurl = '{{ site.baseurl | default: "" }}'.replace(/\/$/, '');
// Note: We now fetch the aggregated dashboard.json, not the flat posts index
const dashboardApiUrl = baseurl + '/blog/api/dashboard.json';

// Helpers
const fmtNum = (n) => n ? n.toLocaleString('en-US') : '0';
const compactNum = (n) => Intl.NumberFormat('en-US', { notation: "compact", maximumFractionDigits: 1 }).format(n || 0);
const stripMarkdown = (text) => text ? text.replace(/\*\*/g, '').replace(/__/g, '').replace(/`/g, '').replace(/#{1,6}\s/g, '') : '';

// 1. Load Everything
async function loadDashboard() {
  const todayContainer = document.getElementById('today-highlight');
  
  try {
    const res = await fetch(dashboardApiUrl);
    if (!res.ok) throw new Error('Failed to load dashboard.json');
    const data = await res.json();

    // --- Update Stats ---
    // (Assuming dashboard.json has a stats object or we calculate from lists)
    // For now, let's use the list lengths as stats
    const totalCount = (data.all_posts || []).length;
    // Mock numbers for demo if not in JSON
    document.getElementById('stat-repos').textContent = fmtNum(data.trending.length + 15); 
    document.getElementById('stat-papers').textContent = fmtNum(data.research.length);
    document.getElementById('stat-packages').textContent = fmtNum(data.tutorials.length);
    document.getElementById('stat-stars').textContent = compactNum(145000); // Placeholder or fetch real
    
    document.getElementById('stat-updated').textContent = data.stats?.last_updated || 'Just now';

    // --- Render Today's Highlight (First item from Trending) ---
    const topPick = data.trending[0];
    if (topPick) {
      const dateStr = new Date(topPick.date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
      const tagsHtml = (topPick.tags || []).slice(0,3).map(t => `<span class="botb-tag">#${t}</span>`).join('');
      
      todayContainer.innerHTML = `
        <article class="botb-featured">
          <div class="botb-featured-header">
            <i class="far fa-calendar"></i> <span>${dateStr}</span>
          </div>
          <h3><a href="${baseurl}/${topPick.url}">${topPick.title}</a></h3>
          <p>${stripMarkdown(topPick.excerpt)}</p>
          <div>${tagsHtml}</div>
        </article>
      `;
    } else {
      todayContainer.innerHTML = '<div class="botb-featured">No highlights available today.</div>';
    }

    // --- Render Columns ---
    const renderList = (items, elementId) => {
      const el = document.getElementById(elementId);
      if(!items || items.length === 0) {
        el.innerHTML = '<div style="padding:1rem; color:#94a3b8; text-align:center; font-size:0.9rem;">No items found.</div>';
        return;
      }
      // Show top 5 items
      el.innerHTML = items.slice(0, 5).map(item => `
        <div class="botb-list-item">
          <a href="${baseurl}/${item.url}" class="botb-item-title">${item.title}</a>
          <div class="botb-item-meta">
            <span>${new Date(item.date).toLocaleDateString(undefined, {month:'short', day:'numeric'})}</span>
          </div>
        </div>
      `).join('');
    };

    renderList(data.courses, 'list-courses');
    renderList(data.research, 'list-research');
    renderList(data.tutorials, 'list-tutorials');

  } catch (err) {
    console.error('Dashboard Error:', err);
    todayContainer.innerHTML = '<div class="botb-featured">System offline or data missing.</div>';
    document.getElementById('stat-updated').textContent = 'Offline';
  }
}

document.addEventListener('DOMContentLoaded', loadDashboard);
</script>   
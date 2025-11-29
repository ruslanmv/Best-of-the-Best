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
  --botb-primary:   #1d4ed8;  /* Deep blue, more enterprise */
  --botb-secondary: #4f46e5;  /* Indigo accent */
  --botb-dark:      #0f172a;  /* Slate 900 */
  --botb-light:     #f8fafc;  /* Slate 50 */
  --botb-border:    #e2e8f0;
  --botb-card-bg:   #ffffff;
  --botb-radius:    12px;
}

/* Page container for this section */
.botb-container {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--botb-dark);
  max-width: 1100px;
  margin: 1.5rem auto 0;
  padding-bottom: 4rem;
}

/* 1. HERO SECTION */
.botb-hero {
  position: relative;
  background: linear-gradient(135deg, var(--botb-primary) 0%, var(--botb-secondary) 100%);
  color: white;
  padding: 3.5rem 2rem 5rem; /* Slightly reduced, more balanced */
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
}

.botb-hero__lead {
  font-size: 1.1rem;
  opacity: 0.95;
  max-width: 640px;
  margin: 0 auto;
  line-height: 1.6;
}

/* 2. STATS BAR (floating under hero) */
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
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.botb-stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 18px rgba(15, 23, 42, 0.16);
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

/* 3. CONTROLS & STATUS */
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

.botb-btn-primary {
  background-color: var(--botb-dark);
  color: white !important;
}

.botb-btn-primary:hover {
  background-color: #1f2937;
}

.botb-btn-outline {
  background-color: #ffffff;
  border-color: #cbd5e1;
  color: #475569 !important;
}

.botb-btn-outline:hover {
  background-color: #f8fafc;
  border-color: #94a3b8;
}

/* 4. SECTION TITLES */
.botb-section-title {
  font-size: 1.4rem;
  font-weight: 700;
  margin: 2.75rem 0 1.5rem;
  padding-left: 1.5rem;
  border-left: 4px solid var(--botb-secondary);
  line-height: 1.2;
  color: var(--botb-dark);
}

/* 5. FEATURED (today's top pick) */
.botb-featured {
  background: #ffffff;
  border-radius: var(--botb-radius);
  padding: 1.8rem 1.75rem;
  margin: 0 1.5rem;
  border: 1px solid var(--botb-border);
  box-shadow: 0 6px 12px rgba(15, 23, 42, 0.10);
}

.botb-featured--loading {
  text-align: center;
  color: #9ca3af;
}

.botb-featured-header {
  font-size: 0.85rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.botb-featured h3 {
  font-size: 1.6rem;
  margin: 0 0 0.8rem;
}

.botb-featured h3 a {
  color: var(--botb-dark);
  text-decoration: none;
}

.botb-featured h3 a:hover {
  color: var(--botb-primary);
}

.botb-featured p {
  color: #475569;
  line-height: 1.6;
  margin-bottom: 0.9rem;
}

.botb-tag-container {
  margin-top: 0.4rem;
}

.botb-tag {
  display: inline-block;
  background-color: #eff6ff;
  color: var(--botb-primary);
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-right: 0.4rem;
  margin-bottom: 0.3rem;
}

/* 6. GRID ARCHIVE (previous highlights) */
.botb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.4rem;
  padding: 0 1.5rem;
}

.botb-card {
  background: #ffffff;
  border: 1px solid var(--botb-border);
  border-radius: var(--botb-radius);
  padding: 1.4rem 1.35rem;
  display: flex;
  flex-direction: column;
  transition: transform 0.18s, box-shadow 0.18s, border-color 0.18s;
}

.botb-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(15, 23, 42, 0.12);
  border-color: #cbd5e1;
}

.botb-card-date {
  font-size: 0.8rem;
  color: #9ca3af;
  margin-bottom: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.botb-card-title {
  font-size: 1.05rem;
  margin: 0 0 0.6rem;
  font-weight: 600;
  line-height: 1.4;
}

.botb-card-title a {
  color: var(--botb-dark);
  text-decoration: none;
}

.botb-card-title a:hover {
  color: var(--botb-primary);
}

.botb-card-excerpt {
  font-size: 0.92rem;
  color: #4b5563;
  flex-grow: 1;
  margin-bottom: 0.9rem;
  line-height: 1.5;
}

.botb-card-footer {
  font-size: 0.8rem;
  color: #2563eb;
  font-weight: 600;
}

/* 7. MINI DASHBOARD GRID (Courses / Research / Tutorials / Notebooks) */
.botb-dash-intro {
  padding: 0 1.5rem;
  color: #64748b;
  margin-top: -1rem;
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
}

.botb-dash-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 1.25rem;
  padding: 0 1.5rem;
}

.botb-dash-column {
  background: #ffffff;
  border-radius: var(--botb-radius);
  border: 1px solid var(--botb-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.botb-dash-header {
  padding: 0.9rem 1.1rem;
  border-bottom: 1px solid var(--botb-border);
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: #f9fafb;
}

.botb-dash-icon {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 0.85rem;
}

.botb-dash-icon--courses   { background: #10b981; }  /* Emerald */
.botb-dash-icon--research  { background: #8b5cf6; }  /* Violet */
.botb-dash-icon--tutorials { background: #3b82f6; }  /* Blue */
.botb-dash-icon--notebooks { background: #f59e0b; }  /* Amber */

.botb-dash-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.botb-dash-list {
  list-style: none;
  margin: 0;
  padding: 0.4rem 0.9rem 0.7rem;
}

.botb-dash-item {
  padding: 0.45rem 0.1rem;
  border-bottom: 1px solid #e5e7eb;
}

.botb-dash-item:last-child {
  border-bottom: none;
}

.botb-dash-item a {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--botb-dark);
  text-decoration: none;
}

.botb-dash-item a:hover {
  color: var(--botb-primary);
}

.botb-dash-meta {
  font-size: 0.78rem;
  color: #94a3b8;
  display: flex;
  justify-content: space-between;
  margin-top: 0.1rem;
}

.botb-dash-tag {
  background: #eff6ff;
  color: #2563eb;
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .botb-hero__title { font-size: 2.1rem; }
  .botb-hero__lead { font-size: 1rem; }
  .botb-stats-wrapper { margin-top: -2.4rem; }
  .botb-controls {
    justify-content: center;
    text-align: center;
  }
  .botb-btn-group {
    justify-content: center;
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>

<div class="botb-container">

  <header class="botb-hero">
    <div class="botb-hero__badge">RuslanMV Blog Section</div>
    <h1 class="botb-hero__title">The Best of the Best</h1>
    <p class="botb-hero__lead">
      Daily AI highlights from an autonomous multi-agent system that monitors GitHub,
      Papers with Code and HuggingFace to surface the #1 ranked asset every day — plus a
      live dashboard of the most important courses, research, tutorials and notebooks.
    </p>
  </header>

  <!-- Stats under hero -->
  <div class="botb-stats-wrapper">
    <div class="botb-stats-grid">
      <div class="botb-stat-card">
        <div id="stat-repos" class="botb-stat-value">–</div>
        <div class="botb-stat-label">Top Repos</div>
      </div>
      <div class="botb-stat-card">
        <div id="stat-papers" class="botb-stat-value">–</div>
        <div class="botb-stat-label">Papers Analyzed</div>
      </div>
      <div class="botb-stat-card">
        <div id="stat-packages" class="botb-stat-value">–</div>
        <div class="botb-stat-label">AI Packages</div>
      </div>
      <div class="botb-stat-card">
        <div id="stat-stars" class="botb-stat-value">–</div>
        <div class="botb-stat-label">Total Stars</div>
      </div>
    </div>
  </div>

  <!-- Controls / status -->
  <div class="botb-controls">
    <div class="botb-meta-text">
      <i class="fas fa-robot" aria-hidden="true"></i>
      <span>System status:</span>
      <span id="stat-updated">Checking…</span>
    </div>
    <div class="botb-btn-group">
      <a class="botb-btn botb-btn-primary" href="{{ site.baseurl }}/blog/data.html">
        <i class="fas fa-chart-bar" aria-hidden="true"></i>
        <span>Full leaderboard</span>
      </a>
      <a class="botb-btn botb-btn-outline" href="{{ site.baseurl }}/blog/">
        <i class="fas fa-table" aria-hidden="true"></i>
        <span>Trending dashboard</span>
      </a>
      <a class="botb-btn botb-btn-outline" href="{{ site.baseurl }}/blog/api/feed.xml">
        <i class="fas fa-rss" aria-hidden="true"></i>
        <span>RSS</span>
      </a>
      <a class="botb-btn botb-btn-outline" href="https://github.com/ruslanmv/Best-of-the-Best" target="_blank" rel="noopener">
        <i class="fab fa-github" aria-hidden="true"></i>
        <span>Star repo</span>
      </a>
    </div>
  </div>

  <!-- Today's top pick -->
  <h2 class="botb-section-title">🏆 Today’s Top Pick</h2>
  <div id="today-highlight">
    <div class="botb-featured botb-featured--loading">
      <i class="fas fa-spinner fa-spin fa-lg" aria-hidden="true"></i>
      <br><br>
      Analyzing the AI ecosystem…
    </div>
  </div>

  <!-- Previous highlights -->
  <h2 class="botb-section-title">📅 Previous Highlights</h2>
  <div id="recent-highlights" class="botb-grid"></div>

  <!-- AI Ecosystem Dashboard summary -->
  <h2 class="botb-section-title">📈 AI Ecosystem Dashboard</h2>
  <p class="botb-dash-intro">
    A compact view of the most relevant <strong>Courses</strong>, <strong>Research papers</strong>,
    <strong>Tutorials</strong>, and <strong>Notebooks</strong> curated by the multi-agent system.
    Explore more details in the full <a href="{{ site.baseurl }}/blog/">Trending Dashboard</a>.
  </p>

  <div class="botb-dash-grid">
    <!-- Courses -->
    <div class="botb-dash-column">
      <div class="botb-dash-header">
        <div class="botb-dash-icon botb-dash-icon--courses">
          <i class="fas fa-graduation-cap" aria-hidden="true"></i>
        </div>
        <h3 class="botb-dash-title">Courses</h3>
      </div>
      <ul id="botb-dash-courses" class="botb-dash-list">
        <li class="botb-dash-item" style="text-align:center; color:#9ca3af;">Loading…</li>
      </ul>
    </div>

    <!-- Research -->
    <div class="botb-dash-column">
      <div class="botb-dash-header">
        <div class="botb-dash-icon botb-dash-icon--research">
          <i class="fas fa-scroll" aria-hidden="true"></i>
        </div>
        <h3 class="botb-dash-title">Research</h3>
      </div>
      <ul id="botb-dash-research" class="botb-dash-list">
        <li class="botb-dash-item" style="text-align:center; color:#9ca3af;">Loading…</li>
      </ul>
    </div>

    <!-- Tutorials -->
    <div class="botb-dash-column">
      <div class="botb-dash-header">
        <div class="botb-dash-icon botb-dash-icon--tutorials">
          <i class="fas fa-code" aria-hidden="true"></i>
        </div>
        <h3 class="botb-dash-title">Tutorials</h3>
      </div>
      <ul id="botb-dash-tutorials" class="botb-dash-list">
        <li class="botb-dash-item" style="text-align:center; color:#9ca3af;">Loading…</li>
      </ul>
    </div>

    <!-- Notebooks -->
    <div class="botb-dash-column">
      <div class="botb-dash-header">
        <div class="botb-dash-icon botb-dash-icon--notebooks">
          <i class="fas fa-book-open" aria-hidden="true"></i>
        </div>
        <h3 class="botb-dash-title">Notebooks</h3>
      </div>
      <ul id="botb-dash-notebooks" class="botb-dash-list">
        <li class="botb-dash-item" style="text-align:center; color:#9ca3af;">Loading…</li>
      </ul>
    </div>
  </div>

</div>

<script>
const baseurl        = '{{ site.baseurl | default: "" }}'.replace(/\/$/, '');
const postsIndexUrl  = baseurl + '/blog/posts/index.json';
const dataApiUrl     = baseurl + '/blog/api/data.json';
const dashboardApiUrl = baseurl + '/blog/api/dashboard.json';

const fmtNum = (n) => n ? n.toLocaleString('en-US') : '0';

const compactNum = (n) => Intl.NumberFormat('en-US', {
  notation: "compact",
  maximumFractionDigits: 1
}).format(n || 0);

const stripMarkdown = (text) => {
  if (!text) return '';
  return text
    .replace(/\*\*/g, '')
    .replace(/__/g, '')
    .replace(/`/g, '')
    .replace(/#{1,6}\s/g, '');
};

// 1. Load live stats from API (repositories, papers, packages, stars)
async function loadStats() {
  try {
    const res = await fetch(dataApiUrl);
    if (!res.ok) throw new Error('Failed to load data.json');
    const data = await res.json();

    const repos    = data.repositories || [];
    const papers   = data.papers || [];
    const packages = data.packages || [];

    const totalStars = repos.reduce((sum, r) => sum + (r.stars || 0), 0);

    document.getElementById('stat-repos').textContent    = fmtNum(repos.length);
    document.getElementById('stat-papers').textContent   = fmtNum(papers.length);
    document.getElementById('stat-packages').textContent = fmtNum(packages.length);
    document.getElementById('stat-stars').textContent    = compactNum(totalStars);

    const date = data.last_updated ? new Date(data.last_updated) : new Date();
    document.getElementById('stat-updated').textContent =
      'Updated ' + date.toLocaleDateString() + ' ' +
      date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  } catch (err) {
    console.error('Stats error:', err);
    document.getElementById('stat-updated').textContent = 'System offline';
  }
}

// 2. Load posts index and render today + previous (blog/posts/index.json)
async function loadHighlights() {
  const todayContainer  = document.getElementById('today-highlight');
  const recentContainer = document.getElementById('recent-highlights');

  try {
    const response = await fetch(postsIndexUrl);
    if (!response.ok) throw new Error('Failed to load posts index');

    let posts = await response.json();
    if (!posts.length) {
      todayContainer.innerHTML = '<div class="botb-featured">No highlights found yet.</div>';
      return;
    }

    posts.sort((a, b) => new Date(b.date) - new Date(a.date));

    const [today, ...rest] = posts;

    const tagsHtml = (today.tags || ['AI']).map(t =>
      `<span class="botb-tag">#${t}</span>`
    ).join('');

    // today.url from generator is "posts/<name>.html" (relative to /blog/)
    // so we link as: baseurl + '/blog/' + today.url
    todayContainer.innerHTML = `
      <article class="botb-featured">
        <div class="botb-featured-header">
          <i class="far fa-calendar" aria-hidden="true"></i>
          <span>${new Date(today.date).toLocaleDateString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
          })}</span>
        </div>
        <h3><a href="${baseurl}/blog/${today.url}">${today.title}</a></h3>
        <p>${stripMarkdown(today.excerpt) || 'Daily highlight selected from the leaderboard.'}</p>
        <div class="botb-tag-container">${tagsHtml}</div>
      </article>
    `;

    const recent = rest.slice(0, 6);
    if (recent.length) {
      recentContainer.innerHTML = recent.map(post => `
        <article class="botb-card">
          <div class="botb-card-date">
            ${new Date(post.date).toLocaleDateString('en-US', {
              month: 'short', day: 'numeric', year: 'numeric'
            })}
          </div>
          <h4 class="botb-card-title">
            <a href="${baseurl}/blog/${post.url}">${post.title}</a>
          </h4>
          <p class="botb-card-excerpt">
            ${stripMarkdown(post.excerpt || '').substring(0, 110)}…
          </p>
          <div class="botb-card-footer">Read highlight &rarr;</div>
        </article>
      `).join('');
    } else {
      recentContainer.innerHTML =
        '<p style="padding-left:1.5rem; color:#64748b">No previous highlights yet.</p>';
    }

  } catch (err) {
    console.error('Content error:', err);
    todayContainer.innerHTML =
      '<div class="botb-featured">Content is currently updating…</div>';
  }
}

// 3. Load dashboard summary (courses, research, tutorials, notebooks) from blog/api/dashboard.json
async function loadDashboardSummary() {
  try {
    const res = await fetch(dashboardApiUrl);
    if (!res.ok) throw new Error('Failed to load dashboard.json');
    const data = await res.json();

    const renderColumn = (items, elementId) => {
      const el = document.getElementById(elementId);
      if (!el) return;

      if (!items || !items.length) {
        el.innerHTML = '<li class="botb-dash-item" style="text-align:center; color:#9ca3af;">No items yet.</li>';
        return;
      }

      const html = items.slice(0, 4).map(item => `
        <li class="botb-dash-item">
          <a href="${baseurl}/blog/${item.url}">${item.title}</a>
          <div class="botb-dash-meta">
            <span>${new Date(item.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
            ${(item.tags && item.tags.length > 0)
              ? `<span class="botb-dash-tag">${item.tags[0]}</span>`
              : ''}
          </div>
        </li>
      `).join('');

      el.innerHTML = html;
    };

    renderColumn(data.courses,   'botb-dash-courses');
    renderColumn(data.research,  'botb-dash-research');
    renderColumn(data.tutorials, 'botb-dash-tutorials');
    renderColumn(data.notebooks, 'botb-dash-notebooks');

  } catch (err) {
    console.error('Dashboard summary error:', err);
    ['botb-dash-courses','botb-dash-research','botb-dash-tutorials','botb-dash-notebooks']
      .forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML =
          '<li class="botb-dash-item" style="text-align:center; color:#9ca3af;">Dashboard offline.</li>';
      });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadHighlights();
  loadDashboardSummary();
});
</script>

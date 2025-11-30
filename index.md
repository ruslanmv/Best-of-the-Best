---
layout: default
title: "Best of the Best | AI Highlights"
permalink: /
author_profile: false
---

<!-- Attach the BOTB CSS (served from assets/css/botb.css) -->
<link rel="stylesheet" href="{{ '/assets/css/botb.css' | relative_url }}">

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

  <!-- CONTROLS -->
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

  <!-- QUICK RANKING SNAPSHOT: repos / papers / packages -->
  <h2 class="botb-section-title">Today’s Rankings Snapshot</h2>
  <div class="botb-leader-grid">

    <!-- Repositories (primary card) -->
    <a class="botb-leader-link" href="{{ site.baseurl }}/blog/data.html">
      <div class="botb-leader-card botb-leader-card--primary">
        <div class="botb-leader-header">
          <span class="botb-leader-emoji">⭐</span>
          <div>
            <h3 class="botb-leader-title">Top GitHub Repositories</h3>
            <p class="botb-leader-subtitle">Top 4 by ⭐</p>
          </div>
        </div>
        <ul id="botb-leader-repos" class="botb-leader-list">
          <li class="botb-leader-item botb-leader-loading">Loading…</li>
        </ul>
        <div class="botb-leader-footer">Open full leaderboard →</div>
      </div>
    </a>

    <!-- Research papers -->
    <a class="botb-leader-link" href="{{ site.baseurl }}/blog/data.html">
      <div class="botb-leader-card">
        <div class="botb-leader-header">
          <span class="botb-leader-emoji">📄</span>
          <div>
            <h3 class="botb-leader-title">Most Cited Research Papers</h3>
            <p class="botb-leader-subtitle">Top 4 by 📑</p>
          </div>
        </div>
        <ul id="botb-leader-papers" class="botb-leader-list">
          <li class="botb-leader-item botb-leader-loading">Loading…</li>
        </ul>
        <div class="botb-leader-footer">Open full leaderboard →</div>
      </div>
    </a>

    <!-- Packages -->
    <a class="botb-leader-link" href="{{ site.baseurl }}/blog/data.html">
      <div class="botb-leader-card">
        <div class="botb-leader-header">
          <span class="botb-leader-emoji">📦</span>
          <div>
            <h3 class="botb-leader-title">Top PyPI Packages</h3>
            <p class="botb-leader-subtitle">Top 4 by 📥</p>
          </div>
        </div>
        <ul id="botb-leader-packages" class="botb-leader-list">
          <li class="botb-leader-item botb-leader-loading">Loading…</li>
        </ul>
        <div class="botb-leader-footer">Open full leaderboard →</div>
      </div>
    </a>

  </div>

  <!-- TODAY'S PICK -->
  <h2 class="botb-section-title">🏆 Today’s Top Pick</h2>
  <div id="today-highlight">
    <div class="botb-featured botb-featured--loading">
      <i class="fas fa-spinner fa-spin fa-lg" aria-hidden="true"></i>
      <br><br>
      Analyzing the AI ecosystem…
    </div>
  </div>

  <!-- DASHBOARD GRID -->
  <h2 class="botb-section-title">📈 AI Ecosystem Dashboard</h2>
  <p class="botb-dash-intro">
    A compact view of the most relevant <strong>Courses</strong>, <strong>Research papers</strong>, 
    <strong>Tutorials</strong>, and <strong>Notebooks</strong> curated by the multi-agent system.
    Explore more details in the full 
    <a href="{{ site.baseurl }}/blog/data.html" class="botb-dash-intro-link">Trending Dashboard</a>.
  </p>

  <div class="botb-dash-grid">

    <!-- Courses -->
    <div class="botb-dash-column">
      <div class="botb-dash-header">
        <div class="botb-dash-icon botb-dash-icon--courses">
          <i class="fas fa-graduation-cap" aria-hidden="true"></i>
        </div>
        <h3 class="botb-dash-title">
          <a href="{{ site.baseurl }}/blog/courses.html">Courses</a>
        </h3>
      </div>
      <ul id="botb-dash-courses" class="botb-dash-list">
        <li class="botb-dash-item botb-dash-item-loading">Loading…</li>
      </ul>
    </div>

    <!-- Research -->
    <div class="botb-dash-column">
      <div class="botb-dash-header">
        <div class="botb-dash-icon botb-dash-icon--research">
          <i class="fas fa-scroll" aria-hidden="true"></i>
        </div>
        <h3 class="botb-dash-title">
          <a href="{{ site.baseurl }}/blog/research.html">Research</a>
        </h3>
      </div>
      <ul id="botb-dash-research" class="botb-dash-list">
        <li class="botb-dash-item botb-dash-item-loading">Loading…</li>
      </ul>
    </div>

    <!-- Tutorials -->
    <div class="botb-dash-column">
      <div class="botb-dash-header">
        <div class="botb-dash-icon botb-dash-icon--tutorials">
          <i class="fas fa-code" aria-hidden="true"></i>
        </div>
        <h3 class="botb-dash-title">
          <a href="{{ site.baseurl }}/blog/tutorials.html">Tutorials</a>
        </h3>
      </div>
      <ul id="botb-dash-tutorials" class="botb-dash-list">
        <li class="botb-dash-item botb-dash-item-loading">Loading…</li>
      </ul>
    </div>

    <!-- Notebooks -->
    <div class="botb-dash-column">
      <div class="botb-dash-header">
        <div class="botb-dash-icon botb-dash-icon--notebooks">
          <i class="fas fa-book-open" aria-hidden="true"></i>
        </div>
        <h3 class="botb-dash-title">
          <a href="{{ site.baseurl }}/blog/notebooks.html">Notebooks</a>
        </h3>
      </div>
      <ul id="botb-dash-notebooks" class="botb-dash-list">
        <li class="botb-dash-item botb-dash-item-loading">Loading…</li>
      </ul>
    </div>

  </div>

  <!-- PREVIOUS HIGHLIGHTS -->
  <h2 class="botb-section-title">📅 Previous Highlights</h2>
  <div id="recent-highlights" class="botb-grid"></div>

</div>

<script>
const baseurl         = '{{ site.baseurl | default: "" }}'.replace(/\/$/, '');
const postsIndexUrl   = baseurl + '/blog/posts/index.json';
const dataApiUrl      = baseurl + '/blog/api/data.json';
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

/**
 * Build a post URL safely.
 * Accepts:
 *   - "posts/2024-11-22-example.html"
 *   - "blog/posts/2024-11-22-example.html"
 *   - "/blog/posts/...."
 * and always returns:  baseurl + "/blog/posts/..."
 * so we never get `/blog/blog/...` 404s.
 */
const buildPostUrl = (rawUrl) => {
  if (!rawUrl) return '#';
  let path = String(rawUrl).replace(/^\/+/, ''); // strip leading '/'

  // If it already starts with 'blog/', just attach baseurl
  if (path.startsWith('blog/')) {
    return `${baseurl}/${path}`;
  }

  // Otherwise treat it as "posts/..." under /blog
  return `${baseurl}/blog/${path}`;
};

/**
 * Render the "Top 4" snapshot cards (repos/papers/packages).
 * all cards themselves link to the full leaderboard page.
 */
const renderLeaders = (data) => {
  const reposList    = document.getElementById('botb-leader-repos');
  const papersList   = document.getElementById('botb-leader-papers');
  const packagesList = document.getElementById('botb-leader-packages');

  if (!reposList || !papersList || !packagesList) return;

  const repos    = Array.isArray(data.repositories) ? data.repositories.slice() : [];
  const papers   = Array.isArray(data.papers) ? data.papers.slice() : [];
  const packages = Array.isArray(data.packages) ? data.packages.slice() : [];

  const topRepos    = repos.sort((a, b) => (b.stars || 0) - (a.stars || 0)).slice(0, 4);
  const topPapers   = papers.sort((a, b) => (b.citations || 0) - (a.citations || 0)).slice(0, 4);
  const topPackages = packages.sort((a, b) => (b.downloads_last_month || 0) - (a.downloads_last_month || 0)).slice(0, 4);

  const makeLeaderHtml = (items, valueKey, suffix) => {
    if (!items.length) {
      return '<li class="botb-leader-item botb-leader-empty">No data yet.</li>';
    }
    return items.map((item, idx) => `
      <li class="botb-leader-item">
        <span class="botb-leader-rank">#${idx + 1}</span>
        <span class="botb-leader-name">${item.name || 'Unknown'}</span>
        ${valueKey ? `<span class="botb-leader-metric">${(item[valueKey] || 0).toLocaleString('en-US')}${suffix || ''}</span>` : ''}
      </li>
    `).join('');
  };

  reposList.innerHTML    = makeLeaderHtml(topRepos, 'stars', '★');
  papersList.innerHTML   = makeLeaderHtml(topPapers, 'citations', ' 📑');
  packagesList.innerHTML = makeLeaderHtml(topPackages, 'downloads_last_month', ' 📥');
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

    // Also populate the new "snapshot" cards
    renderLeaders(data);

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

    todayContainer.innerHTML = `
      <article class="botb-featured">
        <div class="botb-featured-header">
          <i class="far fa-calendar" aria-hidden="true"></i>
          <span>${new Date(today.date).toLocaleDateString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
          })}</span>
        </div>
        <h3><a href="${buildPostUrl(today.url)}">${today.title}</a></h3>
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
            <a href="${buildPostUrl(post.url)}">${post.title}</a>
          </h4>
          <p class="botb-card-excerpt">
            ${stripMarkdown(post.excerpt || '').substring(0, 110)}…
          </p>
          <div class="botb-card-footer">Read highlight &rarr;</div>
        </article>
      `).join('');
    } else {
      recentContainer.innerHTML =
        '<p class="botb-no-highlights">No previous highlights yet.</p>';
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
        el.innerHTML = '<li class="botb-dash-item botb-dash-item-empty">No items yet.</li>';
        return;
      }

      const html = items.slice(0, 4).map(item => `
        <li class="botb-dash-item">
          <a href="${buildPostUrl(item.url)}">${item.title}</a>
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
          '<li class="botb-dash-item botb-dash-item-empty">Dashboard offline.</li>';
      });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadHighlights();
  loadDashboardSummary();
});
</script>

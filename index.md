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

  <!-- AI ECOSYSTEM - Leaderboard dashboard -->
  <h2 class="botb-section-title">📈 AI Ecosystem Rankings</h2>
  <p class="eco-dashboard__subtitle">What is leading today across learning, research, and practical building</p>
  <div class="eco-dashboard">

    <!-- Trending Now -->
    <a class="eco-dashboard__link" href="{{ site.baseurl }}/blog/data.html">
      <div class="eco-dashboard__card eco-dashboard__card--primary">
        <div class="eco-dashboard__header">
          <span class="eco-dashboard__emoji">🔥</span>
          <div>
            <h3 class="eco-dashboard__title">Trending Now</h3>
            <p class="eco-dashboard__meta">Top ranked by popularity</p>
          </div>
        </div>
        <ul id="eco-trending" class="eco-dashboard__list">
          <li class="eco-dashboard__item eco-dashboard__loading">Loading…</li>
        </ul>
        <div class="eco-dashboard__footer">View trending →</div>
      </div>
    </a>

    <!-- Courses -->
    <a class="eco-dashboard__link" href="{{ site.baseurl }}/blog/courses.html">
      <div class="eco-dashboard__card">
        <div class="eco-dashboard__header">
          <span class="eco-dashboard__emoji">🎓</span>
          <div>
            <h3 class="eco-dashboard__title">Top Courses</h3>
            <p class="eco-dashboard__meta">Ranked learning resources</p>
          </div>
        </div>
        <ul id="eco-courses" class="eco-dashboard__list">
          <li class="eco-dashboard__item eco-dashboard__loading">Loading…</li>
        </ul>
        <div class="eco-dashboard__footer">View all courses →</div>
      </div>
    </a>

    <!-- Research -->
    <a class="eco-dashboard__link" href="{{ site.baseurl }}/blog/research.html">
      <div class="eco-dashboard__card">
        <div class="eco-dashboard__header">
          <span class="eco-dashboard__emoji">🔬</span>
          <div>
            <h3 class="eco-dashboard__title">Top Research</h3>
            <p class="eco-dashboard__meta">Ranked papers and studies</p>
          </div>
        </div>
        <ul id="eco-research" class="eco-dashboard__list">
          <li class="eco-dashboard__item eco-dashboard__loading">Loading…</li>
        </ul>
        <div class="eco-dashboard__footer">View all research →</div>
      </div>
    </a>

    <!-- Hands-on -->
    <a class="eco-dashboard__link" href="{{ site.baseurl }}/blog/tutorials.html">
      <div class="eco-dashboard__card">
        <div class="eco-dashboard__header">
          <span class="eco-dashboard__emoji">🛠</span>
          <div>
            <h3 class="eco-dashboard__title">Top Hands-on</h3>
            <p class="eco-dashboard__meta">Ranked tutorials and notebooks</p>
          </div>
        </div>
        <ul id="eco-handson" class="eco-dashboard__list">
          <li class="eco-dashboard__item eco-dashboard__loading">Loading…</li>
        </ul>
        <div class="eco-dashboard__footer">View all tutorials →</div>
      </div>
    </a>

  </div>

  <!-- PREVIOUS HIGHLIGHTS (blog-style list) -->
  <h2 class="botb-section-title">📅 Previous Highlights</h2>
  <div id="recent-highlights" class="botb-posts-list"></div>

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
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')  // [text](url) -> text
    .replace(/\*\*/g, '')
    .replace(/__/g, '')
    .replace(/`/g, '')
    .replace(/#{1,6}\s/g, '');
};

/**
 * Build a URL safely.
 *
 * Cases:
 *   - Absolute external URLs (https://..., http://...):
 *       -> return as-is (no baseurl prefix).
 *   - "blog/posts/2024-11-22-example.html":
 *       -> baseurl + "/blog/posts/..."
 *   - "posts/2024-11-22-example.html":
 *       -> baseurl + "/blog/posts/..."
 *   - "/blog/posts/....":
 *       -> baseurl + "/blog/posts/..."
 */
const buildPostUrl = (rawUrl) => {
  if (!rawUrl) return '#';
  const urlStr = String(rawUrl).trim();

  // External links (Colab, DOI, GitHub, etc) – don't prefix with the site URL
  if (/^https?:\/\//i.test(urlStr)) {
    return urlStr;
  }

  // Internal relative paths
  let path = urlStr.replace(/^\/+/, ''); // strip leading '/'

  // If it already starts with 'blog/', just attach baseurl
  if (path.startsWith('blog/')) {
    return `${baseurl}/${path}`;
  }

  // Otherwise treat it as "posts/..." under /blog
  return `${baseurl}/blog/${path}`;
};

/**
 * Render the "Top 4" snapshot cards (repos/papers/packages).
 * All cards themselves link to the full leaderboard page.
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

    const todayTeaser = today.teaser
      ? `${baseurl}${today.teaser}`
      : `https://picsum.photos/seed/today${today.title.length}/800/400`;
    const todayExcerpt = stripMarkdown(today.excerpt) || 'Daily highlight selected from the leaderboard.';

    todayContainer.innerHTML = `
      <article class="botb-featured">
        <a href="${buildPostUrl(today.url)}" class="botb-featured__image-link">
          <img src="${todayTeaser}" alt="${today.title}" class="botb-featured__image"
               onerror="this.onerror=null; this.src='https://picsum.photos/seed/topick/800/400';">
        </a>
        <div class="botb-featured__body">
          <div class="botb-featured-header">
            <i class="far fa-calendar" aria-hidden="true"></i>
            <span>${new Date(today.date).toLocaleDateString('en-US', {
              weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
            })}</span>
          </div>
          <h3><a href="${buildPostUrl(today.url)}">${today.title}</a></h3>
          <p>${todayExcerpt}</p>
          <div class="botb-tag-container">${tagsHtml}</div>
          <a href="${buildPostUrl(today.url)}" class="botb-featured__cta">Read full article →</a>
        </div>
      </article>
    `;

    // Pagination: 3 posts per page in a grid with slide animation
    const POSTS_PER_PAGE = 3;
    let currentPage = 1;
    const totalPages = Math.ceil(rest.length / POSTS_PER_PAGE);

    function renderPage(page, direction) {
      currentPage = page;
      const start = (page - 1) * POSTS_PER_PAGE;
      const pageItems = rest.slice(start, start + POSTS_PER_PAGE);

      if (!pageItems.length) {
        recentContainer.innerHTML =
          '<p class="botb-no-highlights">No previous highlights yet.</p>';
        return;
      }

      // Build 3-column grid cards
      const cardsHtml = pageItems.map((post, idx) => {
        const pageOffset = (page - 1) * POSTS_PER_PAGE + idx;
        const fallbackImg = `https://picsum.photos/seed/botb${pageOffset}/600/340`;
        const teaserUrl = post.teaser
          ? `${baseurl}${post.teaser}`
          : fallbackImg;
        const cleanExcerpt = stripMarkdown(post.excerpt || '').substring(0, 120);
        const postTags = (post.tags || []).filter(t => t && !['python','package','pypi'].includes(t)).slice(0, 2);
        const tagsHtml = postTags.map(t =>
          `<span class="botb-card-tag">${t.replace(/-/g, ' ')}</span>`
        ).join('');
        const dateStr = new Date(post.date).toLocaleDateString('en-US', {
          year: 'numeric', month: 'short', day: 'numeric'
        });
        const readMin = Math.max(3, Math.ceil((cleanExcerpt.length / 5) * 8 / 200));
        const delay = idx * 120;

        return `
          <article class="botb-post-card" style="animation-delay: ${delay}ms">
            <a href="${buildPostUrl(post.url)}" class="botb-post-card__image-link">
              <img src="${teaserUrl}" alt="${post.title}" class="botb-post-card__image" loading="lazy"
                   onerror="this.onerror=null; this.src='${fallbackImg}';">
            </a>
            <div class="botb-post-card__body">
              <div class="botb-post-card__meta">
                <time class="botb-post-card__date">${dateStr}</time>
                <span class="botb-post-card__meta-dot"></span>
                <span class="botb-post-card__reading-time">${readMin} min read</span>
              </div>
              ${tagsHtml ? `<div class="botb-post-card__tags">${tagsHtml}</div>` : ''}
              <h3 class="botb-post-card__title">
                <a href="${buildPostUrl(post.url)}">${post.title}</a>
              </h3>
              <p class="botb-post-card__excerpt">${cleanExcerpt}${cleanExcerpt.length >= 120 ? '…' : ''}</p>
              <a href="${buildPostUrl(post.url)}" class="botb-post-card__readmore">
                Continue reading <span style="transition:inherit">→</span>
              </a>
            </div>
          </article>
        `;
      }).join('');

      // Pagination controls - show all page numbers
      let paginationHtml = '';
      if (totalPages > 1) {
        const showingStart = start + 1;
        const showingEnd = Math.min(start + POSTS_PER_PAGE, rest.length);

        paginationHtml = `<div class="botb-pagination-wrapper">`;
        paginationHtml += `<div class="botb-pagination-info">Page ${page} of ${totalPages} &middot; Showing ${showingStart}-${showingEnd} of ${rest.length} posts</div>`;
        paginationHtml += `<nav class="botb-pagination" aria-label="Blog pagination">`;

        // Previous button
        paginationHtml += `<button class="botb-page-btn botb-page-btn--nav" onclick="changePage(${page - 1})" ${page <= 1 ? 'disabled' : ''}><span class="botb-page-arrow">&lsaquo;</span> Prev</button>`;

        // Page numbers - show first, last, current±1, and ellipsis
        for (let i = 1; i <= totalPages; i++) {
          if (i === page) {
            paginationHtml += `<span class="botb-page-btn botb-page-btn--active">${i}</span>`;
          } else if (i === 1 || i === totalPages || Math.abs(i - page) <= 1) {
            paginationHtml += `<button class="botb-page-btn" onclick="changePage(${i})">${i}</button>`;
          } else if (i === 2 && page > 4) {
            paginationHtml += `<span class="botb-page-ellipsis">…</span>`;
          } else if (i === totalPages - 1 && page < totalPages - 3) {
            paginationHtml += `<span class="botb-page-ellipsis">…</span>`;
          }
        }

        // Next button
        paginationHtml += `<button class="botb-page-btn botb-page-btn--nav" onclick="changePage(${page + 1})" ${page >= totalPages ? 'disabled' : ''}>Next <span class="botb-page-arrow">&rsaquo;</span></button>`;
        paginationHtml += `</nav></div>`;
      }

      recentContainer.innerHTML = cardsHtml + paginationHtml;
    }

    window.changePage = function(page) {
      if (page < 1 || page > totalPages) return;
      renderPage(page);
      document.getElementById('recent-highlights').scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    renderPage(1);

  } catch (err) {
    console.error('Content error:', err);
    todayContainer.innerHTML =
      '<div class="botb-featured">Content is currently updating…</div>';
  }
}

// 3. Load AI Ecosystem dashboard (leaderboard-style rankings)
async function loadDashboardSummary() {
  const renderRankedList = (items, containerId, limit) => {
    const el = document.getElementById(containerId);
    if (!el) return;
    if (!items || !items.length) {
      el.innerHTML = '<li class="eco-dashboard__item eco-dashboard__empty">No data yet.</li>';
      return;
    }
    el.innerHTML = items.slice(0, limit || 4).map((item, idx) => {
      const typeBadge = (item.tags || []).find(t => ['Course','Paper','Tutorial','Notebook'].includes(t)) || '';
      const title = (item.title || 'Untitled').substring(0, 60);
      return `
        <li class="eco-dashboard__item">
          <span class="eco-dashboard__rank">#${idx + 1}</span>
          <span class="eco-dashboard__name">${title}${item.title && item.title.length > 60 ? '…' : ''}</span>
          ${typeBadge ? `<span class="eco-dashboard__type">${typeBadge}</span>` : ''}
        </li>
      `;
    }).join('');
  };

  try {
    const res = await fetch(dashboardApiUrl);
    if (!res.ok) throw new Error('Failed to load dashboard.json');
    const data = await res.json();

    // Trending: mix top items from all categories
    const trending = data.trending || [];
    if (trending.length < 4) {
      const supplement = [...(data.courses || []), ...(data.tutorials || [])].slice(0, 4 - trending.length);
      trending.push(...supplement);
    }
    renderRankedList(trending, 'eco-trending', 4);

    // Courses
    renderRankedList(data.courses, 'eco-courses', 4);

    // Research
    renderRankedList(data.research, 'eco-research', 4);

    // Hands-on: merge tutorials + notebooks, deduplicate by title
    const seen = new Set();
    const handson = [...(data.tutorials || []), ...(data.notebooks || [])].filter(item => {
      if (seen.has(item.title)) return false;
      seen.add(item.title);
      return true;
    });
    renderRankedList(handson, 'eco-handson', 4);

  } catch (err) {
    console.error('Dashboard error:', err);
    ['eco-trending','eco-courses','eco-research','eco-handson'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = '<li class="eco-dashboard__item eco-dashboard__empty">Dashboard is updating…</li>';
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadHighlights();
  loadDashboardSummary();
});
</script>

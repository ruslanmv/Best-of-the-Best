"""
Generate index.json and index.html for blog posts
"""

import json
from pathlib import Path
from datetime import datetime
import re


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown file"""
    frontmatter = {}

    # Check if file has frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1].strip()

            # Parse simple YAML
            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')

                    # Handle tags (array)
                    if key == 'tags':
                        # Extract tags from ["tag1", "tag2"] format
                        tags = re.findall(r'"([^"]*)"', value)
                        frontmatter[key] = tags
                    else:
                        frontmatter[key] = value

            # Get excerpt from content
            content_body = parts[2].strip()
            # Get first paragraph as excerpt
            paragraphs = [p.strip() for p in content_body.split('\n\n') if p.strip() and not p.strip().startswith('#')]
            if paragraphs:
                excerpt = paragraphs[0][:200] + '...' if len(paragraphs[0]) > 200 else paragraphs[0]
                frontmatter['excerpt'] = excerpt

    return frontmatter


def generate_html_index(posts: list):
    """Generate index.html file for the blog"""

    html_template = '''<!DOCTYPE html>
<html lang="en" class="no-js">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily AI Package Highlights - Best of the Best</title>
    <meta name="description" content="Discover the best AI packages with watsonx.ai and Watson Orchestrate integration insights">
    <meta name="author" content="Ruslan Magana Vsevolodovna">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="Daily AI Package Highlights">
    <meta property="og:description" content="Discover the best AI packages with watsonx.ai and Watson Orchestrate integration insights">

    <!-- Minimal Mistakes inspired CSS -->
    <style>
        /* Reset and Base Styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary-color: #7a8288;
            --link-color: #3273dc;
            --link-hover-color: #0a0a0a;
            --text-color: #3a3a3a;
            --background-color: #fff;
            --border-color: #bdc1c4;
            --notice-bg: #f3f3f3;
            --code-bg: #fafafa;
            --masthead-bg: #fff;
            --footer-bg: #000;
            --font-family: -apple-system, BlinkMacSystemFont, "Roboto", "Segoe UI", "Helvetica Neue", "Lucida Grande", Arial, sans-serif;
            --font-family-mono: Monaco, Consolas, "Lucida Console", monospace;
        }

        html {
            font-size: 16px;
            -webkit-text-size-adjust: 100%;
            -webkit-font-smoothing: antialiased;
        }

        body {
            font-family: var(--font-family);
            color: var(--text-color);
            background-color: var(--background-color);
            line-height: 1.5;
        }

        /* Masthead */
        .masthead {
            position: relative;
            background-color: var(--masthead-bg);
            border-bottom: 1px solid var(--border-color);
            animation: intro 0.3s both;
            animation-delay: 0.15s;
            z-index: 20;
        }

        .masthead__inner-wrap {
            max-width: 1280px;
            margin-left: auto;
            margin-right: auto;
            padding: 1em;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }

        .site-title {
            font-size: 1.25rem;
            font-weight: bold;
            line-height: 1;
            text-decoration: none;
            color: var(--text-color);
        }

        .greedy-nav {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .greedy-nav a {
            color: var(--text-color);
            text-decoration: none;
            padding: 0.5rem;
            border-radius: 4px;
            transition: background-color 0.2s;
        }

        .greedy-nav a:hover {
            background-color: var(--notice-bg);
        }

        /* Page Content */
        .page__content {
            max-width: 1024px;
            margin: 0 auto;
            padding: 2em 1em;
        }

        /* Hero */
        .page__hero {
            position: relative;
            margin-bottom: 2em;
            background-color: var(--notice-bg);
            background-size: cover;
            background-position: center;
            animation: intro 0.3s both;
            animation-delay: 0.25s;
        }

        .page__hero-overlay {
            position: relative;
            padding: 3em 1em;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.8) 0%, rgba(118, 75, 162, 0.8) 100%);
            color: #fff;
        }

        .page__title {
            font-size: 2.5em;
            line-height: 1.2;
            margin-bottom: 0.5em;
            color: #fff;
        }

        .page__lead {
            font-size: 1.25em;
            margin-bottom: 0;
        }

        /* Archive */
        .archive {
            margin-bottom: 2em;
        }

        .archive__item-title {
            margin-bottom: 0.25em;
            font-size: 1.5em;
            line-height: 1.2;
        }

        .archive__item-title a {
            color: var(--text-color);
            text-decoration: none;
        }

        .archive__item-title a:hover {
            color: var(--link-color);
            text-decoration: underline;
        }

        .archive__item-excerpt {
            margin-top: 0.5em;
            font-size: 0.875em;
            color: var(--primary-color);
        }

        .archive__item {
            background: var(--background-color);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 1.5em;
            margin-bottom: 1.5em;
            transition: box-shadow 0.2s;
        }

        .archive__item:hover {
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }

        .page__meta {
            margin-top: 0.5em;
            color: var(--primary-color);
            font-size: 0.875em;
        }

        .page__meta i {
            margin-right: 0.25em;
        }

        /* Tags */
        .page__taxonomy {
            margin-top: 1em;
        }

        .page__taxonomy-item {
            display: inline-block;
            margin-right: 0.5em;
            margin-bottom: 0.5em;
            padding: 0.25em 0.75em;
            background-color: var(--code-bg);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 0.75em;
            text-decoration: none;
            color: var(--text-color);
        }

        .page__taxonomy-item:hover {
            background-color: var(--notice-bg);
        }

        /* Notice */
        .notice {
            margin: 2em 0;
            padding: 1em;
            background-color: var(--notice-bg);
            border-left: 4px solid var(--link-color);
            border-radius: 4px;
        }

        .notice h4 {
            margin-bottom: 0.5em;
            color: var(--text-color);
        }

        /* Features */
        .feature__wrapper {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5em;
            margin: 2em 0;
        }

        .feature__item {
            background: var(--background-color);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 1.5em;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .feature__item:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
        }

        .feature__item h3 {
            font-size: 1.25em;
            margin-bottom: 0.5em;
            color: var(--text-color);
        }

        /* Footer */
        .page__footer {
            background-color: var(--footer-bg);
            color: #fff;
            margin-top: 3em;
            animation: intro 0.3s both;
            animation-delay: 0.45s;
        }

        .page__footer-inner {
            max-width: 1024px;
            margin: 0 auto;
            padding: 2em 1em;
        }

        .page__footer-copyright {
            text-align: center;
            font-size: 0.875em;
        }

        .page__footer-follow {
            text-align: center;
            margin-bottom: 1em;
        }

        .page__footer a {
            color: #fff;
            text-decoration: none;
            margin: 0 0.5em;
        }

        .page__footer a:hover {
            text-decoration: underline;
        }

        /* Buttons */
        .btn {
            display: inline-block;
            margin-bottom: 0.25em;
            padding: 0.5em 1em;
            font-family: var(--font-family);
            font-size: 0.875em;
            font-weight: bold;
            text-align: center;
            text-decoration: none;
            border-width: 0;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        .btn--primary {
            background-color: var(--link-color);
            color: #fff;
        }

        .btn--primary:hover {
            background-color: #276cda;
        }

        /* Animations */
        @keyframes intro {
            0% {
                opacity: 0;
            }
            100% {
                opacity: 1;
            }
        }

        /* Responsive */
        @media (max-width: 768px) {
            .page__title {
                font-size: 2em;
            }

            .page__lead {
                font-size: 1em;
            }

            .archive__item-title {
                font-size: 1.25em;
            }

            .masthead__inner-wrap {
                flex-direction: column;
                align-items: flex-start;
            }

            .greedy-nav {
                margin-top: 1em;
                flex-wrap: wrap;
            }
        }

        /* Loading state */
        .loading {
            text-align: center;
            padding: 2em;
            color: var(--primary-color);
        }

        .loading::after {
            content: '...';
            animation: loading 1.5s infinite;
        }

        @keyframes loading {
            0% { content: '.'; }
            33% { content: '..'; }
            66% { content: '...'; }
        }
    </style>
</head>
<body>
    <!-- Masthead -->
    <div class="masthead">
        <div class="masthead__inner-wrap">
            <a class="site-title" href="/">Best of the Best</a>
            <nav class="greedy-nav">
                <a href="/">Home</a>
                <a href="data.html">Data Dashboard</a>
                <a href="api/data.json" target="_blank">API</a>
                <a href="https://github.com/ruslanmv/Best-of-the-Best" target="_blank">GitHub</a>
            </nav>
        </div>
    </div>

    <!-- Hero -->
    <div class="page__hero">
        <div class="page__hero-overlay">
            <div class="page__content">
                <h1 class="page__title">Daily AI Package Highlights</h1>
                <p class="page__lead">Discover the best AI packages with watsonx.ai and Watson Orchestrate integration insights</p>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="page__content">
        <!-- Introduction -->
        <div class="notice">
            <h4>🤖 AI-Powered Daily Insights</h4>
            <p>Every day, our multi-agent AI system powered by CrewAI and Ollama analyzes the most trending AI packages, evaluates their potential integration with IBM watsonx.ai and Watson Orchestrate, and creates comprehensive blog posts to help you stay ahead in the AI landscape.</p>
        </div>

        <!-- Features -->
        <h2>Why This Blog?</h2>
        <div class="feature__wrapper">
            <div class="feature__item">
                <h3>🔍 AI-Powered Research</h3>
                <p>Our research agent analyzes thousands of AI packages daily to identify the most impactful and trending tools.</p>
            </div>
            <div class="feature__item">
                <h3>🧠 watsonx.ai Integration</h3>
                <p>Expert analysis on how each package can enhance your IBM watsonx.ai workflows and capabilities.</p>
            </div>
            <div class="feature__item">
                <h3>⚙️ Watson Orchestrate Applications</h3>
                <p>Discover how to leverage packages in Watson Orchestrate for automated business processes.</p>
            </div>
            <div class="feature__item">
                <h3>📝 Daily Insights</h3>
                <p>Fresh content every day, written by AI agents with deep technical knowledge and business acumen.</p>
            </div>
            <div class="feature__item">
                <h3>🤖 Multi-Agent System</h3>
                <p>Powered by CrewAI with specialized agents for research, analysis, and technical writing.</p>
            </div>
            <div class="feature__item">
                <h3>💡 Practical Examples</h3>
                <p>Each post includes code examples, use cases, and implementation strategies.</p>
            </div>
        </div>

        <!-- Blog Posts -->
        <h2>Latest Posts</h2>
        <div id="posts-container" class="archive">
            <div class="loading">Loading posts</div>
        </div>

        <!-- Call to Action -->
        <div style="text-align: center; margin: 3em 0;">
            <a href="https://github.com/ruslanmv/Best-of-the-Best" class="btn btn--primary">⭐ Star on GitHub</a>
            <a href="api/feed.xml" class="btn btn--primary">📰 Subscribe to RSS</a>
        </div>
    </div>

    <!-- Footer -->
    <footer class="page__footer">
        <div class="page__footer-inner">
            <div class="page__footer-follow">
                <a href="https://github.com/ruslanmv" target="_blank">GitHub</a>
                <a href="https://ruslanmv.com" target="_blank">Personal Site</a>
                <a href="api/feed.xml">RSS Feed</a>
            </div>
            <div class="page__footer-copyright">
                &copy; 2025 <strong>Ruslan Magana Vsevolodovna</strong>. Powered by Jekyll & Minimal Mistakes.
            </div>
        </div>
    </footer>

    <!-- JavaScript -->
    <script>
        // Load and display blog posts
        async function loadPosts() {
            const container = document.getElementById('posts-container');

            try {
                const response = await fetch('posts/index.json');
                if (!response.ok) {
                    throw new Error('Could not load posts index');
                }

                const posts = await response.json();

                if (posts.length === 0) {
                    container.innerHTML = `
                        <div class="notice">
                            <p>No posts available yet. Check back tomorrow for the first daily highlight!</p>
                        </div>
                    `;
                    return;
                }

                // Sort posts by date (newest first)
                posts.sort((a, b) => new Date(b.date) - new Date(a.date));

                // Generate HTML for each post
                container.innerHTML = posts.map(post => {
                    const date = new Date(post.date);
                    const formattedDate = date.toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                    });

                    return `
                        <article class="archive__item">
                            <h2 class="archive__item-title">
                                <a href="posts/${post.filename}">${post.title}</a>
                            </h2>
                            <p class="page__meta">
                                <i>📅</i> <time datetime="${post.date}">${formattedDate}</time>
                                <span> • </span>
                                <i>✍️</i> ${post.author || 'AI Multi-Agent System'}
                            </p>
                            <p class="archive__item-excerpt">${post.excerpt || 'Click to read more...'}</p>
                            <div class="page__taxonomy">
                                ${(post.tags || ['AI', 'Machine Learning']).map(tag =>
                                    `<a href="#${tag}" class="page__taxonomy-item">${tag}</a>`
                                ).join('')}
                            </div>
                        </article>
                    `;
                }).join('');

            } catch (error) {
                console.error('Error loading posts:', error);
                container.innerHTML = `
                    <div class="notice">
                        <h4>Posts Coming Soon</h4>
                        <p>Posts will appear here once the multi-agent system starts generating daily content.</p>
                        <p>The system analyzes trending AI packages and creates insightful blog posts automatically!</p>
                    </div>
                `;
            }
        }

        // Load posts when page loads
        document.addEventListener('DOMContentLoaded', loadPosts);
    </script>
</body>
</html>'''

    # Write the HTML file
    with open('blog/index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)

    print(f"✅ Generated blog/index.html")


def generate_posts_index():
    """Generate index.json file for all blog posts"""
    posts_dir = Path('blog/posts')
    posts_dir.mkdir(parents=True, exist_ok=True)

    posts = []

    # Scan all markdown files
    for md_file in posts_dir.glob('*.md'):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            frontmatter = extract_frontmatter(content)

            post_info = {
                'filename': md_file.name,
                'title': frontmatter.get('title', md_file.stem),
                'date': frontmatter.get('date', datetime.now().isoformat()),
                'author': frontmatter.get('author', 'AI Multi-Agent System'),
                'tags': frontmatter.get('tags', ['AI', 'Machine Learning']),
                'excerpt': frontmatter.get('excerpt', '')
            }

            posts.append(post_info)

        except Exception as e:
            print(f"Error processing {md_file}: {e}")

    # Write index.json
    index_file = posts_dir / 'index.json'
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated index with {len(posts)} posts")
    print(f"📝 Index file: {index_file}")

    return posts


if __name__ == '__main__':
    # Generate JSON index
    posts = generate_posts_index()

    # HTML index is now handled by Jekyll (index.md using Minimal Mistakes).
    # If you still want a standalone HTML blog index under /blog/,
    # you can keep the next line; otherwise, comment it out.
    # generate_html_index(posts)

from collections import Counter, defaultdict
from datetime import datetime
from json import load
from os.path import join
from pathlib import Path
from urllib.request import urlopen
import time

from cv2 import IMREAD_GRAYSCALE, THRESH_BINARY, imdecode, threshold
from google.cloud import bigquery
from matplotlib import font_manager
import matplotlib.pyplot as plt
from numpy import any, asarray, mean, median
from pypistats import overall, recent
from tqdm import tqdm
from wordcloud import WordCloud
from httpx import HTTPStatusError

# Set of available badge names (from SVG images)
BADGES = set(image.stem for image in Path('./images').glob('*.svg'))
TOP_K = 20

def colab_url(url: str) -> str:
    return f'[![Open In Colab](./images/colab.svg)]({url})'

def doi_url(url: str) -> str:
    doi = url.split('org/')[1]
    return f'[![](https://api.juleskreuer.eu/citation-badge.php?doi={doi})]({url})'

def git_url(url: str) -> str:
    repo = '/'.join(url.split('com/')[1].split('/')[:2])
    return f'[![](https://img.shields.io/github/stars/{repo}?style=social)]({url})'

def pypi_url(package: str, period='dm') -> str:
    return f'[![](https://img.shields.io/pypi/{period}/{package}?style=flat&logo=pypi&label=%E2%80%8D&labelColor=f7f7f4&color=006dad)](https://pypi.org/{package}/)'

def read_json(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        return load(f)

def load_projects():
    for entity in ['cources', 'research', 'tutorials']:
        yield from read_json(join('data', f'{entity}.json'))

def get_git_repo_name(git_url: tuple[str, str, int]) -> tuple[str, int]:
    """
    Extracts the repository name in the format "user/repo" from a GitHub URL.
    """
    _, url, stars = git_url
    parts = url.split('/')
    if len(parts) >= 5:
        repo = parts[3] + '/' + parts[4]
    else:
        repo = url
    return (repo, stars)

def parse_link(link_tuple: tuple[str, str], height=20) -> str:
    name, url = link_tuple
    if name in BADGES:
        return f'[<img src="./images/{name}.svg" alt="{name}" height={height}/>]({url})'
    return f'[{name}]({url})'

def parse_authors(authors: list[tuple[str, str]], num_of_visible: int) -> str:
    if len(authors) == 1:
        return '[{}]({})'.format(*authors[0])
    if len(authors) <= num_of_visible + 1:
        return '<ul>' + ' '.join(f'<li>[{author}]({link})</li>' for author, link in authors[:num_of_visible + 1]) + '</ul>'
    return '<ul>' + ' '.join(f'<li>[{author}]({link})</li>' for author, link in authors[:num_of_visible]) + '<details><summary>others</summary>' + ' '.join(f'<li>[{author}]({link})</li>' for author, link in authors[num_of_visible:]) + '</ul></details>'

def parse_links(list_of_links: list[tuple[str, str]]) -> str:
    if len(list_of_links) == 0:
        return ''
    dct = defaultdict(list)
    for name_url in list_of_links:
        name, url = name_url[0], name_url[1]
        dct[name].append(url)
    line = ''
    if 'doi' in dct:
        line += doi_url(dct['doi'][0]) + ' '
        dct.pop('doi')
    if 'git' in dct:
        line += git_url(dct['git'][0]) + ' '
        if len(dct['git']) == 1:
            dct.pop('git')
        else:
            dct['git'].pop(0)
    if len(dct) == 0:
        return line
    return line + '<ul>' + ''.join('<li>' + ', '.join(parse_link((name, url)) for url in dct[name]) + '</li>' for name in dct.keys()) + '</ul>'

def get_top_authors(topK) -> tuple[str, int]:
    global TOP_K
    authors, num_of_authors = [], []
    for project in load_projects():
        authors.extend([tuple(author) for author in project['author']])
        num_of_authors.append(len(project['author']))
    cnt = Counter(authors)
    most_common = cnt.most_common()
    contributions = most_common[topK][1]
    idx = topK
    while idx < len(most_common) and most_common[idx][1] == contributions:
        idx += 1
    num_of_visible = int(min(mean(num_of_authors), median(num_of_authors)))
    TOP_K = idx
    return '<ul>' + ' '.join(f'<li>[{author}]({link})</li>' for (author, link), _ in most_common[:idx]) + '</ul>', num_of_visible

def get_best_repositories(topK) -> str:
    """
    Returns a markdown table for the top repositories (by stars) found in the projects.
    """
    repos = {}
    for project in load_projects():
        for link in project['links']:
            if link[0] == 'git':
                repo, stars = get_git_repo_name(link)
                repos[repo] = stars
                break
    repos = sorted(repos.items(), key=lambda item: item[1], reverse=True)[:topK]
    table = "| Repository | Stars | Link |\n"
    table += "|---|---|---|\n"
    for repo, stars in repos:
        link = f"https://github.com/{repo}"
        table += f"| {repo} | {stars} | [GitHub]({link}) |\n"
    return table

def get_best_papers(topK) -> str:
    """
    Returns a markdown table for the top papers (by citation count) found in the projects.
    """
    papers = {}
    for project in load_projects():
        for link in project['links']:
            if link[0] == 'doi':
                doi_link = link[1]
                citations = link[2]
                paper_title = project['name']
                if doi_link not in papers or citations > papers[doi_link][1]:
                    papers[doi_link] = (paper_title, citations)
                break
    papers_sorted = sorted(
        [(title, doi, citations) for doi, (title, citations) in papers.items()],
        key=lambda x: x[2], reverse=True
    )[:topK]
    table = "| Paper | Citations | Link |\n"
    table += "|---|---|---|\n"
    for title, doi, citations in papers_sorted:
        link_md = doi_url(doi)
        table += f"| {title} | {citations} | {link_md} |\n"
    return table

def get_best_packages(packages, topK) -> str:
    """
    Returns a markdown table for the top packages (by total downloads) from the PyPI stats.
    """
    packages_sorted = sorted(packages, key=lambda x: x[2], reverse=True)[:topK]
    table = "| Package | Downloads Last Month | Total Downloads | Link |\n"
    table += "|---|---|---|---|\n"
    for package, last_month, total in packages_sorted:
        table += f"| {package} | {last_month} | {total} | {pypi_url(package)} |\n"
    return table

def generate_table(fn: str, num_visible_authors: int):
    data = read_json(fn)
    colabs = sorted(data, key=lambda kv: kv['update'], reverse=True)
    to_write = [
        '| name | description | authors | links | colaboratory | update |',
        '|------|-------------|:--------|:------|:------------:|:------:|',
    ]
    for line in colabs:
        line['author'] = parse_authors(line['author'], num_visible_authors)
        line['links'] = parse_links(sorted(line['links'], key=lambda x: x[0]))
        line['url'] = colab_url(line['colab'])
        line['update'] = datetime.fromtimestamp(line['update']).strftime('%d.%m.%Y')
        to_write.append('| {name} | {description} | {author} | {links} | {url} | {update} |'.format(**line))
    return to_write

def safe_get_stat(stat_func, package, retries=3, sleep_time=3, **kwargs):
    """
    Attempts to retrieve stats for a given package using stat_func.
    In case of HTTP errors (e.g. 429 Too Many Requests), it waits and retries.
    """
    for attempt in range(retries):
        try:
            return stat_func(package, **kwargs)
        except HTTPStatusError as e:
            print(f"Error retrieving stats for package '{package}': {e}. Attempt {attempt + 1} of {retries}.")
            if attempt < retries - 1:
                time.sleep(sleep_time)
            else:
                return None

def get_pypi_downloads(engine: str = 'pypistats'):
    packages = set()
    for project in load_projects():
        for url in project['links']:
            if url[0] == 'pypi':
                packages.add(url[1].rstrip('/').split('/')[-1])
    if engine == 'bigquery':
        def get_query(date_filtering: str) -> str:
            return f"""
            SELECT
                file.project,
                COUNT(*) AS num_downloads
            FROM
                `bigquery-public-data.pypi.file_downloads`
            WHERE
                file.project IN ('{"', '".join(packages)}')
                AND DATE(timestamp) BETWEEN {date_filtering}
            GROUP BY
                file.project
            """
        client = bigquery.Client()
        last_month = 'DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 MONTH) AND DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 DAY)'
        total = 'DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR) AND CURRENT_DATE()'
        query_last_month = client.query(get_query(last_month))
        query_total = client.query(get_query(total))
        res_last_month = {row.project: row.num_downloads for row in query_last_month.result()}
        res_total = {row.project: row.num_downloads for row in query_total.result()}
        return [(package, res_last_month.get(package, 0), res_total.get(package, 0)) for package in packages]

    downloads = []
    for package in tqdm(packages, desc="Retrieving PyPI stats"):
        recent_stats = safe_get_stat(recent, package, format='pandas')
        overall_stats = safe_get_stat(overall, package, format='pandas')
        try:
            last_month = int(recent_stats.last_month) if recent_stats is not None else 0
        except Exception as e:
            print(f"Error parsing recent stats for {package}: {e}")
            last_month = 0
        try:
            if overall_stats is not None:
                overall_df = overall_stats.query('category == "Total"')
                total = int(overall_df.iloc[0]['downloads']) if not overall_df.empty else 0
            else:
                total = 0
        except Exception as e:
            print(f"Error parsing overall stats for {package}: {e}")
            total = 0
        downloads.append((package, last_month, total))
    return downloads

def generate_trending_dashboard(topK: int, packages):
    """
    Generates a dashboard plot showing trending repositories, papers, and packages.
    The trending metric is computed as the ratio of current value (stars, citations, or downloads)
    to the previous (old) value.
    """
    old_stars = read_json('data/stars.json')
    old_citations = read_json('data/citations.json')
    new_stars = {}
    new_citations = {}
    for project in load_projects():
        used = set()
        for link in project['links']:
            if link[0] == 'git' and 'git' not in used:
                _, url, stars = link
                parts = url.split('/')
                if len(parts) >= 5:
                    repo = parts[3] + '/' + parts[4]
                else:
                    repo = url
                new_stars[repo] = stars
                used.add('git')
            elif link[0] == 'doi' and 'doi' not in used:
                new_citations[project['name']] = (link[1], link[2])
                used.add('doi')

    trending_repos = []
    for repo, stars in new_stars.items():
        old = old_stars.get(repo, float('inf'))
        ratio = stars / old if old not in [0, float('inf')] else stars
        trending_repos.append((repo, ratio, stars, old))
    trending_repos.sort(key=lambda x: x[1], reverse=True)
    trending_repos = trending_repos[:topK]

    trending_papers = []
    for paper, (doi, citations) in new_citations.items():
        old_cit = old_citations.get(paper, ['', float('inf')])[1]
        old_cit = max(old_cit, 1)
        ratio = citations / old_cit if old_cit != 0 else citations
        trending_papers.append((paper, ratio, citations, old_cit))
    trending_papers.sort(key=lambda x: x[1], reverse=True)
    trending_papers = trending_papers[:topK]

    trending_packages = []
    for package, last_month, total in packages:
        denom = total - last_month
        ratio = last_month / denom if denom > 0 else last_month
        trending_packages.append((package, ratio, last_month, total))
    trending_packages.sort(key=lambda x: x[1], reverse=True)
    trending_packages = trending_packages[:topK]

    fig, axs = plt.subplots(1, 3, figsize=(18, 6))

    repo_names = [r[0] for r in trending_repos]
    repo_ratios = [r[1] for r in trending_repos]
    axs[0].barh(repo_names, repo_ratios, color='skyblue')
    axs[0].set_title('Trending Repositories')
    axs[0].set_xlabel('Stars Increase Ratio')
    axs[0].invert_yaxis()

    paper_names = [p[0] for p in trending_papers]
    paper_ratios = [p[1] for p in trending_papers]
    axs[1].barh(paper_names, paper_ratios, color='lightgreen')
    axs[1].set_title('Trending Papers')
    axs[1].set_xlabel('Citations Increase Ratio')
    axs[1].invert_yaxis()

    package_names = [p[0] for p in trending_packages]
    package_ratios = [p[1] for p in trending_packages]
    axs[2].barh(package_names, package_ratios, color='salmon')
    axs[2].set_title('Trending Packages')
    axs[2].set_xlabel('Downloads Increase Ratio')
    axs[2].invert_yaxis()

    plt.tight_layout()
    dashboard_path = join('./images', 'dashboard.png')
    plt.savefig(dashboard_path)
    plt.close(fig)

def generate_markdown():
    top_authors, num_visible_authors = get_top_authors(TOP_K)
    packages = get_pypi_downloads()
    generate_trending_dashboard(TOP_K, packages)
    now = datetime.now()
    best_header = f"# The best for now {now.strftime('%B %Y')}:"
    collection_title = "# Some notebooks collection that you should know."

    # Reordering: the top of the file will have only the best_header,
    # and the following items will be appended at the end.
    to_write = [
        best_header,
        # Repository/Paper/Package section
        "### Repositories",
        get_best_repositories(TOP_K),
        "### Papers",
        get_best_papers(TOP_K),
        "### Packages",
        get_best_packages(packages, TOP_K),
        #"\n[![Stargazers over time](https://starchart.cc/amrzv/awesome-colab-notebooks.svg?variant=adaptive)](https://starchart.cc/amrzv/awesome-colab-notebooks)",
        #"\n(generated by [generate_markdown.py](generate_markdown.py) based on [research.json](data/research.json), [tutorials.json](data/tutorials.json), [cources.json](data/cources.json))",
        # Moved information at the end
        collection_title,
        '[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://github.com/amrzv/awesome-colab-notebooks)](https://hits.seeyoufarm.com)',
        #'![awesome-colab-notebooks](https://count.getloli.com/get/@awesome-colab-notebooks?theme=rule34)\n',
        '[![Word Cloud](./images/cloud.svg)](./images/cloud.svg)',
        #"\nThe page might not be rendered properly. Please open [README.md](https://github.com/amrzv/awesome-colab-notebooks/blob/main/README.md) file directly",
        "## Trending Dashboard",
        "![Trending Dashboard](./images/dashboard.png)",
        "## Cources",
        "<details>\n<summary>COURCES</summary>\n",
        *generate_table(join('data', 'cources.json'), num_visible_authors),
        "\n</details>\n",
        "## Research",
        "<details>\n<summary>RESEARCH</summary>\n",
        *generate_table(join('data', 'research.json'), num_visible_authors),
        "\n</details>\n",
        "## Tutorials",
        "<details>\n<summary>TUTORIALS</summary>\n",
        *generate_table(join('data', 'tutorials.json'), num_visible_authors),
        "\n</details>\n"
    ]
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(to_write))

def main():
    generate_markdown()

if __name__ == '__main__':
    main()

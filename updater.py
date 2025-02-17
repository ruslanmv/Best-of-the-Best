import json
import time
import requests
from pathlib import Path

# Define file paths
data_dir = Path("data")
citations_file = data_dir / "citations.json"
stars_file = data_dir / "stars.json"
courses_file = data_dir / "cources.json"
research_file = data_dir / "research.json"
tutorials_file = data_dir / "tutorials.json"

# Define APIs
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/v1/paper/"
GITHUB_API = "https://api.github.com/repos/"


def update_citations():
    """Updates citation counts from Semantic Scholar or CrossRef."""
    if not citations_file.exists():
        print("Citations file not found.")
        return
    
    with open(citations_file, "r", encoding="utf-8") as f:
        citations = json.load(f)
    
    for paper, data in citations.items():
        doi = data[0].split("doi.org/")[-1]
        response = requests.get(SEMANTIC_SCHOLAR_API + doi)
        if response.status_code == 200:
            result = response.json()
            citations[paper][1] = result.get("citationCount", data[1])
            print(f"Updated citations for {paper}: {citations[paper][1]}")
        time.sleep(1)
    
    with open(citations_file, "w", encoding="utf-8") as f:
        json.dump(citations, f, indent=4)
    

def update_github_stars():
    """Updates GitHub star counts."""
    if not stars_file.exists():
        print("Stars file not found.")
        return
    
    with open(stars_file, "r", encoding="utf-8") as f:
        stars = json.load(f)
    
    for repo_url in stars.keys():
        repo_name = "/".join(repo_url.split("/")[-2:])
        response = requests.get(GITHUB_API + repo_name)
        if response.status_code == 200:
            stars[repo_url] = response.json().get("stargazers_count", stars[repo_url])
            print(f"Updated stars for {repo_name}: {stars[repo_url]}")
        time.sleep(1)
    
    with open(stars_file, "w", encoding="utf-8") as f:
        json.dump(stars, f, indent=4)
    

def update_json_data(json_file):
    """Generic function to update JSON files."""
    if not json_file.exists():
        print(f"{json_file} not found.")
        return
    
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for entry in data:
        entry["update"] = time.time()
    
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    
    print(f"Updated timestamps in {json_file.name}")
    

def main():
    print("Updating citations...")
    update_citations()
    print("Updating GitHub stars...")
    update_github_stars()
    print("Updating courses, research, and tutorials...")
    update_json_data(courses_file)
    update_json_data(research_file)
    update_json_data(tutorials_file)
    print("Update completed.")


if __name__ == "__main__":
    main()

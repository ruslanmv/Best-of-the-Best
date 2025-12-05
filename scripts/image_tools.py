import os
import requests
import matplotlib.pyplot as plt
from datetime import datetime
from crewai_tools import tool
from playwright.sync_api import sync_playwright

# 1. SETUP FOR HEADLESS ENVIRONMENTS
# Essential for running in GitHub Actions/Docker where no display exists
import matplotlib
matplotlib.use('Agg') 

# Define assets directory relative to the workspace
ASSETS_DIR = os.path.join(os.getcwd(), "assets", "images")
os.makedirs(ASSETS_DIR, exist_ok=True)

class ImageTools:
    
    @tool("Search and Download Stock Photo")
    def get_stock_photo(query: str):
        """
        Searches Pexels for a stock photo and downloads it.
        Useful for blog headers or generic illustrative content.
        Requires 'PEXELS_API_KEY' env var.
        """
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            return "Error: PEXELS_API_KEY not found. Cannot download stock photo."
        
        headers = {"Authorization": api_key}
        # Searching for landscape orientation suitable for blog headers
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=1&orientation=landscape"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("photos"):
                image_url = data["photos"][0]["src"]["large2x"] # High quality
                
                # Sanitize filename
                safe_query = "".join([c for c in query if c.isalnum() or c in (' ','-','_')]).strip().replace(' ', '_')
                filename = f"{safe_query}_{datetime.now().strftime('%H%M%S')}.jpg"
                filepath = os.path.join(ASSETS_DIR, filename)
                
                img_data = requests.get(image_url, timeout=20).content
                with open(filepath, 'wb') as handler:
                    handler.write(img_data)
                    
                return filepath
            return "No images found for this query."
        except Exception as e:
            return f"Error downloading stock photo: {str(e)}"

    @tool("Generate Architecture Diagram")
    def generate_architecture_diagram(python_code: str):
        """
        Executes Python code to generate a cloud architecture diagram using the 'diagrams' library.
        
        CRITICAL RULES FOR CODE GENERATION:
        1. Import all necessary classes inside the code.
        2. Use `with Diagram("Name", show=False, filename="assets/images/output_name"):` 
        3. YOU MUST set `show=False` or the agent will crash in CI/CD.
        4. YOU MUST set the filename path to start with 'assets/images/'.
        """
        try:
            # We explicitly pass the current global context to allow imports to work
            # Warning: exec() is dangerous; ensure input is from your trusted Agent only.
            exec_globals = {}
            exec(python_code, exec_globals)
            
            # Since 'diagrams' doesn't return the path, we assume success if no error raised.
            # The agent should have named the file in the code as requested.
            return f"Diagram generation code executed. Check {ASSETS_DIR} for output files."
        except Exception as e:
            return f"Error generating diagram: {str(e)}\nHint: Did you forget to install graphviz in the workflow?"

    @tool("Create Data Chart")
    def create_chart(x_values: list, y_values: list, title: str, x_label: str, y_label: str, style: str = "xkcd"):
        """
        Generates a line chart for data visualization.
        Args:
            x_values: List of items (e.g. ["Jan", "Feb"])
            y_values: List of numbers (e.g. [10, 20])
            style: 'xkcd' for sketch style, 'standard' for professional style.
        """
        filename = f"chart_{datetime.now().strftime('%H%M%S')}.png"
        filepath = os.path.join(ASSETS_DIR, filename)
        
        try:
            # Context manager for style to prevent leaking style to other plots
            if style == "xkcd":
                # Fallback mechanism: XKCD style requires fonts that might be missing in CI
                try:
                    with plt.xkcd():
                        ImageTools._plot_logic(x_values, y_values, title, x_label, y_label, filepath)
                except Exception:
                    # Fallback to standard if XKCD fails (common in headless Linux)
                    print("XKCD font missing, falling back to standard style.")
                    ImageTools._plot_logic(x_values, y_values, title, x_label, y_label, filepath)
            else:
                # Standard style
                ImageTools._plot_logic(x_values, y_values, title, x_label, y_label, filepath)
                
            return filepath
        except Exception as e:
            return f"Error creating chart: {str(e)}"

    @staticmethod
    def _plot_logic(x, y, title, xlabel, ylabel, path):
        """Helper to keep plotting logic consistent"""
        plt.figure(figsize=(10, 6))
        plt.plot(x, y, marker='o')
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()

    @tool("Take Website Screenshot")
    def take_screenshot(url: str, filename_prefix: str = "screenshot"):
        """
        Takes a screenshot of a URL using headless Chromium.
        """
        filename = f"{filename_prefix}_{datetime.now().strftime('%H%M%S')}.png"
        filepath = os.path.join(ASSETS_DIR, filename)
        
        try:
            with sync_playwright() as p:
                # Launch options specifically for CI/CD containers
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                # Setup context with a realistic viewport size
                context = browser.new_context(viewport={'width': 1280, 'height': 720})
                page = context.new_page()
                
                page.goto(url, timeout=30000) # 30s timeout
                page.screenshot(path=filepath)
                
                browser.close()
            return filepath
        except Exception as e:
            return f"Error taking screenshot: {str(e)}"

# Export for CrewAI
image_toolkit = [
    ImageTools.get_stock_photo,
    ImageTools.generate_architecture_diagram,
    ImageTools.create_chart,
    ImageTools.take_screenshot
]
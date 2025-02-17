from flask import Flask, render_template_string
import os
from pyngrok import ngrok

app = Flask(__name__)

# Function to read and return the README content
def read_readme():
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h3 style='color:red;'>❌ README.md not found. Please upload or create this file.</h3>"
    except Exception as e:
        return f"<h3 style='color:red;'>⚠️ An error occurred: {e}</h3>"

@app.route('/')
def display_readme():
    readme_content = read_readme()
    html_template = f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>README.md Viewer</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>📖 README.md Viewer</h1>
        <div>{readme_content}</div>
    </body>
    </html>
    """
    return render_template_string(html_template)

if __name__ == "__main__":
    # Set up ngrok authentication using os.system
    NGROK_TOKEN = os.getenv("NGROK_TOKEN")
    if NGROK_TOKEN:
        os.system(f"ngrok authtoken {NGROK_TOKEN}")
    else:
        print("Please add your NGROK_TOKEN in environment variables.")
    
    # Start Flask app in the background
    port = 5000
    public_url = ngrok.connect(port).public_url
    print(f"Flask app running at: {public_url}")
    os.system(f"flask run --host=0.0.0.0 --port={port} --debug")

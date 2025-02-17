import subprocess
import sys
import os

def install_packages():
    """Installs required packages based on the environment."""
    try:
        # Check if running in Google Colab
        import google.colab
        in_colab = True
    except ImportError:
        in_colab = False

    if in_colab:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit", "pyngrok"])
    else:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])  # Standard installation


install_packages()  # Install packages before importing

import streamlit as st

# Write the Streamlit app code to app.py
app_code = """\
import streamlit as st

st.title("Best of the Best")
st.write("")

try:
    with open("README.md", "r") as f:
        readme_content = f.read()
    st.markdown(readme_content, unsafe_allow_html=True)

except FileNotFoundError:
    st.error("README.md not found. Please upload or create this file.")

except Exception as e:
    st.error(f"An error occurred: {e}")
"""

# Save the Streamlit app code to app.py
with open("app.py", "w") as f:
    f.write(app_code)


def start_streamlit():
    """Starts the Streamlit app, using ngrok if in Colab."""
    try:
        # Check if running in Google Colab
        import google.colab
        in_colab = True
    except ImportError:
        in_colab = False

    if in_colab:
        from pyngrok import ngrok
        # Set up ngrok for tunneling
        from google.colab import userdata

        NGROK_TOKEN = userdata.get('NGROK_TOKEN')  # Fetch token from Colab secrets
        if NGROK_TOKEN:
            ngrok.set_auth_token(NGROK_TOKEN)  # Use ngrok.set_auth_token
            # Run Streamlit in the background
            subprocess.Popen(["streamlit", "run", "app.py", "--server.port=8501"]) # Use subprocess.Popen

            # Open a public URL with ngrok
            public_url = ngrok.connect(8501).public_url
            print(f"Streamlit app running at: {public_url}")
        else:
            print("Please add your NGROK_TOKEN in Colab secrets.")

    else:
        # Run Streamlit normally (no ngrok needed)
        subprocess.Popen(["streamlit", "run", "app.py"])  # Use subprocess.Popen
        print("Streamlit app running locally. Access it at http://localhost:8501")

# Run Streamlit
start_streamlit()
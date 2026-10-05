"""Streamlit frontend.  Run:  streamlit run frontend/app.py"""
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="GitHub Repo Explainer", page_icon="🧠", layout="wide")
st.title("🧠 GitHub Repository Code Explainer")
st.caption("Paste a GitHub URL. A local LLM reads the code and explains it in simple language.")

with st.sidebar:
    st.header("Pipeline")
    st.markdown("GitHub repo → clone → pick files → local LLM → FastAPI → Streamlit")
    api = st.text_input("Backend URL", API_URL)
    if st.button("Check backend"):
        try:
            h = requests.get(f"{api}/health", timeout=5).json()
            st.success(f"Backend OK • model: {h['model']}")
        except Exception as e:
            st.error(f"Backend not reachable: {e}")

url = st.text_input("GitHub repository URL", placeholder="https://github.com/username/repository")

if st.button("Explain this repository", type="primary"):
    if not url.strip():
        st.warning("Please enter a repository URL.")
    else:
        with st.spinner("Cloning repository and asking the local LLM... (can take a minute or two)"):
            try:
                resp = requests.post(f"{api}/explain", json={"repo_url": url}, timeout=900)
            except requests.RequestException as e:
                st.error(f"Could not reach the backend: {e}")
                st.stop()

        if resp.status_code == 200:
            data = resp.json()
            st.markdown(data["explanation"])
            st.divider()
            c1, c2 = st.columns(2)
            c1.metric("Model", data["model"])
            c2.metric("Files analysed", len(data["files_analyzed"]))
            with st.expander("Languages detected"):
                st.write(", ".join(data["languages"]) or "—")
            with st.expander("Files sent to the LLM"):
                st.code("\n".join(data["files_analyzed"]))
        else:
            detail = resp.json().get("detail", resp.text)
            if isinstance(detail, list):  # pydantic validation errors
                detail = detail[0].get("msg", str(detail))
            st.error(detail)

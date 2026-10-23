import json
import yaml
import streamlit as st
import trafilatura
from bs4 import BeautifulSoup
from urllib.parse import urljoin

st.set_page_config(page_title="EPL Social Media Manager", page_icon="⚽", layout="wide")

# Simple password gate (Optional protection so only your friend can log in)
st.sidebar.auth = st.sidebar.text_type = "Access Control"
password_input = st.sidebar.text_input("Enter Access Password:", type="password")

# Set your secret app password here
APP_PASSWORD = "eplpassword123" 

if password_input != APP_PASSWORD:
    st.title("🔒 Restricted Access")
    st.warning("Please enter the correct password in the sidebar to access the social media crawler.")
    st.stop()

st.title("⚽ EPL Social Media Post Generator")
st.markdown("Select a team below, fetch the latest articles, and grab your copy-paste-ready Facebook posts.")

# Load configuration locally or embedded
def load_config():
    try:
        with open("teams_config.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception:
        # Fallback config if yaml isn't found online
        return {
            "arsenal": {
                "page_name": "Arsenal FC Fans",
                "sources": ["https://www.bbc.com/sport/football/teams/arsenal"]
            },
            "liverpool": {
                "page_name": "Liverpool FC News",
                "sources": ["https://www.bbc.com/sport/football/teams/liverpool"]
            }
        }

config = load_config()
team_keys = list(config.keys())

selected_team_key = st.selectbox("Choose a Team:", team_keys, format_func=lambda x: config[x]['page_name'])
target_limit = st.slider("Number of posts to fetch:", 1, 10, 5)

if st.button("🚀 Fetch & Format Posts", type="primary"):
    data = config[selected_team_key]
    st.info(f"Scraping latest updates for {data['page_name']}...")
    
    collected_posts = []
    
    for source in data['sources']:
        if len(collected_posts) >= target_limit:
            break
        try:
            downloaded = trafilatura.fetch_url(source)
            if not downloaded:
                continue
            soup = BeautifulSoup(downloaded, 'html.parser')
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if any(term in href for term in ['/sport/', '/news/', '/article/']):
                    links.add(urljoin(source, href))
            
            for url in links:
                if len(collected_posts) >= target_limit:
                    break
                
                json_output = trafilatura.extract(downloaded if url == source else trafilatura.fetch_url(url), output_format='json', with_metadata=True)
                if not json_output:
                    continue
                
                art_data = json.loads(json_output) if isinstance(json_output, str) else json_output
                if isinstance(art_data, dict) and art_data.get("title"):
                    title = art_data.get("title").strip()
                    text_content = " ".join((art_data.get("text", "") or "").split())
                    snippet = text_content[:300] + "..." if len(text_content) > 300 else text_content
                    
                    post_text = f"""🚨 {selected_team_key.upper()} UPDATE 🚨\n\n📌 {title}\n\n{snippet}\n\n🔗 Read more: {url}\n\n👇 What are your thoughts on this? Drop them in the comments below!\n\n#{selected_team_key.capitalize()} #PremierLeague #EPL #FootballFans"""
                    
                    collected_posts.append(post_text)
        except Exception as e:
            st.error(f"Error reading source: {e}")
            
    if collected_posts:
        st.success(f"Successfully generated {len(collected_posts)} posts!")
        for idx, post in enumerate(collected_posts, 1):
            with st.expander(f"Post #{idx} Preview"):
                st.text_area(f"Copy Box {idx}", post, height=200)
    else:
        st.warning("No posts found. Try checking your source links in `teams_config.yaml`.")

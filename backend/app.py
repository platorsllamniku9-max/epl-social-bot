import json
import yaml
from pathlib import Path
import streamlit as st
import trafilatura
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- PAGE CONFIGURATION (MOBILE-FIRST) ---
st.set_page_config(
    page_title="EPL Social Hub",
    page_icon="⚽",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- AESTHETIC MOBILE CSS ---
st.markdown("""
    <style>
    /* Dark Mode Core Theme */
    .stApp {
        background-color: #0d0f12;
        color: #f3f4f6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Hide Default Header/Footer Chrome for Native App Feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }

    /* Mobile Header Badge */
    .mobile-header {
        background: linear-gradient(135deg, #38003c 0%, #1c001e 100%);
        border: 1px solid #520059;
        border-radius: 18px;
        padding: 16px;
        text-align: center;
        margin-bottom: 16px;
        box-shadow: 0 8px 24px rgba(56, 0, 60, 0.4);
    }
    .mobile-header h1 {
        color: #00ff85;
        font-size: 1.5rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .mobile-header p {
        color: #d1d5db;
        font-size: 0.8rem;
        margin-top: 4px;
        margin-bottom: 0;
    }

    /* Custom Mobile Cards */
    .post-card {
        background: #161a22;
        border: 1px solid #262c36;
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .post-badge {
        background-color: #00ff85;
        color: #38003c;
        font-weight: 800;
        font-size: 0.7rem;
        padding: 3px 10px;
        border-radius: 12px;
        text-transform: uppercase;
    }

    /* Primary Touch Buttons */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00ff85 0%, #00cc6a 100%) !important;
        color: #38003c !important;
        font-weight: 800 !important;
        font-size: 1.05rem !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 14px 20px !important;
        width: 100% !important;
        box-shadow: 0 4px 16px rgba(0, 255, 133, 0.3) !important;
    }

    /* Secondary Buttons */
    div.stButton > button[kind="secondary"] {
        background-color: #212631 !important;
        color: #ffffff !important;
        border: 1px solid #343b4d !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        width: 100% !important;
    }

    /* Input & Tab Label Polish */
    .stSelectbox label, .stSlider label {
        color: #9ca3af !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161a22;
        border-radius: 10px;
        padding: 8px 16px;
        color: #9ca3af;
    }
    .stTabs [aria-selected="true"] {
        background-color: #38003c !important;
        color: #00ff85 !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

CONFIG_PATH = Path("teams_config.yaml")

# --- DEFAULT FALLBACK CONFIGURATION ---
DEFAULT_CONFIG = {
    "arsenal": {
        "page_name": "Arsenal FC Central",
        "sources": [
            "https://www.bbc.com/sport/football/teams/arsenal",
            "https://www.skysports.com/arsenal-news"
        ]
    },
    "liverpool": {
        "page_name": "Liverpool FC Pulse",
        "sources": [
            "https://www.bbc.com/sport/football/teams/liverpool",
            "https://www.skysports.com/liverpool-news"
        ]
    },
    "mancity": {
        "page_name": "Manchester City Hub",
        "sources": [
            "https://www.bbc.com/sport/football/teams/manchester-city"
        ]
    }
}

# --- CONFIG LOADER & WRITER ---
def load_config():
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        from ruamel.yaml import YAML
        yaml_loader = YAML(typ='safe')
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml_loader.load(f) or DEFAULT_CONFIG
    except Exception:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or DEFAULT_CONFIG
        except Exception:
            return DEFAULT_CONFIG

def save_config(config_data):
    try:
        from ruamel.yaml import YAML
        yaml_writer = YAML()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml_writer.dump(config_data, f)
    except Exception:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False)

# --- FAST CRAWLER ---
def fetch_team_posts(team_key, sources, target_limit=10):
    collected_posts = []
    seen_links = set()

    for source in sources:
        if len(collected_posts) >= target_limit:
            break
        try:
            downloaded = trafilatura.fetch_url(source)
            if not downloaded:
                continue

            soup = BeautifulSoup(downloaded, 'html.parser')
            for a in soup.find_all('a', href=True):
                if len(collected_posts) >= target_limit:
                    break

                href = a['href']
                if any(term in href for term in ['/sport/', '/news/', '/article/']):
                    full_url = urljoin(source, href)
                    if full_url in seen_links:
                        continue
                    seen_links.add(full_url)

                    art_data = trafilatura.extract(
                        trafilatura.fetch_url(full_url),
                        output_format='json',
                        with_metadata=True
                    )
                    if not art_data:
                        continue

                    parsed = json.loads(art_data) if isinstance(art_data, str) else art_data
                    if isinstance(parsed, dict) and parsed.get("title"):
                        title = parsed.get("title").strip()
                        text_body = " ".join((parsed.get("text", "") or "").split())
                        snippet = text_body[:280] + "..." if len(text_body) > 280 else text_body

                        if len(snippet) < 40:
                            continue

                        formatted_post = (
                            f"🚨 {team_key.upper()} UPDATE 🚨\n\n"
                            f"📌 {title}\n\n"
                            f"{snippet}\n\n"
                            f"🔗 Read full story: {full_url}\n\n"
                            f"👇 What are your thoughts on this? Drop them below!\n\n"
                            f"#{team_key.capitalize()} #PremierLeague #EPL #Football"
                        )

                        collected_posts.append({
                            "title": title,
                            "url": full_url,
                            "text": formatted_post
                        })
        except Exception:
            continue

    return collected_posts

# --- INITIALIZATION ---
if 'config' not in st.session_state:
    st.session_state['config'] = load_config()

config = st.session_state['config']
team_keys = list(config.keys())

# --- HEADER ---
st.markdown("""
    <div class="mobile-header">
        <h1>⚽ EPL Social Hub</h1>
        <p>1-Click Mobile Post Generator</p>
    </div>
""", unsafe_allow_html=True)

# --- NATIVE TABS FOR MOBILE NAVIGATION ---
tab_composer, tab_config = st.tabs(["🚀 Post Generator", "⚙️ Team Manager"])

# ==========================================
# TAB 1: POST GENERATOR
# ==========================================
with tab_composer:
    st.markdown("### 1️⃣ Choose Club & Count")

    selected_team_key = st.selectbox(
        "Select Club",
        team_keys,
        format_func=lambda x: config[x].get('page_name', x.capitalize())
    )

    post_limit = st.slider(
        "Fetch count (up to 10)",
        min_value=1,
        max_value=10,
        value=5
    )

    st.write("")

    if st.button("⚡ Fetch & Generate Posts", type="primary", use_container_width=True):
        with st.spinner("Scraping live team news..."):
            sources = config[selected_team_key].get('sources', [])
            posts = fetch_team_posts(selected_team_key, sources, target_limit=post_limit)
            st.session_state['generated_posts'] = posts
            st.session_state['current_team'] = config[selected_team_key].get('page_name', selected_team_key)

    if 'generated_posts' in st.session_state and st.session_state['generated_posts']:
        st.markdown("---")
        st.markdown(f"### 2️⃣ Posts for {st.session_state['current_team']}")
        st.caption(f"Fetched {len(st.session_state['generated_posts'])} posts. Tap inside any box below to select and copy!")

        for idx, item in enumerate(st.session_state['generated_posts'], 1):
            st.markdown(f"""
                <div class="post-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span class="post-badge">Option #{idx}</span>
                    </div>
                    <strong style="color:#ffffff; font-size:0.95rem;">{item['title']}</strong>
                </div>
            """, unsafe_allow_html=True)

            st.text_area(
                f"Copy Box #{idx}",
                value=item['text'],
                height=160,
                key=f"post_text_{idx}",
                label_visibility="collapsed"
            )
            st.write("")
    elif 'generated_posts' in st.session_state:
        st.warning("No articles found right now. Try selecting another team or re-running!")

# ==========================================
# TAB 2: TEAM CONFIG MANAGER
# ==========================================
with tab_config:
    st.markdown("### ⚙️ Club Configuration")
    
    selected_edit_key = st.selectbox(
        "Select Club to Edit",
        team_keys,
        format_func=lambda x: config[x].get('page_name', x.capitalize()),
        key="edit_select"
    )

    if selected_edit_key in config:
        club_data = config[selected_edit_key]
        
        updated_name = st.text_input("Display Name", value=club_data.get("page_name", ""))
        existing_sources = club_data.get("sources", [])
        sources_text = st.text_area("Source URLs (One per line)", value="\n".join(existing_sources))

        if st.button("💾 Save Config", type="primary", use_container_width=True):
            parsed_sources = [s.strip() for s in sources_text.split("\n") if s.strip()]
            config[selected_edit_key] = {
                "page_name": updated_name,
                "sources": parsed_sources
            }
            save_config(config)
            st.session_state['config'] = config
            st.success("Saved config successfully!")
            st.rerun()

    st.markdown("---")
    st.markdown("### ➕ Add New Club")
    new_key = st.text_input("New Club Key (e.g. 'chelsea')").lower().strip()
    new_name = st.text_input("Display Name (e.g. 'Chelsea FC Hub')")
    
    if st.button("➕ Add Club", use_container_width=True):
        if new_key and new_name and new_key not in config:
            config[new_key] = {
                "page_name": new_name,
                "sources": ["https://www.bbc.com/sport/football"]
            }
            save_config(config)
            st.session_state['config'] = config
            st.success(f"Added {new_name}!")
            st.rerun()
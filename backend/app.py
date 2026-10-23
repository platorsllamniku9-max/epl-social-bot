import json
import yaml
from pathlib import Path
import streamlit as st
import trafilatura
import feedparser

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="EPL Social Media Manager",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS STYLING ---
st.markdown("""
    <style>
    /* Global Styling */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Social Media Preview Cards */
    .preview-card {
        border-radius: 12px;
        padding: 16px;
        margin-top: 10px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .x-card {
        background-color: #000000;
        color: #ffffff;
        border: 1px solid #2f3336;
    }
    
    .li-card {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #e0e0e0;
    }

    .fb-card {
        background-color: #ffffff;
        color: #050505;
        border: 1px solid #ced0d4;
    }

    .ig-card {
        background-color: #ffffff;
        color: #262626;
        border: 1px solid #dbdbdb;
    }

    /* Primary Accent Buttons */
    div.stButton > button[kind="primary"] {
        background-color: #00ff85 !important;
        color: #38003c !important;
        font-weight: 700 !important;
        border: none !important;
    }
    </style>
""", unsafe_allow_html=True)

CONFIG_PATH = Path("teams_config.yaml")

# --- DEFAULT FALLBACK CONFIGURATION ---
DEFAULT_CONFIG = {
    "arsenal": {
        "page_name": "Arsenal FC Central",
        "handle": "@Arsenal",
        "avatar": "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=100&auto=format&fit=crop&q=80",
        "hashtags": ["#AFC", "#COYG", "#Arsenal", "#PremierLeague"],
        "default_footer": "👇 What are your thoughts on Gunners' latest performance?",
        "sources": [
            "https://www.bbc.com/sport/football/teams/arsenal",
            "https://www.skysports.com/arsenal-news"
        ]
    },
    "liverpool": {
        "page_name": "Liverpool FC Pulse",
        "handle": "@LFC",
        "avatar": "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=100&auto=format&fit=crop&q=80",
        "hashtags": ["#LFC", "#YNWA", "#Liverpool", "#PremierLeague"],
        "default_footer": "🔴 Up the Reds! Drop your comments below!",
        "sources": [
            "https://www.bbc.com/sport/football/teams/liverpool",
            "https://www.skysports.com/liverpool-news"
        ]
    }
}

# --- YAML CONFIG ENGINE ---
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

# --- SCRAPER & INGESTION ENGINE ---
def extract_article_details(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {}
        extracted_json = trafilatura.extract(
            downloaded,
            output_format="json",
            with_metadata=True,
            include_images=True
        )
        if extracted_json:
            return json.loads(extracted_json)
    except Exception as e:
        st.error(f"Error scraping URL: {e}")
    return {}

def parse_rss_or_web(club_key, urls, limit=5):
    results = []
    for source_url in urls:
        if len(results) >= limit:
            break
        feed = feedparser.parse(source_url)
        if feed.entries:
            for entry in feed.entries[:limit]:
                if len(results) >= limit:
                    break
                link = entry.get("link", source_url)
                title = entry.get("title", "EPL Match Update")
                summary = entry.get("summary", entry.get("description", ""))
                clean_summary = trafilatura.html2txt(summary) if summary else ""

                results.append({
                    "id": f"rss_{abs(hash(link))}",
                    "club_key": club_key,
                    "title": title,
                    "source_domain": entry.get("author", "RSS Feed"),
                    "published_time": entry.get("published", "Recently"),
                    "summary": clean_summary[:300] if clean_summary else "Click to read full story.",
                    "article_url": link,
                    "image_url": None
                })
        else:
            data = extract_article_details(source_url)
            if data and data.get("title"):
                text_body = data.get("text", "")
                results.append({
                    "id": f"web_{abs(hash(source_url))}",
                    "club_key": club_key,
                    "title": data.get("title"),
                    "source_domain": data.get("hostname", "News Outlet"),
                    "published_time": data.get("date", "Today"),
                    "summary": text_body[:300] + "..." if len(text_body) > 300 else text_body,
                    "article_url": source_url,
                    "image_url": data.get("image")
                })
    return results

# --- SESSION STATE INITS ---
if "config" not in st.session_state:
    st.session_state.config = load_config()

if "composer_text" not in st.session_state:
    st.session_state.composer_text = ""

if "composer_media_url" not in st.session_state:
    st.session_state.composer_media_url = ""

if "active_club" not in st.session_state:
    st.session_state.active_club = list(st.session_state.config.keys())[0] if st.session_state.config else "arsenal"

# --- SIDEBAR ---
st.sidebar.title("⚽ EPL Social Hub")
st.sidebar.caption("Content Operations Platform")

view_option = st.sidebar.radio(
    "Navigation Mode",
    ["Interactive Composer", "RSS & Feed Ingestion Board", "Team Config Editor"],
    index=0
)

st.sidebar.divider()
st.sidebar.metric("Active Teams Configured", len(st.session_state.config))

# ==============================================================================
# TIER 1: INTERACTIVE POST COMPOSER
# ==============================================================================
if view_option == "Interactive Composer":
    st.title("📝 Interactive Post Composer")
    st.caption("Draft once, visualize live rendering previews across multiple social platforms.")

    col_editor, col_preview = st.columns([1, 1], gap="large")

    with col_editor:
        st.subheader("Post Editor")

        club_keys = list(st.session_state.config.keys())
        selected_club = st.selectbox(
            "Select Club Context",
            club_keys,
            format_func=lambda x: st.session_state.config[x].get("page_name", x),
            key="active_club_select"
        )
        st.session_state.active_club = selected_club
        current_club_cfg = st.session_state.config.get(selected_club, {})

        with st.expander("🔗 Fetch Direct Article URL into Draft", expanded=False):
            scrape_url_input = st.text_input("Article URL:", placeholder="https://www.bbc.com/sport/football/...")
            if st.button("Fetch & Draft Article", use_container_width=True):
                if scrape_url_input:
                    with st.spinner("Extracting web page via Trafilatura..."):
                        extracted = extract_article_details(scrape_url_input)
                        if extracted and extracted.get("title"):
                            title = extracted.get("title", "")
                            text_body = extracted.get("text", "")
                            snippet = text_body[:280] + "..." if len(text_body) > 280 else text_body
                            footer = current_club_cfg.get("default_footer", "")
                            tags = " ".join(current_club_cfg.get("hashtags", []))
                            
                            st.session_state.composer_text = f"🚨 BREAKING: {title}\n\n{snippet}\n\n🔗 Read full report: {scrape_url_input}\n\n{footer}\n\n{tags}"
                            if extracted.get("image"):
                                st.session_state.composer_media_url = extracted.get("image")
                            st.success("Imported article content into editor!")
                            st.rerun()

        template_col1, template_col2 = st.columns(2)
        with template_col1:
            if st.button("➕ Matchday Template", use_container_width=True):
                tags = " ".join(current_club_cfg.get("hashtags", []))
                footer = current_club_cfg.get("default_footer", "")
                st.session_state.composer_text = f"MATCHDAY! ⚽🔥\n\nThe squad returns to action today for a crucial fixture.\n\n📍 Venue: Home Grounds\n⏰ Kickoff: 15:00 GMT\n\n{footer}\n\n{tags}"
                st.rerun()
        with template_col2:
            if st.button("➕ Breaking News Template", use_container_width=True):
                tags = " ".join(current_club_cfg.get("hashtags", []))
                footer = current_club_cfg.get("default_footer", "")
                st.session_state.composer_text = f"🚨 BREAKING TEAM NEWS 🚨\n\nOfficial confirmation regarding team lineup updates and squad news.\n\n{footer}\n\n{tags}"
                st.rerun()

        post_text = st.text_area(
            "Post Content",
            value=st.session_state.composer_text,
            height=180,
            placeholder="Draft post body..."
        )
        st.session_state.composer_text = post_text
        st.caption(f"Character Count: **{len(post_text)}** characters")

        media_url = st.text_input(
            "Media Attachment URL",
            value=st.session_state.composer_media_url,
            placeholder="https://images.unsplash.com/..."
        )
        st.session_state.composer_media_url = media_url

        st.write("**Quick Tag Ingestion:**")
        hashtags = current_club_cfg.get("hashtags", [])
        chip_cols = st.columns(len(hashtags) if hashtags else 1)
        for idx, tag in enumerate(hashtags):
            if chip_cols[idx].button(tag, key=f"chip_{idx}"):
                if tag not in st.session_state.composer_text:
                    st.session_state.composer_text += f" {tag}"
                    st.rerun()

        st.divider()
        act_col1, act_col2 = st.columns(2)
        with act_col1:
            if st.button("Clear Composer", use_container_width=True):
                st.session_state.composer_text = ""
                st.session_state.composer_media_url = ""
                st.rerun()
        with act_col2:
            if st.button("Copy Output Code", type="primary", use_container_width=True):
                st.code(st.session_state.composer_text, language="markdown")
                st.toast("Copied code block ready above!")

    with col_preview:
        st.subheader("Live Multi-Platform Previews")

        preview_platform = st.radio(
            "Platform Render View",
            ["X / Twitter", "LinkedIn", "Facebook", "Instagram"],
            horizontal=True
        )

        page_name = current_club_cfg.get("page_name", "Team Name")
        handle = current_club_cfg.get("handle", "@team")
        avatar_url = current_club_cfg.get("avatar", "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=100&auto=format&fit=crop&q=80")
        display_text = st.session_state.composer_text if st.session_state.composer_text else "Draft content preview will render live here..."

        if preview_platform == "X / Twitter":
            st.markdown(f"""
            <div class="preview-card x-card">
                <div style="display: flex; gap: 12px; align-items: start;">
                    <img src="{avatar_url}" style="width: 44px; height: 44px; border-radius: 50%; object-fit: cover;">
                    <div style="flex: 1;">
                        <div style="display: flex; gap: 6px; align-items: center;">
                            <strong>{page_name}</strong>
                            <span style="color: #71767b; font-size: 0.85rem;">{handle} · 1m</span>
                        </div>
                        <div style="margin-top: 8px; white-space: pre-wrap; font-size: 0.95rem; line-height: 1.4;">{display_text}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.composer_media_url:
                st.image(st.session_state.composer_media_url, use_container_width=True)

        elif preview_platform == "LinkedIn":
            st.markdown(f"""
            <div class="preview-card li-card">
                <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 12px;">
                    <img src="{avatar_url}" style="width: 48px; height: 48px; border-radius: 4px; object-fit: cover;">
                    <div>
                        <strong style="font-size: 0.95rem;">{page_name}</strong>
                        <div style="color: #666666; font-size: 0.8rem;">Official Premier League Account</div>
                        <div style="color: #666666; font-size: 0.8rem;">Just now · 🌐</div>
                    </div>
                </div>
                <div style="white-space: pre-wrap; font-size: 0.9rem; line-height: 1.5; color: #191919;">{display_text}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.composer_media_url:
                st.image(st.session_state.composer_media_url, use_container_width=True)

        elif preview_platform == "Facebook":
            st.markdown(f"""
            <div class="preview-card fb-card">
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 10px;">
                    <img src="{avatar_url}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;">
                    <div>
                        <strong style="font-size: 0.9rem;">{page_name} ✔️</strong>
                        <div style="font-size: 0.75rem; color: #65676b;">1 min · 🌐</div>
                    </div>
                </div>
                <div style="white-space: pre-wrap; font-size: 0.9rem; line-height: 1.4;">{display_text}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.composer_media_url:
                st.image(st.session_state.composer_media_url, use_container_width=True)

        elif preview_platform == "Instagram":
            ig_handle = handle.replace("@", "").lower()
            st.markdown(f"""
            <div class="preview-card ig-card">
                <div style="display: flex; gap: 10px; align-items: center; padding-bottom: 10px; border-bottom: 1px solid #efefef;">
                    <img src="{avatar_url}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; border: 1.5px solid #e1306c;">
                    <strong style="font-size: 0.85rem;">{ig_handle}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.composer_media_url:
                st.image(st.session_state.composer_media_url, use_container_width=True)
            else:
                st.info("📷 Attach an image URL to view card background.")
            st.markdown(f"""
            <div style="padding: 10px; font-size: 0.85rem; background: white; border: 1px solid #dbdbdb; border-radius: 0 0 12px 12px;">
                <strong>{ig_handle}</strong> <span style="white-space: pre-wrap;">{display_text}</span>
            </div>
            """, unsafe_allow_html=True)

# ==============================================================================
# TIER 2: RSS & FEED INGESTION BOARD
# ==============================================================================
elif view_option == "RSS & Feed Ingestion Board":
    st.title("📡 RSS & Feed Ingestion Board")
    st.caption("Scrapes live Premier League news articles with a one-click draft button.")

    col_filter1, col_filter2 = st.columns([2, 1])
    with col_filter1:
        club_keys = list(st.session_state.config.keys())
        selected_feed_club = st.selectbox(
            "Target Ingestion Club",
            club_keys,
            format_func=lambda x: st.session_state.config[x].get("page_name", x)
        )
    with col_filter2:
        fetch_limit = st.slider("Max Articles", 1, 10, 4)

    target_sources = st.session_state.config.get(selected_feed_club, {}).get("sources", [])
    st.info(f"Configured Feeds: `{', '.join(target_sources)}`")

    if st.button("🚀 Ingest Live RSS & Web Feeds", type="primary", use_container_width=True):
        with st.spinner(f"Crawling sources for {selected_feed_club.upper()}..."):
            articles = parse_rss_or_web(selected_feed_club, target_sources, limit=fetch_limit)
            st.session_state.fetched_articles = articles

    fetched_items = st.session_state.get("fetched_articles", [])
    if fetched_items:
        st.subheader(f"Ingested Stories ({len(fetched_items)})")
        grid_cols = st.columns(2)
        for idx, item in enumerate(fetched_items):
            col_target = grid_cols[idx % 2]
            with col_target:
                with st.container(border=True):
                    st.caption(f"{item['source_domain']} · {item['published_time']}")
                    st.markdown(f"#### {item['title']}")
                    st.write(item['summary'])
                    st.markdown(f"[🔗 Open Original Link]({item['article_url']})")

                    if st.button(f"✏️ Draft Post from Article", key=f"draft_{idx}", use_container_width=True):
                        club_cfg = st.session_state.config.get(selected_feed_club, {})
                        footer = club_cfg.get("default_footer", "")
                        tags = " ".join(club_cfg.get("hashtags", []))

                        draft_post = f"🚨 UPDATE: {item['title']}\n\n{item['summary']}\n\n🔗 Read full story: {item['article_url']}\n\n{footer}\n\n{tags}"
                        st.session_state.composer_text = draft_post
                        if item.get("image_url"):
                            st.session_state.composer_media_url = item.get("image_url")
                        st.success("Draft loaded into Interactive Composer! Switch tab to edit.")
    else:
        st.write("Click 'Ingest Live RSS & Web Feeds' above to fetch stories.")

# ==============================================================================
# TIER 3: TEAM & CLUB CONFIGURATION EDITOR
# ==============================================================================
elif view_option == "Team Config Editor":
    st.title("⚙️ Team & Club Configuration Editor")
    st.caption("Visual GUI replacement for modifying `teams_config.yaml`.")

    col_list, col_details = st.columns([1, 2])

    with col_list:
        st.subheader("Configured Clubs")
        club_keys = list(st.session_state.config.keys())
        selected_edit_key = st.radio("Select Club", club_keys, format_func=lambda x: st.session_state.config[x].get("page_name", x))

        st.divider()
        st.subheader("Add New Club Entry")
        new_key = st.text_input("New Club Key (e.g. 'chelsea')").lower().strip()
        new_name = st.text_input("Display Page Name (e.g. 'Chelsea FC Hub')")
        if st.button("➕ Add Club", use_container_width=True):
            if new_key and new_name:
                if new_key not in st.session_state.config:
                    st.session_state.config[new_key] = {
                        "page_name": new_name,
                        "handle": f"@{new_key}",
                        "avatar": "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=100&auto=format&fit=crop&q=80",
                        "hashtags": [f"#{new_key.upper()}", "#PremierLeague"],
                        "default_footer": "Drop your thoughts below!",
                        "sources": ["https://www.bbc.com/sport/football"]
                    }
                    save_config(st.session_state.config)
                    st.success(f"Added {new_name}!")
                    st.rerun()

    with col_details:
        if selected_edit_key in st.session_state.config:
            st.subheader(f"Edit Config: `{selected_edit_key}`")
            club_data = st.session_state.config[selected_edit_key]

            updated_name = st.text_input("Page Display Name", value=club_data.get("page_name", ""))
            updated_handle = st.text_input("Social Media Handle", value=club_data.get("handle", ""))
            updated_avatar = st.text_input("Avatar Image URL", value=club_data.get("avatar", ""))
            
            existing_tags = ", ".join(club_data.get("hashtags", []))
            updated_tags_str = st.text_input("Hashtags (comma-separated)", value=existing_tags)
            
            updated_footer = st.text_area("Default Footer / CTA", value=club_data.get("default_footer", ""))

            st.write("**Ingestion RSS / Source Links:**")
            existing_sources = club_data.get("sources", [])
            sources_text = st.text_area("Source URLs (One per line)", value="\n".join(existing_sources))

            col_save, col_del = st.columns(2)
            with col_save:
                if st.button("💾 Save Changes", type="primary", use_container_width=True):
                    parsed_tags = [t.strip() for t in updated_tags_str.split(",") if t.strip()]
                    parsed_sources = [s.strip() for s in sources_text.split("\n") if s.strip()]

                    st.session_state.config[selected_edit_key] = {
                        "page_name": updated_name,
                        "handle": updated_handle,
                        "avatar": updated_avatar,
                        "hashtags": parsed_tags,
                        "default_footer": updated_footer,
                        "sources": parsed_sources
                    }
                    save_config(st.session_state.config)
                    st.success("teams_config.yaml saved!")
                    st.rerun()

            with col_del:
                if st.button("🗑️ Delete Club", use_container_width=True):
                    if len(st.session_state.config) > 1:
                        del st.session_state.config[selected_edit_key]
                        save_config(st.session_state.config)
                        st.success(f"Deleted {selected_edit_key}!")
                        st.rerun()
                    else:
                        st.error("Cannot delete the only remaining club in config.")
import streamlit as st
import preprocessor
import helper
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import zipfile
import os
from collections import Counter

st.set_page_config(
    page_title="WhatsApp Chat Analyzer",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---- STYLING ----
st.markdown("""
<style>
    .stApp {
        background-color: #F0F2F6;
        color: #333333;
    }

    .title-container {
        text-align: center;
        margin-top: 3rem;
    }
    .title-container h1 {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        font-size: 2.5rem;
        font-weight: 700;
        color: #008069;
        margin-bottom: 0.5rem;
    }
    .title-icon {
        background-color: #008069;
        color: white;
        padding: 0.5rem;
        border-radius: 10px;
        line-height: 1;
        width: 50px;
        height: 50px;
        text-align: center;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #667781;
        text-align: center;
        margin-bottom: 3rem;
    }

    [data-testid="stFileUploader"] {
        border: 2px dashed #008069;
        border-radius: 10px;
        padding: 2rem;
        background-color: #FFFFFF;
        width: 100%;
    }
    [data-testid="stFileUploader"] button {
        background-color: #008069;
        color: white;
        border: none;
        border-radius: 5px;
    }
    [data-testid="stFileUploader"] button:hover {
        background-color: #005c4b;
        color: white;
        border: none;
    }

    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
    }
    [data-testid="stMetricLabel"] {
        color: #333 !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricValue"] {
        color: #008069 !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
    }

    [data-testid="stTabs"] {
        border-bottom: 2px solid #ddd !important;
    }
    [data-testid="stTab"] {
        color: #444 !important;
        font-weight: 500 !important;
        font-size: 1.05rem !important;
    }
    [data-testid="stTab"][aria-selected="true"] {
        color: #008069 !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #008069 !important;
    }
    [data-testid="stTab"]:hover {
        background-color: #e8f5e9 !important;
        color: #00654f !important;
    }
</style>
""", unsafe_allow_html=True)


# ---- SESSION STATE INIT ----
if 'analysis_triggered' not in st.session_state:
    st.session_state.analysis_triggered = False
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'media_files' not in st.session_state:
    st.session_state.media_files = []

# ---- UPLOAD INTERFACE ----
if not st.session_state.analysis_triggered:
    left_spacer, main_col, right_spacer = st.columns([1, 1.5, 1])
    with main_col:
        st.markdown("""
            <div class="title-container">
                <h1>
                    <span class="title-icon">❚</span>
                    <span>WhatsApp Chat Analyzer</span>
                </h1>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('<p class="subtitle">Upload your WhatsApp chat export (.txt or .zip with media)</p>', unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Upload WhatsApp Chat (.txt or .zip with media)",
            type=["txt", "zip"],
            label_visibility="collapsed"
        )

        if uploaded_file:
            chat_data = None
            media_files = []

            if uploaded_file.name.endswith(".zip"):
                try:
                    with zipfile.ZipFile(uploaded_file, 'r') as z:
                        all_files = z.namelist()
                        txt_files = [f for f in all_files if f.endswith(".txt")]
                        if not txt_files:
                            st.error("No chat .txt file found in ZIP.")
                            st.stop()

                        chat_file = z.open(txt_files[0])
                        chat_data = chat_file.read().decode("utf-8")

                        media_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3', '.pdf', '.docx')
                        media_files = [f for f in all_files if f.lower().endswith(media_extensions)]

                except Exception as e:
                    st.error(f"Error reading ZIP: {e}")
                    st.stop()
            else:
                chat_data = uploaded_file.getvalue().decode("utf-8")

            if chat_data:
                st.session_state.uploaded_file = chat_data
                st.session_state.media_files = media_files
                st.session_state.analysis_triggered = True
                st.rerun()

# ---- ANALYSIS PAGE ----
else:
    data = st.session_state.uploaded_file
    media_files = st.session_state.media_files

    try:
        df = preprocessor.preprocess(data)
    except Exception as e:
        st.error(f"File Processing Error: Please upload a valid WhatsApp chat file. Details: {e}")
        if st.button("Try again"):
            st.session_state.analysis_triggered = False
            st.rerun()
        st.stop()

    st.sidebar.title("Analysis Options")
    user_list = df['user'].unique().tolist()
    if 'group_notification' in user_list:
        user_list.remove('group_notification')
    user_list.sort()
    user_list.insert(0, "Overall")
    selected_user = st.sidebar.selectbox("Analyze chat for:", user_list)

    if st.sidebar.button("⬅️ Back to Upload"):
        st.session_state.analysis_triggered = False
        st.session_state.uploaded_file = None
        st.session_state.media_files = []
        st.rerun()

    st.header(f"Dashboard for: {selected_user}")

    num_messages, words, num_media, num_links = helper.fetch_stats(selected_user, df, media_files)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(label="💬 Total Messages", value=f"{num_messages:,}")
    kpi2.metric(label="📄 Total Words", value=f"{words:,}")
    kpi3.metric(label="🖼️ Media Shared", value=f"{num_media:,}")
    kpi4.metric(label="🔗 Links Shared", value=f"{num_links:,}")

    if media_files:
        with st.expander("📁 Media Files Summary"):
            counts = Counter([os.path.splitext(f)[1].lower() for f in media_files])
            st.write("**Media Types and Counts:**")
            for ext, count in counts.items():
                st.write(f"- `{ext}` → {count} files")
            st.write("**Example Media Files:**")
            st.write(media_files[:10])

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🗓️ Timeline & Activity", "💬 Content Analysis", "👥 User Leaderboard", "🔗 Links Shared"])

    with tab1:
        st.subheader("Message Timelines")
        col1, col2 = st.columns(2)
        with col1:
            timeline = helper.monthly_timeline(selected_user, df)
            fig = px.line(timeline, x='time', y='message', title="Monthly Message Count", labels={'time': 'Month', 'message': 'Messages'}, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            daily_timeline = helper.daily_timeline(selected_user, df)
            fig = px.line(daily_timeline, x='only_date', y='message', title="Daily Message Count", labels={'only_date': 'Date', 'message': 'Messages'}, color_discrete_sequence=['#2ca02c'], template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Activity Maps")
        col1, col2 = st.columns(2)
        with col1:
            busy_day = helper.week_activity_map(selected_user, df)
            fig = px.bar(busy_day, x=busy_day.index, y=busy_day.values, title="Most Busy Days", color=busy_day.index, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            busy_month = helper.month_activity_map(selected_user, df)
            fig = px.bar(busy_month, x=busy_month.index, y=busy_month.values, title="Most Busy Months", color=busy_month.index, color_discrete_sequence=px.colors.sequential.Plasma, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Weekly Activity Heatmap")
        user_heatmap = helper.activity_heatmap(selected_user, df)
        if not user_heatmap.empty:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax = sns.heatmap(user_heatmap, cmap='YlGnBu', ax=ax)
            plt.title("Weekly Activity Heatmap")
            st.pyplot(fig)
        else:
            st.warning("Not enough data to display the Weekly Activity Heatmap.")

    with tab2:
        st.subheader("Message Content Insights")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**☁️ Word Cloud**")
            df_wc = helper.create_wordcloud(selected_user, df)
            fig, ax = plt.subplots(facecolor='white')
            ax.imshow(df_wc)
            ax.axis("off")
            st.pyplot(fig)
        with col2:
            st.markdown("**🔠 Most Common Words**")
            most_common_df = helper.most_common_words(selected_user, df)
            fig = px.bar(most_common_df.head(15), x=1, y=0, orientation='h', labels={'1': 'Frequency', '0': 'Words'}, color_discrete_sequence=['#d62728'], template="plotly_white")
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("😊 Emoji Analysis")
        emoji_df = helper.emoji_helper(selected_user, df)
        if emoji_df.empty:
            st.warning("No emojis found.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                if 0 in emoji_df.columns and 1 in emoji_df.columns:
                    emoji_df.columns = ['Emoji', 'Count']
                st.dataframe(emoji_df, use_container_width=True)
            with col2:
                labels = emoji_df['Emoji'].head() if 'Emoji' in emoji_df.columns else emoji_df[0].head()
                sizes = emoji_df['Count'].head() if 'Count' in emoji_df.columns else emoji_df[1].head()
                fig = px.pie(values=sizes, names=labels, title="Top 5 Emojis", hole=.4, template="plotly_white")
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("User Leaderboard")
        if selected_user == 'Overall':
            x, new_df = helper.most_busy_users(df)
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(x, x=x.index, y=x.values, color=x.index, title="Top Users by Message Count", template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(new_df.style.background_gradient(cmap='viridis'), use_container_width=True)
        else:
            st.info("This view is only available for the 'Overall' chat analysis. Please select 'Overall' in the sidebar.")

    with tab4:
        st.subheader("Links Shared")
        # Extract links for the selected user
        from urlextract import URLExtract
        extract = URLExtract()
        if selected_user != 'Overall':
            link_df = df[df['user'] == selected_user]
        else:
            link_df = df
        all_links = []
        for idx, row in link_df.iterrows():
            found = extract.find_urls(row['message'])
            for url in found:
                all_links.append({'date': row['date'], 'user': row['user'], 'url': url})
        if all_links:
            st.write(f"Total links found: {len(all_links)}")
            st.dataframe(all_links)
        else:
            st.info("No links found in this chat.")
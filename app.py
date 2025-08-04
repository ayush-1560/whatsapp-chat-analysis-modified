import streamlit as st
import re
import preprocessor
import helper
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import zipfile
import os
import pandas as pd
from collections import Counter
from urlextract import URLExtract
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email_validator import validate_email, EmailNotValidError

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
    .title-icon-img {
        width: 50px;
        height: 50px;
        border-radius: 10px;
        background-color: white;
        padding: 5px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
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

# ---- EMAIL REPORT FUNCTION ----

def send_email_report(recipient_email, subject, body_html, image_tuples):
    sender_email = "ayush88843@gmail.com"
    sender_password = "coab gbmv ugyf dfjg"

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email

    msg_alt = MIMEMultipart("alternative")
    msg.attach(msg_alt)

    msg_text = MIMEText(body_html, "html")
    msg_alt.attach(msg_text)

    for i, (filename, img_bytes) in enumerate(image_tuples):
        img = MIMEImage(img_bytes)
        img.add_header("Content-ID", f"<img{i}>")
        img.add_header("Content-Disposition", "inline", filename=filename)
        msg.attach(img)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")
        return False



# ---- UPLOAD INTERFACE ----
if not st.session_state.analysis_triggered:
    left_spacer, main_col, right_spacer = st.columns([1, 1.5, 1])
    with main_col:
        st.markdown("""
            <div class="title-container">
                <h1>
                    <img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg"
                         alt="WhatsApp Logo"
                         class="title-icon-img" />
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

    # 📧 Email Report Section
    st.sidebar.markdown("---")
    st.sidebar.subheader("📧 Email Report")
    email_input = st.sidebar.text_input("Enter your email")

    num_messages, words, num_media, num_links = helper.fetch_stats(selected_user, df, media_files)

    if st.sidebar.button("Send Report"):
        try:
            valid = validate_email(email_input)
            email = valid.email

            # Fetch stats and charts
            num_messages, words, num_media, num_links = helper.fetch_stats(selected_user, df, media_files)
            timeline_imgs = helper.generate_timeline_charts(selected_user, df)
            activity_imgs = helper.generate_activity_maps(selected_user, df)
            content_imgs = helper.generate_content_charts(selected_user, df)
            leaderboard_imgs = helper.generate_user_leaderboard_charts(df)

            all_imgs = timeline_imgs + activity_imgs + content_imgs + leaderboard_imgs

            html_body = f"""
            <h2 style="color:#008069;">📊 WhatsApp Chat Full Report</h2>
            <p><b>User:</b> {selected_user}</p>
            <p><b>Total Messages:</b> {num_messages}<br>
            <b>Total Words:</b> {words}<br>
            <b>Media Files:</b> {num_media}<br>
            <b>Links Shared:</b> {num_links}</p>

            <hr><h3>🗓️ Timeline & Activity</h3>
            <img src="cid:img0"><br><img src="cid:img1"><br>
            <img src="cid:img2"><br><img src="cid:img3"><br><img src="cid:img4">

            <hr><h3>💬 Content Analysis</h3>
            <img src="cid:img5"><br><img src="cid:img6"><br><img src="cid:img7">

            <hr><h3>👥 User Leaderboard</h3>
            <img src="cid:img8">

            <p style="color:#999">Generated using WhatsApp Chat Analyzer · Preserves layout with colors and insights</p>
            """

            success = send_email_report(email, "Your WhatsApp Chat Report", html_body, all_imgs)
            if success:
                st.sidebar.success("✅ Report emailed successfully!")
        except EmailNotValidError as e:
            st.sidebar.error(f"Invalid email: {e}")

    st.header(f"Dashboard for: {selected_user}")

    # 👇 All your existing tabs and analysis logic stay untouched below this
    # Tabs: tab1, tab2, tab3, tab4, tab5
    # (Not repeated here since you've already provided them — they remain 100% same)



    num_messages, words, num_media, num_links = helper.fetch_stats(selected_user, df, media_files)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(label="💬 Total Messages", value=f"{num_messages:,}")
    kpi2.metric(label="📄 Total Words", value=f"{words:,}")
    kpi3.metric(label="🖼️ Media Shared", value=f"{num_media:,}")
    kpi4.metric(label="🔗 Links Shared", value=f"{num_links:,}")

    

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🗓️ Timeline & Activity",
        "💬 Content Analysis",
        "👥 User Leaderboard",
        "🔗 Links Shared",
        "🔍 Smart Chat Search",
        "📁 Media File Summary"
    ])

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
        extract = URLExtract()
        link_df = df if selected_user == 'Overall' else df[df['user'] == selected_user]
        all_links = []
        for idx, row in link_df.iterrows():
            found = extract.find_urls(row['message'])
            for url in found:
                all_links.append({
                    'date': row['date'],
                    'user': row['user'],
                    'url': f'<a href="{url}" target="_blank">{url}</a>'
                })

        if all_links:
            st.write(f"Total links found: {len(all_links)}")
            links_df = pd.DataFrame(all_links)[['date', 'user', 'url']]
            links_df.columns = ['Date', 'User', 'Link']
            st.write(links_df.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("No links found in this chat.")


    import re  # Ensure this is at the top of app.py

    with tab5:
        st.subheader("🔍 Smart Chat Search (Beta)")

        with st.expander("💡 Try asking: 'Who talked about exams?' or 'Show messages about birthday party'"):
            user_query = st.text_input("Enter your question about the chat:")

            if user_query:
                with st.spinner("Searching..."):
                    try:
                        chat_results = helper.smart_chat_search(df, user_query, selected_user)

                        if not chat_results:
                            st.warning("🔍 No relevant messages found for your query.")
                        else:
                            st.success("💬 Found relevant conversation blocks:")

                            current_block = []
                            previous_index = -10
                            keywords = user_query.strip().split()

                            for i, row in enumerate(chat_results):
                                message_text = row['message']

                                if row.name - previous_index > 3 and current_block:
                                    st.markdown('''
                                        <div style="background: #e8f5e9; padding: 16px; border-left: 6px solid #00b386; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
                                    ''', unsafe_allow_html=True)
                                    for msg in current_block:
                                        st.markdown(f"""
                                            <div style="margin-bottom: 12px;">
                                                <b style="color: #00664b;">{msg['user']}</b>
                                                <span style="color: #777;">[{msg['date']}]</span><br>
                                                <span style="color: #111; line-height: 1.6;">{msg['highlighted']}</span>
                                            </div>
                                        """, unsafe_allow_html=True)
                                    st.markdown("</div>", unsafe_allow_html=True)
                                    current_block = []

                                # Highlight keywords (case-insensitive)
                                highlighted_message = message_text
                                for word in keywords:
                                    if word.strip() == "":
                                        continue
                                    pattern = re.compile(re.escape(word), re.IGNORECASE)
                                    highlighted_message = pattern.sub(
                                        lambda m: f"<span style='background-color: #fff176; font-weight:bold; color:#000;'>{m.group(0)}</span>",
                                        highlighted_message
                                    )

                                current_block.append({
                                    'user': row['user'],
                                    'date': row['date'],
                                    'highlighted': highlighted_message
                                })
                                previous_index = row.name

                            if current_block:
                                st.markdown('''
                                    <div style="background: #e8f5e9; padding: 16px; border-left: 6px solid #00b386; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
                                ''', unsafe_allow_html=True)
                                for msg in current_block:
                                    st.markdown(f"""
                                        <div style="margin-bottom: 12px;">
                                            <b style="color: #00664b;">{msg['user']}</b>
                                            <span style="color: #777;">[{msg['date']}]</span><br>
                                            <span style="color: #111; line-height: 1.6;">{msg['highlighted']}</span>
                                        </div>
                                    """, unsafe_allow_html=True)
                                st.markdown("</div>", unsafe_allow_html=True)

                    except Exception as e:
                        st.error(f"Something went wrong while searching: {e}")






    with tab6:
        st.subheader("📁 Media File Summary")

        if media_files:
            with st.expander("📁 Media Files Summary"):
                counts = Counter([os.path.splitext(f)[1].lower() for f in media_files])
                st.write("**Media Types and Counts:**")
                for ext, count in counts.items():
                    st.write(f"- `{ext}` → {count} files")
                st.write("**Example Media Files:**")
                st.write(media_files[:10])

        st.markdown("<br>", unsafe_allow_html=True)


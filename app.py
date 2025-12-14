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
    msg_alt.attach(MIMEText(body_html, "html"))

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

# ---- UPLOAD PAGE ----
if not st.session_state.analysis_triggered:
    uploaded_file = st.file_uploader("Upload WhatsApp Chat", type=["txt", "zip"])

    if uploaded_file:
        chat_data = None
        media_files = []

        if uploaded_file.name.endswith(".zip"):
            with zipfile.ZipFile(uploaded_file, 'r') as z:
                txt_files = [f for f in z.namelist() if f.endswith(".txt")]
                chat_data = z.open(txt_files[0]).read().decode("utf-8")
                media_files = [f for f in z.namelist() if not f.endswith(".txt")]
        else:
            chat_data = uploaded_file.getvalue().decode("utf-8")

        st.session_state.uploaded_file = chat_data
        st.session_state.media_files = media_files
        st.session_state.analysis_triggered = True
        st.rerun()

# ---- ANALYSIS PAGE ----
else:
    df = preprocessor.preprocess(st.session_state.uploaded_file)
    media_files = st.session_state.media_files

    user_list = df['user'].unique().tolist()
    if 'group_notification' in user_list:
        user_list.remove('group_notification')
    user_list.sort()
    user_list.insert(0, "Overall")

    selected_user = st.sidebar.selectbox("Analyze chat for:", user_list)

    num_messages, words, num_media, num_links = helper.fetch_stats(selected_user, df, media_files)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💬 Messages", num_messages)
    k2.metric("📄 Words", words)
    k3.metric("🖼 Media", num_media)
    k4.metric("🔗 Links", num_links)

    tab1, tab2, tab3 = st.tabs(["📊 Activity", "💬 Content", "👥 Users"])

    # ---- TAB 1 ----
    with tab1:
        busy_day = helper.week_activity_map(selected_user, df).reset_index()
        busy_day.columns = ["day", "count"]

        fig = px.bar(
            busy_day,
            x="day",
            y="count",
            title="Most Busy Days",
            color="day",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        busy_month = helper.month_activity_map(selected_user, df).reset_index()
        busy_month.columns = ["month", "count"]

        fig = px.bar(
            busy_month,
            x="month",
            y="count",
            title="Most Busy Months",
            color="month",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---- TAB 2 ----
    with tab2:
        wc = helper.create_wordcloud(selected_user, df)
        fig, ax = plt.subplots()
        ax.imshow(wc)
        ax.axis("off")
        st.pyplot(fig)

    # ---- TAB 3 ----
    with tab3:
        if selected_user == "Overall":
            x, table = helper.most_busy_users(df)
            x_df = x.reset_index()
            x_df.columns = ["user", "count"]

            fig = px.bar(
                x_df,
                x="user",
                y="count",
                color="user",
                title="Top Users",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(table)

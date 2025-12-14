from urlextract import URLExtract
from wordcloud import WordCloud
import pandas as pd
from collections import Counter
import emoji
import os
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import io
import re

extract = URLExtract()
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def fetch_stats(selected_user, df, media_files=None):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    words = sum(len(msg.split()) for msg in df['message'])
    links = sum(len(extract.find_urls(msg)) for msg in df['message'])

    media_count = len(media_files) if media_files else 0
    return df.shape[0], words, media_count, links

def most_busy_users(df):
    counts = df['user'].value_counts()
    percent = round((counts / counts.sum()) * 100, 2)
    percent_df = percent.reset_index().rename(columns={"index": "user", "user": "percent"})
    return counts.head(), percent_df

def create_wordcloud(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    text = " ".join(df['message'])
    return WordCloud(width=500, height=500, background_color="white").generate(text)

def week_activity_map(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    return df['day_name'].value_counts()

def month_activity_map(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    return df['month'].value_counts()

def generate_activity_maps(selected_user, df):
    imgs = []

    busy_day = week_activity_map(selected_user, df).reset_index()
    busy_day.columns = ["day", "count"]

    fig = px.bar(busy_day, x="day", y="count", color="day", template="plotly_white")
    buf = io.BytesIO()
    fig.write_image(buf, format="png")
    imgs.append(("busy_days.png", buf.getvalue()))

    busy_month = month_activity_map(selected_user, df).reset_index()
    busy_month.columns = ["month", "count"]

    fig = px.bar(busy_month, x="month", y="count", color="month", template="plotly_white")
    buf = io.BytesIO()
    fig.write_image(buf, format="png")
    imgs.append(("busy_months.png", buf.getvalue()))

    return imgs

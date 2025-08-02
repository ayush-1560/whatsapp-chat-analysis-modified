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


extract = URLExtract()

# Load the sentence transformer model once
embedder = SentenceTransformer('all-MiniLM-L6-v2')


def fetch_stats(selected_user, df, media_files=None):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    num_messages = df.shape[0]

    words = []
    for message in df['message']:
        words.extend(message.split())

    media_count = len(media_files) if media_files else df[df['message'] == '<Media omitted>\n'].shape[0]

    links = []
    for message in df['message']:
        links.extend(extract.find_urls(message))

    return num_messages, len(words), media_count, len(links)


def most_busy_users(df):
    x = df['user'].value_counts().head()
    percent_df = round((df['user'].value_counts() / df.shape[0]) * 100, 2).reset_index().rename(
        columns={'index': 'name', 'user': 'percent'})
    return x, percent_df


def create_wordcloud(selected_user, df):
    if not os.path.exists('stop_hinglish.txt'):
        return WordCloud(width=500, height=500).generate("No stopword file found.")

    with open('stop_hinglish.txt', 'r', encoding='utf-8') as f:
        stop_words = f.read()

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    temp = df[df['user'] != 'group_notification']
    temp = temp[temp['message'] != '<Media omitted>\n']

    def remove_stop_words(message):
        return " ".join([word for word in message.lower().split() if word not in stop_words])

    wc = WordCloud(width=500, height=500, min_font_size=10, background_color='white')
    temp['message'] = temp['message'].apply(remove_stop_words)
    return wc.generate(temp['message'].str.cat(sep=" "))


def most_common_words(selected_user, df):
    if not os.path.exists('stop_hinglish.txt'):
        return pd.DataFrame()

    with open('stop_hinglish.txt', 'r', encoding='utf-8') as f:
        stop_words = f.read()

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    temp = df[df['user'] != 'group_notification']
    temp = temp[temp['message'] != '<Media omitted>\n']

    words = []
    for message in temp['message']:
        for word in message.lower().split():
            if word not in stop_words:
                words.append(word)

    return pd.DataFrame(Counter(words).most_common(20))


def emoji_helper(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    emojis = []
    for message in df['message']:
        emojis.extend([c for c in message if emoji.is_emoji(c)])

    return pd.DataFrame(Counter(emojis).most_common(len(Counter(emojis))))


def monthly_timeline(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    timeline = df.groupby(['year', 'month_num', 'month']).count()['message'].reset_index()
    timeline['time'] = timeline['month'] + "-" + timeline['year'].astype(str)
    return timeline


def daily_timeline(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    return df.groupby('only_date').count()['message'].reset_index()


def week_activity_map(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    return df['day_name'].value_counts()


def month_activity_map(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    return df['month'].value_counts()


def activity_heatmap(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    return df.pivot_table(index='day_name', columns='period', values='message', aggfunc='count').fillna(0)


# 🔍 SMART CHAT SEARCH
def smart_chat_search(df, query, selected_user="Overall", top_n=10):
    if selected_user != "Overall":
        df = df[df['user'] == selected_user]

    df = df[df['message'].str.strip() != '']
    df = df[~df['message'].str.contains('<Media omitted>', na=False)]

    messages = df['message'].tolist()
    if not messages:
        return pd.DataFrame(columns=["user", "date", "message", "score"])

    message_embeddings = embedder.encode(messages, convert_to_tensor=True)
    query_embedding = embedder.encode(query, convert_to_tensor=True)

    similarities = cosine_similarity(
        [query_embedding.cpu().numpy()], message_embeddings.cpu().numpy()
    )[0]

    df = df.copy()
    df['score'] = similarities
    df_sorted = df.sort_values(by='score', ascending=False).head(top_n)

    return df_sorted[['user', 'date', 'message', 'score']]

# 🔍 Email Reports Content 
def generate_timeline_charts(selected_user, df):
    imgs = []

    # Monthly timeline
    timeline = monthly_timeline(selected_user, df)
    fig = px.line(timeline, x='time', y='message', title="Monthly Message Count", template='plotly_white')
    buf = io.BytesIO()
    fig.write_image(buf, format='png')
    imgs.append(('monthly.png', buf.getvalue()))

    # Daily timeline
    daily = daily_timeline(selected_user, df)
    fig = px.line(daily, x='only_date', y='message', title="Daily Message Count", color_discrete_sequence=['#2ca02c'], template='plotly_white')
    buf = io.BytesIO()
    fig.write_image(buf, format='png')
    imgs.append(('daily.png', buf.getvalue()))

    return imgs

def generate_activity_maps(selected_user, df):
    imgs = []

    # Weekly bar
    busy_day = week_activity_map(selected_user, df)
    fig = px.bar(busy_day, x=busy_day.index, y=busy_day.values, title="Most Busy Days", color=busy_day.index, template="plotly_white")
    buf = io.BytesIO()
    fig.write_image(buf, format='png')
    imgs.append(('busy_days.png', buf.getvalue()))

    # Monthly bar
    busy_month = month_activity_map(selected_user, df)
    fig = px.bar(busy_month, x=busy_month.index, y=busy_month.values, title="Most Busy Months", color=busy_month.index, template="plotly_white")
    buf = io.BytesIO()
    fig.write_image(buf, format='png')
    imgs.append(('busy_months.png', buf.getvalue()))

    # Heatmap
    heatmap_data = activity_heatmap(selected_user, df)
    if not heatmap_data.empty:
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.heatmap(heatmap_data, cmap='YlGnBu', ax=ax)
        plt.title("Weekly Activity Heatmap")
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig)
        imgs.append(('heatmap.png', buf.getvalue()))

    return imgs

def generate_content_charts(selected_user, df):
    imgs = []

    # Wordcloud
    wc_img = create_wordcloud(selected_user, df)
    fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
    ax.imshow(wc_img, interpolation='bilinear')
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    imgs.append(('wordcloud.png', buf.getvalue()))

    # Common words bar
    common_df = most_common_words(selected_user, df).head(15)
    fig = px.bar(common_df, x=1, y=0, orientation='h', labels={'0': 'Words', '1': 'Frequency'}, color_discrete_sequence=['#d62728'], template="plotly_white")
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    buf = io.BytesIO()
    fig.write_image(buf, format='png')
    imgs.append(('common_words.png', buf.getvalue()))

    # Emoji pie chart
    emoji_df = emoji_helper(selected_user, df)
    if not emoji_df.empty:
        emoji_df.columns = ['Emoji', 'Count']
        fig = px.pie(emoji_df.head(5), values='Count', names='Emoji', title="Top 5 Emojis", hole=.4, template='plotly_white')
        fig.update_traces(textposition='inside', textinfo='percent+label')
        buf = io.BytesIO()
        fig.write_image(buf, format='png')
        imgs.append(('emoji.png', buf.getvalue()))

    return imgs

def generate_user_leaderboard_charts(df):
    imgs = []
    x, _ = most_busy_users(df)
    fig = px.bar(x, x=x.index, y=x.values, color=x.index, title="Top Users by Message Count", template="plotly_white")
    buf = io.BytesIO()
    fig.write_image(buf, format='png')
    imgs.append(('leaderboard.png', buf.getvalue()))
    return imgs

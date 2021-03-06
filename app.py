import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from asari.api import Sonar

from utils import get_motivation, get_tweet, cleaning

st.title('Create Motivation Graph')

tw_id = st.sidebar.text_input('Input Tweeter ID')
st.write('PROGRESS BAR')
percentage = st.empty()
progress_bar = st.progress(0)
if tw_id == '':
    st.warning("Input Tweeter ID")
    st.stop()

@st.cache(allow_output_mutation=True, suppress_st_warning=True)
def get_tweet_df(tw_id):
    df, message = get_tweet.create_tw_df(tw_id)
    if message != 'Success':
        st.warning(message)
        st.stop()
    # indexをdatetimeにする
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df['clean_text'] = df['text'].map(cleaning.format_text)
    df['clean_text'] = df['clean_text'].map(cleaning.normalize)
    return df

@st.cache(suppress_st_warning=True)
def get_scores(text_list):
    sonar = Sonar()
    with st.spinner('Wait for API...'):
        A = list(map(sonar.ping, text_list))
    st.success('Done!')
    scores = []
    total = len(text_list)
    count = 0
    for res in A:
        if res['text'] == ' ': #空白にもスコアが追加されてしまうため
            scores.append(0)
            count += 1
            continue
        label = res['top_class']
        if label == 'negative':
            index = 0
            score = round(-1 * (res['classes'][index]['confidence']), 4)
        else:
            index = 1
            score = round(res['classes'][index]['confidence'], 4)
        scores.append(score)
        # 四捨五入する
        count += 1
        percent = round((count/total) * 100)
        percentage.text(f'Progress: {percent}%')
        progress_bar.progress(percent)
        time.sleep(0.001)
    print('total:', total)
    print('count:', count)
    return scores

@st.cache()
def create_motivation_df(df, score_list):
    df['score'] = score_list
    motivation_df = df.resample("1D").mean()
    return motivation_df

df = get_tweet_df(tw_id)
scores = get_scores(df['clean_text'].tolist())
# motivation_df : index:datetime(日付のみ時間は9:00), score(total)
motivation_df = create_motivation_df(df, scores)

@st.cache(allow_output_mutation=True)
def create_counter(df, motivation_df):
    # dfからその日のツイートを取得
    count_df = pd.DataFrame({'Timestamp':df.index, 'tweet':df.text})
    count_df['date'] = count_df['Timestamp'].apply(lambda x: '%d-%d-%d' % (x.year, x.month, x.day))
    count_df = count_df.reset_index(drop=True)
    # 日毎のツイート数
    counter = count_df.groupby(['date']).size() # Series
    date_list = list(map(lambda x: '%d-%d-%d' % (x.year, x.month, x.day), motivation_df.index.tolist()))
    motivation_df['date'] = date_list
    return counter, motivation_df

counter, motivation_df = create_counter(df, motivation_df)

# 可視化範囲指定
until = datetime.now() + timedelta(hours=9)
since = until - relativedelta(years=1)
date_range = st.sidebar.date_input("date range of tweet",
                                    value= [until - relativedelta(days=7), until],
                                    min_value=since, max_value=until)
if len(date_range) < 2:
    st.warning('Select 2 days from sidebar')
    st.stop()

date_span = (date_range[1] - date_range[0]).days
if date_span <= 31:
    dtick = '1D'
elif 31 < date_span <= 60:
    dtick = 3 * 86400000.0
elif 60 < date_span < 120:
    dtick = 7 * 86400000.0
else:
    dtick = '1M'

# 可視化
x_coord = motivation_df.loc[date_range[0]:date_range[1], :].index.tolist()
y_coord = motivation_df.loc[date_range[0]:date_range[1], :].score.values.tolist()

trace0 = go.Scatter(x = x_coord, y = y_coord, mode = 'lines + markers', name = 'X')

fig = go.Figure(data=trace0)

fig.update_layout(
            title = dict(text = 'motivation graph'),
            xaxis = dict(title = 'date', type='date', dtick = dtick, tickformat="%Y-%m-%d"),  # dtick: 'M1'で１ヶ月ごとにラベル表示
            yaxis = dict(title = 'motivation score', range=[-1,1]),
            width=900,
            height = 500
            )

st.plotly_chart(fig)

emoji_dict = {'painful':'😭', 'sad':'😢', 'pien': '🥺', 'usual':'😃', 'joy': '😁', 'exciting': '😆', 'happy':'✌😎✌️'}
def sentiment_emoji(score):
    if -1 <= score < -0.7:
        return emoji_dict['painful']
    elif -0.7 <= score < -0.4:
        return emoji_dict['sad']
    elif -0.4 <= score < -0.2:
        return emoji_dict['pien']
    elif -0.2 <= score < 0.2:
        return emoji_dict['usual']
    elif 0.2 <= score < 0.4:
        return emoji_dict['joy']
    elif 0.4 <= score < 0.7:
        return emoji_dict['exciting']
    else:
        st.balloons()
        return emoji_dict['happy']

# 選択した日付のテキストを表示
d = st.sidebar.date_input('When Tweet', value=until,min_value=since, max_value=until)
st.write(f'{d}のツイート')
total = motivation_df[pd.to_datetime(motivation_df.date) == pd.to_datetime(d)].score.tolist()
st.write(f'Total_score:{round(total[0], 4)}')
st.write(f'Status:  {sentiment_emoji(total[0])}')
tweets = df[pd.to_datetime(df.index.date) == pd.to_datetime(d)]
tweets = tweets.reset_index(drop=True)
# ここのtextは前処理なしの文章(URLも含む) scoreを出す際はURL除いてる
st.table(tweets[['created_at', 'text', 'score']])
import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime
from dateutil.relativedelta import relativedelta

from utils import get_motivation, get_tweet


st.title('Create Motivation Graph')

tw_id = st.sidebar.text_input('Input Tweeter ID')

if tw_id == '':
    st.warning("Input Tweeter ID")
    st.stop()

@st.cache(allow_output_mutation=True)
def create_motive_df(tw_id):
    get_tweet.create_tw_csv(tw_id)
    df = pd.read_csv('data/tweet.csv', encoding='utf8')
    # indexをdatetimeにする
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    motivation_df = get_motivation.day_motivation_df(df)
    return df, motivation_df

# motivation_df : index:datetime(日付のみ時間は9:00), score(total)
df, motivation_df = create_motive_df(tw_id)
@st.cache(allow_output_mutation=True)
def change_df(df, motivation_df):
    # # dfからその日のツイートを取得
    count_df = pd.DataFrame({'Timestamp':df.index, 'tweet':df.text})
    count_df['date'] = count_df['Timestamp'].apply(lambda x: '%d-%d-%d' % (x.year, x.month, x.day))
    count_df = count_df.reset_index(drop=True)
    # 日毎のツイート数
    counter = count_df.groupby(['date']).size() # Series
    date_list = list(map(lambda x: '%d-%d-%d' % (x.year, x.month, x.day), motivation_df.index.tolist()))
    motivation_df['date'] = date_list
    return counter, motivation_df

counter, motivation_df = change_df(df, motivation_df)

# 可視化
x_coord = motivation_df.index.tolist()
y_coord = motivation_df.score.values.tolist()

trace0 = go.Scatter(x = x_coord, y = y_coord, mode = 'lines', name = 'X')

fig = go.Figure(data=trace0)

fig.update_layout(
            title = dict(text = 'Anual motivation graph'),
            xaxis = dict(title = 'date', type='date', dtick = 'M1'),  # dtick: 'M1'で１ヶ月ごとにラベル表示
            yaxis = dict(title = 'motivation score'),
            width=1000,
            height = 500
            )

st.plotly_chart(fig)

until = datetime.now()
since = until - relativedelta(years=1)
# 選択した日付のテキストを表示
d = st.sidebar.date_input('When Tweet',min_value=since, max_value=until)
st.write(f'{d}のツイート')
total = motivation_df[pd.to_datetime(motivation_df.date) == pd.to_datetime(d)].score.tolist()
st.write('total_score:',round(total[0], 4))
# TODO:scoreごとに顔文字追加

tweets = df[pd.to_datetime(df.index.date) == pd.to_datetime(d)]
tweets = tweets.reset_index(drop=True)
# ここのtextは前処理なしの文章(URLも含む)
# scoreを出す際はURL除いてる
st.table(tweets[['created_at', 'text', 'score']])
from datetime import datetime

from pandas import DataFrame


def clean_time_duplicates(df: DataFrame):
    for i in range(len(df)):
        if 'AM' in df.date.iloc[i] or 'PM' in df.date.iloc[i]:
            df.at[i, 'date'] = datetime.strptime(df.date.iloc[i], '%Y-%m-%d %I-%p')
        elif '/' in df.date.iloc[i]:
            if ':' in df.date.iloc[i]:
                df.at[i, 'date'] = datetime.strptime(df.date.iloc[i], '%Y/%m/%d %H:%M:%S')
            else:
                df.at[i, 'date'] = datetime.strptime(df.date.iloc[i], '%Y/%m/%d')
        else:
            df.at[i, 'date'] = datetime.fromisoformat(df.date.iloc[i])
    df.drop_duplicates(subset=['date'], inplace=True)
    del df['date']


def save_to_file(filename, content):
    with open(filename, "w") as file:
        file.write(str(content))

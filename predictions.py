import time
import uuid

import records
import os

import maya
import numpy as np
import pandas as pd

# Matplotlib hack.
import matplotlib
matplotlib.use('agg')

from fbprophet import Prophet

from scraper import Coin, MWT, convert_to_decimal


PERIODS = 30


@MWT(timeout=300)
def get_predictions(coin, render=False):
    """Returns a list of predictions, unless render is True.
    Otherwise, returns the path of a rendered image.
    """

    c = Coin(coin)

    q = "SELECT date as ds, value as y from api_coin WHERE name=:coin"

    db = records.Database()
    rows = db.query(q, coin=c.name)

    df = rows.export('df')

    df['y_orig'] = df['y']  # to save a copy of the original data..you'll see why shortly. 

    # log-transform y
    df['y'] = np.log(df['y'])

    model = Prophet(weekly_seasonality=True, yearly_seasonality=True)
    model.fit(df)

    future_data = model.make_future_dataframe(periods=PERIODS, freq='d')
    forecast_data = model.predict(future_data)

    if render:
        f_name = str(uuid.uuid4())

        matplotlib.pyplot.gcf()
        model.plot(forecast_data).savefig(f_name)

        return f'{f_name}.png'

    forecast_data_orig = forecast_data  # make sure we save the original forecast data
    forecast_data_orig['yhat'] = np.exp(forecast_data_orig['yhat'])
    forecast_data_orig['yhat_lower'] = np.exp(forecast_data_orig['yhat_lower'])
    forecast_data_orig['yhat_upper'] = np.exp(forecast_data_orig['yhat_upper'])

    df['y_log'] = df['y']  #copy the log-transformed data to another column
    df['y'] = df['y_orig']  #copy the original data to 'y'

    # print(forecast_data_orig)
    d = forecast_data_orig['yhat'].to_dict()
    predictions = []

    for i, k in enumerate(list(d.keys())[-PERIODS:]):
        w = maya.when(f'{i+1} days from now')
        predictions.append({
            'when': w.slang_time(),
            'timestamp': w.iso8601(),
            'usd': convert_to_decimal(d[k]),
        })

    return predictions


if __name__ == '__main__':
    print(get_predictions('btc'))

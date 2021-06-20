import requests
import urllib
import datetime

import pandas as pd
from matplotlib import pyplot as plt

def getCovid():
	params = {
		"loc" : "ON",
		# "date" : dt.strftime('%d-%m-%Y'),
	}
	p = urllib.parse.urlencode(params)

	response = requests.get("https://api.opencovid.ca/timeseries?" + p)
	return response.json()

def date_map(dt_str):
	return datetime.datetime.strptime(dt_str, '%d-%m-%Y').date()

x = getCovid()


def get_covid_by_type(func_key, date_key):
	df = pd.DataFrame.from_records(x[func_key], index = date_key)
	df.index = df.index.map(date_map)
	return df

active_df = get_covid_by_type('active', date_key = 'date_active')
cases_df = get_covid_by_type('cases', date_key = 'date_report')[['cases']]
# print(get_covid_by_type('avaccine', date_key = 'date_vaccine_administered'))
vac_df = get_covid_by_type('cvaccine', date_key = 'date_vaccine_completed')[['cvaccine', 'cumulative_cvaccine']]
# print(get_covid_by_type('dvaccine', date_key = 'date_vaccine_distributed'))]

df = active_df.join(cases_df).join(vac_df)

df[['cvaccine']].plot()
plt.show()

# print(df)
# print(df.columns)
# print(df.shape)



# for index, c in cases_df.iterrows():
# 	print(index, c.get('cases'))
# print(cases_df.loc['11-06-2021', :])
# print(date_map('11-06-2021'))

vac_df['manu_diff'] = vac_df['cumulative_cvaccine'].diff()
print(vac_df)

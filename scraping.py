import datetime
import urllib.request
import urllib.parse
import requests
import http.cookiejar
from bs4 import BeautifulSoup
import re
from dbAPI import dbIO
import logging

logging.basicConfig(
	filename = "records.log",
    filemode = 'w',
    format = '%(asctime)s | %(levelname)s | %(message)s',
    datefmt = '%H:%M:%S',
    level = logging.DEBUG
)

logger = logging.getLogger()

''' login part '''
# this is the login url
login_url = 'https://api.condos.ca/v1/users/login'
# pretend to be a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:56.0) Gecko/20100101 Firefox/56.0',
    'Connection': 'keep-alive',
}
params = {
    'email': 'legolascyt@gmail.com',
    'password': 'cyt70104809',
    'hasMobileApp': False
}

# create session to remain login
session = requests.Session()
# make a post request to login and save to session
resp = session.post(login_url, params, headers = headers)

BASE_PATH = "https://condos.ca"

''' Tools '''

def tackle_date(dt_str):
	if "on" in dt_str:
		is_leased = True
		leased_dt = dt_str.replace("on ", "")
		leased_dt = datetime.datetime.strptime(leased_dt, "%d/%m/%y").date()
		leased_day_ago = (datetime.date.today() - leased_dt).days
	elif "Added" in dt_str:
		is_leased = False
		dt = re.findall(r'\d+', dt_str)
		leased_dt = None
		if len(dt) == 0:
			leased_day_ago = None
		else:
			leased_day_ago = dt[0]
	else:
		is_leased = None
		leased_dt = None
		leased_day_ago = None
	return is_leased, leased_dt, leased_day_ago

def extract_price(price_str):
	return float(price_str.replace("$", "").replace(",", ""))


''' single page scrapping '''


def getSoup(url):
	r = session.get(url, headers = headers)
	bs = BeautifulSoup(r.content, features = "lxml")
	return bs

def saveToHtml(url, filename):
	html = getSoup(url).prettify()
	with open(filename, "w", encoding = "utf8") as obj:
		obj.write(html)

def get_list_urls(url):
	# go over 11 pages
	for i in range(11):
		url_page = url + "&page=" + str(i + 1)
		bs = getSoup(url_page)

		for r in bs.find_all("a", class_ = "styles___Link-sc-1x8803n-6 giVjNP"):
			yield r.text, f"{BASE_PATH}{r.get('href')}"

def get_data_from_rent(rent_url, district, name):

	bs = getSoup(rent_url)

	#### find standard info
	keys = []
	values = []
	for r in bs.find_all("div", class_ = "styles___BlurCont-qq1hs5-0 styles___InfoRowTitle-sc-1cv9cf1-3 gdZyIb"):
		if str(r.text) in ('Area:', 'Actual size'):
			continue
		keys.append(r.text)

	for r in bs.find_all("div", class_ = "styles___ValueDiv-sc-1cv9cf1-5 cbTzmD"):
		values.append(r.text)

	# save infos to dict
	r = dict(zip(keys, values))

	# find lease date
	dt_str = bs.find("div", class_ = "styles___ListedAgo-ka5njm-4 endwPo").text.replace("Loading", "")
	is_leased, leased_dt, leased_day_ago = tackle_date(dt_str)
	r["LeaseDt"] = leased_dt
	r["IsLeased"] = is_leased
	r["ListedDay"] = leased_day_ago

	# find lease price
	regrex = re.compile("styles___Price-ka5njm-23.*")  # the div has multiple classes, use regrex to match
	p_tags = bs.find("div", class_ = regrex)
	div_p = p_tags.find("div")  # current or old price
	span_p = p_tags.find("span")  # updated price or none (if span has content, use span price)
	price = span_p.text if span_p.text is not '' else div_p.text
	r["LeasedPrice"] = extract_price(price)

	r["District"] = district
	r["Name"] = name
	r["Url"] = rent_url



	return r

DISTRICT_MAPPING = {
	"Alexandra Park" : 758,
	'Annex - U of T' : 759,
	'Bay St.Corridor': 750,
	'Cabbagetown': 741,
	'Chinatown': 756,
	'Church St.Corridor': 749,
	'CityPlace': 752,
	'Corktown': 744,
	'Distillery District': 745,
	'Fort York':761,
	'Grange Park': 755,
	'Kensington Market':757,
	'King West':753,
	'Moss Park':743,
	'Queen West':754,
	'Regent Park':742,
	'St.James Town':740,
	'St.Lawrence': 746,
	'The Core':751,
	'The Waterfront':747,
	'Yonge and Bloor':748,
	'Yorkville':760
}

COL_NAME_MAPPINGS = {
	'Name' : 'Name',
	'Size': 'Size',
	'Exposure': 'Exposure',
	'Furnished': 'Furnished',
	'Possession': 'Possession',
	'Age of building': 'AgeOfBuilding',
	'Outdoor space': 'OuterSpace',
	'Hydro included': 'HasHydro',
	'Locker': 'Locker',
	'Heating type:': 'Heating',
	'Parking type:': 'ParkingType',
	'Property type:': 'PropertyType',
	'Ensuite laundry:': 'Haslaundry',
	'Water included:': 'HasWater',
	'Parking:': 'Parking',
	'Corp #:': 'CorpNo',
	'Size:': 'Size',
	'LeaseDt': 'LeaseDt',
	'IsLeased': 'IsLeased',
	'ListedDay': 'ListedDay',
	'LeasedPrice': 'LeasedPrice',
	'Url' : 'Url'
}

def rename_dict_keys(old_dict, key_mappings):
	new_dict = {}
	for k, v in old_dict.items():
		new_k = key_mappings.get(k, k)
		new_dict[new_k] = v
	return new_dict


def getDistrictUrl(district):
	district_code = DISTRICT_MAPPING.get(district)
	return f'{BASE_PATH}/toronto/condos-for-rent?mode=Leased&sort=-end_date_unix&end_date_unix=relative%2C-365&neighbourhood_id={district_code}'


def saveRentalEntry(rental_dict):
	rental_data = rename_dict_keys(rental_dict, COL_NAME_MAPPINGS)
	sql = "INSERT INTO rentals({}) VALUES ({});".format(",".join(rental_data.keys()), ",".join(["%s" for k in rental_data.keys()]))
	dbIO.modify_sql(sql, list(rental_data.values()))

if __name__ == '__main__':

	# scraburl = 'https://condos.ca/toronto/condos-for-rent?mode=Leased&sort=-end_date_unix&end_date_unix=relative%2C-365&neighbourhood_id=758'
	#
	# for name, url in get_list_urls(scraburl):
	# 	rental_data = get_data_from_rent(url)
	# 	print(rental_data)
	# 	print("------------------------------------------------------------\n")
	#
	# rent_url = "https://condos.ca/toronto/totem-condos-17-dundonald-st/unit-701-C5186185"
	# get_data_from_rent(rent_url)

	# saveToHtml("https://condos.ca/toronto/condos-for-rent?mode=Leased&sort=-end_date_unix&end_date_unix=relative%2C-365&neighbourhood_id=758", "htmls/main_page.html")




	for district in DISTRICT_MAPPING.keys():
		url = getDistrictUrl(district)

		for name, rentalUrl in get_list_urls(url):
			logger.info(f"Name: {name}, District: {district}, Url: {rentalUrl}")
			print(f"Name: {name}, District: {district}, Url: {rentalUrl}")

			sql = "select distinct Name from rentals;"
			df = dbIO.query_sql_df(sql)
			if not df.empty:
				if name in df["Name"].tolist():
					logger.debug(f"condo {name} already exists in database, skip to next condo")
					continue

			try:
				rental_data = get_data_from_rent(rentalUrl, district, name)
				saveRentalEntry(rental_data)
			except Exception as e:
				logger.error(str(e))



	# import pandas as pd
	#
	# sql = "select * from rentals where LeasedPrice > %s;"
	# df = dbIO.query_sql_df(sql, 2400)
	# print(df)

import sys
import time
import datetime
import requests
from requests.auth import HTTPBasicAuth

from config import (
    API_KEY, 
    SECRET_KEY,
    AMAZON_USA,
    AMAZON_CAN,
    PREM_SHIRTS, 
    NSOTD,
    EBAY,
    BUCKEROO,
    WORLD_MAP,
    SLEEP,
)


AUTH = HTTPBasicAuth(API_KEY, SECRET_KEY)

"""
Refresh and import orders from the selling platforms.

    key (str):              ShipStation API key
    secret (str):           ShipStation API secret
    amazon_us_id (str):     Amazon US store identification number
    amazon_can_id (str):    Amazon Canada store identification number
    ebay_id (str):          eBay store identification number
    premier_id (str):       Premier store identification number
    nsotd_id (str):         New Shirt of the Day store identification number
    buckeroo_id (str):      Buckeroo store identification number
"""
try:
    ssapi = 'https://ssapi.shipstation.com/stores/refreshstore?storeId='

    amazon_USA_resp = requests.post(ssapi + AMAZON_USA, auth=AUTH)
    amazon_CAN_resp = requests.post(ssapi + AMAZON_CAN, auth=AUTH)
    ebay_resp = requests.post(ssapi + EBAY, auth=AUTH)
    prem_shirts_resp = requests.post(ssapi + PREM_SHIRTS, auth=AUTH)
    nsotd_resp = requests.post(ssapi + NSOTD, auth=AUTH)
    buck_resp = requests.post(ssapi + BUCKEROO, auth=AUTH)
except Exception as e:
    print('Error importing orders.\n')
    print(e)
    sys.exit()


# suspend execution for two minutes to allow enough time for all stores to import orders
if (amazon_USA_resp.json()['success'] == 'true' and
    amazon_CAN_resp.json()['success'] == 'true' and
    ebay_resp.json()['success'] == 'true' and
    prem_shirts_resp.json()['success'] == 'true' and
    nsotd_resp.json()['success'] == 'true' and
    buck_resp.json()['success'] == 'true'):
    
    # ex: Monday May 29 at 09:29 AM
    print('\nRefreshing all stores - ' + datetime.datetime.now().strftime('%A %b %d') + ' ' + datetime.datetime.now().strftime("%I:%M %p") + '\n')
    
    time.sleep(SLEEP)
    
    print('\nStore refress successful, all orders imported.\n')
else:
    print('Store refresh unsuccessful.')
    sys.exit()


# HTML file with google maps links, used to display location of foreign orders
with open(WORLD_MAP, 'w', encoding='utf-8') as f:
    f.write('\n')
import os
import sys
import time
import datetime
import requests
from requests.auth import HTTPBasicAuth

from config import API_KEY, SECRET_KEY, EBAY, WORLD_MAP, EBAY_ORDERS, EBAY_LOG, EBAY_IDS
import logic


AUTH = HTTPBasicAuth(API_KEY, SECRET_KEY)

# order information: the item Stock Keeping Unit (SKU) and its quantity
# key : str (SKU)
# val : str (quantity)
new_orders_dict = {}

# individual orders with an item quantity of more than one
# key : str (order number)
# val : tuple (str (customer name), str (SKU), str (quantity))
item_quantity_more_than_one_dict = {}

# customers with multiple orders
# key : str (customer name)
# val : int (quantity))
customer_name_more_than_one_dict = {}

# cleaned SKUs
# key : str (item brand and style)
# val : str (item size and quantity)
cleaned_orders_dict = {}

# these will be updated with the most recent order number to avoid processing new orders placed after the pick list is generated for this batch
most_recent_order_number = float('-inf')
most_recent_order_string = '0'


# order ID file: if no file exists it was purged so initialize new set for order IDs, if the file exists open and covert order IDs to a set
if not os.path.isfile(EBAY_IDS):
    order_id_set = set() # new order ID's
else:
    with open(EBAY_IDS, 'r') as f:
        # f.read() returns a string; split returns list; convert list to set
        order_id_set = set(f.read().split(','))


# create new empty log for each pick list
with open(EBAY_LOG, 'w', encoding='utf-8') as f:
    f.write('')


# refresh store to pull all new orders
try:
    EBAY_refresh = requests.post(f'https://ssapi.shipstation.com/stores/refreshstore?storeId={EBAY}', auth=AUTH)
except:
    print('Error with store refresh POST request.')
    sys.exit()

if EBAY_refresh.json()['success'] == 'true':
    # date and time as MM/DD/YYYY HH:MM:SS AM/PM
    print('\nImporting EBAY - ' + datetime.datetime.now().strftime('%A %b %d') + ' ' + datetime.datetime.now().strftime("%I:%M %p") + '\n')
else:
    print('Store refresh unsuccessful.')
    sys.exit()


# order data for all new orders awaiting shipment
await_ship_resp = requests.get(f'https://ssapi.shipstation.com/orders?orderStatus=awaiting_shipment&storeId={EBAY}&sortBy=OrderDate&sortDir=DESC&pageSize=500', auth=AUTH)

# list of JSON dicts
await_ship_list = await_ship_resp.json()['orders']


# display the store name and number of orders
current_number_of_orders = str(len(await_ship_list))
store_name = 'EBAY'
header_ending = ' ORDERS |'
# formatting
print('+' + ('-' * ( len(store_name) + len(current_number_of_orders) + len(header_ending) + 2)  ) + '+')
print('| ' + store_name + ': ' + current_number_of_orders + header_ending)
print('+' + ('-' * ( len(store_name) + len(current_number_of_orders) + len(header_ending) + 2)  ) + '+')


# set the most recent order number
for order in await_ship_list:
    # ShipStation API uses "orderKey" for eBay's updated order number and "orderNumber" for eBay's former serial order numbers
    order_num = order['orderKey']
    serial_order_num = order['orderNumber']
    # Then set most recent order number as the new eBay orderKey
    curr_order_num = int(serial_order_num)
    if curr_order_num > most_recent_order_number:
        most_recent_order_number = curr_order_num
        most_recent_order_string = order_num


# parse, clean, create pick list
logic.parse_awaiting_shipment_order_data(
    await_ship_list,
    customer_name_more_than_one_dict,
    order_id_set,
    EBAY_LOG,
    item_quantity_more_than_one_dict,
    EBAY_IDS,
    WORLD_MAP,
    new_orders_dict,
    is_ebay=True)

logic.clean_and_normalize_order_data(new_orders_dict, cleaned_orders_dict)

logic.create_pick_list(cleaned_orders_dict, EBAY_ORDERS)


# add most recent order number to pick list for verification
with open(EBAY_ORDERS, 'a', encoding='utf-8') as f:
    f.write('\n------------------------------------------')
    f.write('\n\nEBAY:  ' + str(most_recent_order_string))


# automatically open pick list! :)
os.system(f"open {EBAY_ORDERS}")

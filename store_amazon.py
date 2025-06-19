import os
import sys
import time
import datetime
import requests
from requests.auth import HTTPBasicAuth

from config import API_KEY, SECRET_KEY, AMAZON_USA, AMAZON_CAN, WORLD_MAP, AMAZON_ORDERS, AMAZON_LOG, AMAZON_IDS
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

# this will be updated with the most recent order number to avoid processing new orders placed after the pick list is generated for this batch
current_number_of_orders = '0'


# order ID file: if no file exists it was purged so initialize new set for order IDs, if the file exists open and covert order IDs to a set
if not os.path.isfile(AMAZON_IDS):
    order_id_set = set() # new order ID's
else:
    with open(AMAZON_IDS, 'r') as f:
        # f.read() returns a string; split returns list; convert list to set
        order_id_set = set(f.read().split(','))


# create new empty log for each pick list
with open(AMAZON_LOG, 'w', encoding='utf-8') as f:
    f.write('')


# refresh store to pull all new orders
try:
    USA_refresh = requests.post(f'https://ssapi.shipstation.com/stores/refreshstore?storeId={AMAZON_USA}', auth=AUTH)
    CAN_refresh = requests.post(f'https://ssapi.shipstation.com/stores/refreshstore?storeId={AMAZON_CAN}', auth=AUTH)
except:
    print('Error with store refresh POST request.')
    sys.exit()

if USA_refresh.json()['success'] == 'true' and CAN_refresh.json()['success'] == 'true':
    print('\nImporting AMAZON - ' + datetime.datetime.now().strftime('%A %b %d') + ' ' + datetime.datetime.now().strftime("%I:%M %p") + '\n')
else:
    print('Store refresh unsuccessful.')
    sys.exit()


# order data for all new orders awaiting shipment and (Amazon specific) pending fulfillment
USA_await_ship_resp = requests.get(f'https://ssapi.shipstation.com/orders?orderStatus=awaiting_shipment&storeId={AMAZON_USA}&sortBy=OrderDate&sortDir=DESC&pageSize=500', auth=AUTH)
USA_pend_ful_resp = requests.get(f'https://ssapi.shipstation.com/orders?orderStatus=pending_fulfillment&storeId={AMAZON_USA}&sortBy=OrderDate&sortDir=DESC&pageSize=500', auth=AUTH)
CAN_await_shipt_resp = requests.get(f'https://ssapi.shipstation.com/orders?orderStatus=awaiting_shipment&storeId={AMAZON_CAN}&sortBy=OrderDate&sortDir=DESC&pageSize=500', auth=AUTH)
CAN_pend_ful_resp = requests.get(f'https://ssapi.shipstation.com/orders?orderStatus=pending_fulfillment&storeId={AMAZON_CAN}&sortBy=OrderDate&sortDir=DESC&pageSize=500', auth=AUTH)

# list of JSON dicts
USA_await_ship_list = USA_await_ship_resp.json()['orders']
USA_pend_ful_list = USA_pend_ful_resp.json()['orders']
CAN_await_ship_list = CAN_await_shipt_resp.json()['orders']
CAN_pend_ful_list = CAN_pend_ful_resp.json()['orders']


# display the store name and number of orders
current_number_of_orders = str(len(USA_await_ship_list) + len(USA_pend_ful_list) + len(CAN_await_ship_list) + len(CAN_pend_ful_list))
store_name = 'AMAZON'
header_ending = ' ORDERS |'
# formatting
print('+' + ('-' * ( len(store_name) + len(current_number_of_orders) + len(header_ending) + 2)  ) + '+')
print('| ' + store_name + ': ' + current_number_of_orders + header_ending)
print('+' + ('-' * ( len(store_name) + len(current_number_of_orders) + len(header_ending) + 2)  ) + '+')


# parse, clean, create pick list
logic.parse_awaiting_shipment_order_data(
    USA_await_ship_list,
    customer_name_more_than_one_dict,
    order_id_set,
    AMAZON_LOG,
    item_quantity_more_than_one_dict,
    AMAZON_IDS,
    WORLD_MAP,
    new_orders_dict,
    is_ebay=False
    )

logic.parse_awaiting_shipment_order_data(
    USA_pend_ful_list,
    customer_name_more_than_one_dict,
    order_id_set,
    AMAZON_LOG,
    item_quantity_more_than_one_dict,
    AMAZON_IDS,
    WORLD_MAP,
    new_orders_dict,
    is_ebay=False
    )

logic.parse_awaiting_shipment_order_data(
    CAN_await_ship_list,
    customer_name_more_than_one_dict,
    order_id_set,
    AMAZON_LOG,
    item_quantity_more_than_one_dict,
    AMAZON_IDS,
    WORLD_MAP,
    new_orders_dict,
    is_ebay=False
    )

logic.parse_awaiting_shipment_order_data(
    CAN_pend_ful_list,
    customer_name_more_than_one_dict,
    order_id_set,
    AMAZON_LOG,
    item_quantity_more_than_one_dict,
    AMAZON_IDS,
    WORLD_MAP,
    new_orders_dict,
    is_ebay=False
    )

logic.clean_and_normalize_order_data(new_orders_dict, cleaned_orders_dict)

logic.create_pick_list(cleaned_orders_dict, AMAZON_ORDERS)


# add most recent order number to pick list for verification
with open(AMAZON_ORDERS, 'a', encoding='utf-8') as f:
    f.write('\n------------------------------------------')
    f.write('\n\nAMAZON: ' + current_number_of_orders + ' ORDERS\n')
    f.write('\nCUSTOMERS WITH MORE THAN ONE ORDER:\n\n')

    customer_with_multiple_orders = 0
    for key, value in customer_name_more_than_one_dict.items():
        if value > 1:
            customer_with_multiple_orders += 1
            f.write('\t' + key + ' - ' + str(value) + '\n')
    if customer_with_multiple_orders == 0:
        f.write('\t' + u'\U0001f4a9' + '\n')


# add orders with more than one item quantity to pick list
with open(AMAZON_ORDERS, 'a', encoding='utf-8') as f:
    f.write('\nORDERS WITH MORE THAN ONE ITEM QUANTITY:\n\n')
    if item_quantity_more_than_one_dict:
        for key, value in item_quantity_more_than_one_dict.items():
            for i in value:
                f.write('\t' + key + ' - ' + i + '\n')
    else:
        f.write('\t' + u'\U0001f4a9' + '\n')


# automatically open pick list! :)
os.system(f"open {AMAZON_ORDERS}")
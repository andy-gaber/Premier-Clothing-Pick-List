import requests
from sku_map import MAP


# helper: append order number and customer name to log
def _log_order_and_customer(order_num, cust_name, LOG_FILE):
	with open(LOG_FILE, 'a', encoding='utf-8') as f:
		f.write('+' + '-'*40 + '\n')
		f.write('| ' + order_num + '\n')
		f.write('| ' + cust_name + '\n')

# helper: append SKU and its quantity to log
def _log_sku_and_quantity(sku, quantity, LOG_FILE):
	# quantity = int
	with open(LOG_FILE, 'a', encoding='utf-8') as f:
		if quantity > 1:
			f.write('| ' + sku + ' (' + str(quantity) + ')' + '\n')
		else:
			f.write('| ' + sku + '\n')

# helper: append google maps location link to HTML file (only for foreign orders)
def _log_foreign_order(city, country, LOCATION_FILE):
	g_maps = f'https://www.google.com/maps/place/{city},+{country}/'

	with open(LOCATION_FILE, 'a', encoding='utf-8') as f:
		f.write(f'<h3><a href="{g_maps}">{city}, {country}</a><br></h3>' + '\n')


def parse_awaiting_shipment_order_data(
	awaiting_shipment_orders_list,
	customer_name_more_than_one_dict,
	order_id_set,
	LOG_FILE,
	item_quantity_more_than_one_dict,
	ID_FILE,
	LOCATION_FILE,
	new_orders_dict,
	is_ebay
):
	"""
	Parses JSON data of customers’ orders

		awaiting_shipment_orders_list: 		list of JSON dictionaries
		customer_name_more_than_one_dict: 	dictionary to keep track of a customers with multiple orders
		order_id_set: 						set of current batch of order IDs
		LOG_FILE: 							string of the name of the store's log file
		item_quantity_more_than_one_dict: 	dictionary to keep track if customer purchased more than one of a unique item
		ID_FILE: 							string of the name of the store's order ID file
		LOCATION_FILE: 						string of the name of the HTML file for foreign orders
		new_orders_dict: 					dictionary to keep track of items from the current batch of order IDs
		is_ebay: 							boolean to flag if currently processing orders from eBay
	"""

	# ShipStation API uses "orderKey" for eBay's updated order number and "orderNumber" for eBay's former serial order numbers
	for order in awaiting_shipment_orders_list:
		if is_ebay:  order_num = order['orderKey']
		else: 		 order_num = order['orderNumber']

		cust_name = order['billTo']['name']

		# keep track of customer name for each order to flag a customer with multiple orders (to combine shipping)
		if cust_name not in customer_name_more_than_one_dict:
			customer_name_more_than_one_dict[cust_name] = 1
		else:
			customer_name_more_than_one_dict[cust_name] += 1

		_log_order_and_customer(order_num, cust_name, LOG_FILE)
		
		items_list = order['items']  # list of dictionaries
		
		for item in items_list:
			sku = item['sku']
			description = item['name']   # item description that we provided
			quantity = item['quantity']  # this is an int

			# Clean the SKU
			if sku is None: 		 sku = description  # null
			elif sku == '': 		 sku = description  # empty string
			elif sku in MAP: 		 sku = MAP[sku]  	# revised SKU
			elif sku[:3] == 'wi_': 	 sku = description  # randomly generated
			elif sku[-3:] == '-SL':	 sku = sku[:-3]  	# obsolete
			elif sku[-4:] == '-SLL': sku = sku[:-4]  	# obsolete
			elif sku[-2:] == '-D': 	 sku = sku[:-2]  	# obsolete
			elif sku[-2:] == '-2':	 sku = sku[:-2]		# new SKU for FBA
			
			_log_sku_and_quantity(sku, quantity, LOG_FILE)

			# for Amazon only check if customer purchased more than one of a unique item
			if quantity > 1:
				# ex: "John Doe - PREM-612-SML (1)"
				cust_sku_quant = cust_name + ' - ' + sku + ' (' + str(quantity) + ')'

				# one item has more than one quantity
				if order_num not in item_quantity_more_than_one_dict:
					item_quantity_more_than_one_dict[order_num] = [cust_sku_quant]
				# multiple items has more than one quantity
				else:
					item_quantity_more_than_one_dict[order_num].append(cust_sku_quant)

			# add only new items to pick list
			if order_num not in order_id_set:
				if sku not in new_orders_dict:
					new_orders_dict[sku] = quantity
				else:
					new_orders_dict[sku] += quantity

		# add foreign city and country to HTML file 
		if order_num not in order_id_set:
			if order['shipTo']['country'] != 'US':
				city = order['shipTo']['city']
				country = order['shipTo']['country']
				_log_foreign_order(city, country, LOCATION_FILE)

		# add the order ID to ID file to mark it as not new
		with open(ID_FILE, 'a') as f:
			f.write(order_num + ',')


def clean_and_normalize_order_data(new_orders_dict, cleaned_orders_dict):
	"""
	Cleans and standardizes all SKUs in current batch of orders

		new_orders_dict: 		dictionary with SKU string as key and its quantity int as value (example entry: "PREM-612-XL": 1)
		cleaned_orders_dict : 	dictionary to keep track of cleaned SKUs
	"""

	# Each order added to the list will be a tuple of (str (SKU), int (quantity))
	for item, quantity in new_orders_dict.items():
		SKU = item
		sku_array = SKU.split('-')
		brand = sku_array[0]

		brand_and_style = None
		size = None

		#--- PREMIER
		if brand == 'PREM':
			# PREM-646-MED, PREM-631NEW-LRG, PREM-210P-5XL
			if len(sku_array) == 3:
				premier, style, _size = sku_array
				# PREM-631NEW-XL
				if style[-3:] == 'NEW':
					style = style[:3]
				brand_and_style = premier + '-' + style
				size = _size
			# PREM-618-RED-MED, PREM-SS-101-LRG, PREM-TS201-LS-SML, PREM-TS201-SS-SML
			elif len(sku_array) == 4:
				premier, index_1, index_2, _size = sku_array
				# T-Shirt SS / LS
				if index_1[:2] == 'TS':
					style = index_1[2:]
					# TS-LS-201 / TS-SS-201
					SS_or_LS_style = 'TS-' + index_2 + '-' + style
					brand_and_style = premier + '-' + SS_or_LS_style
				else:
					style = index_1 + '-' + index_2
					brand_and_style = premier + '-' + style
				size = _size
		#--- STEX
		elif brand == 'STEX' or brand == 'STX':
			stex, color, _size = sku_array
			# add number so colors in pick list are ordered the same as colors in warehouse
			if color == 'WHT':      stex = 'STEX4'
			elif color == 'BRIT':   stex = 'STEX9'
			elif color == 'GRN':    stex = 'STEX7'
			elif color == 'CHAR':   stex = 'STEX1'
			elif color == 'BLK':    stex = 'STEX3'
			elif color == 'GREY':   stex = 'STEX8'
			elif color == 'RED':    stex = 'STEX6'
			elif color == 'NAVY':   stex = 'STEX2'
			elif color == 'KAK':    stex = 'STEX5'
			brand_and_style = stex + '-' + color
			size = _size
		#--- WICK SHORTS and WEAR SHORTS 
		elif brand == 'WICK' or brand == 'WEAR':
			wick, color, _size = sku_array
			brand_and_style = wick + '-' + color
			size = _size
		#--- VESE and AMDS 
		elif brand == 'VESE' or brand == 'AMDS':
			# AMDS-RED-01-XL / VESE-GREEN-11-LRG
			vese_or_amds, color, style, _size = sku_array
			brand_and_style = vese_or_amds + '-' + style + '-' + color
			size = _size
		#--- CASUAL COUNTRY 
		elif brand == 'CAS' or brand == 'CASS':
			# CAS-PURP-01-LRG / CAS-NAV-3065-MED
			if len(sku_array) == 4:
				cas, color, style, _size = sku_array
				# CAS-NAV-3065-MED
				if style == '3065':
					style = 'SOLID-3065'
				brand_and_style = cas + '-' + style + '-' + color
				size = _size
			# CAS-SS-45-WHT-SML
			elif len(sku_array) == 5:
				cas, ss, style, color, _size = sku_array
				brand_and_style = cas + '-' + ss + '-' + style + '-' + color
				size = _size
		#--- RODEO and ACE OF DIAMONDS 
		elif brand == 'ROD' or brand == 'RODEO' or brand == 'ACE':
			# RODEO-524-XL
			if len(sku_array) == 3:
				rodeo, style, _size = sku_array
				brand_and_style = rodeo + '-' + style
				size = _size
			# RODEO-BEIG-533-MED, ROD-WOM-506-XL
			elif len(sku_array) == 4:
				rodeo_or_ace, color, style, _size = sku_array
				# strip 'PS400' from SKUs: RODEO-BRWN-PS400461N-MED
				if style[:5] == 'PS400':
					style = style[5:]
				# reorder big and tall SKUs: RODEO-RED-438BT -> RODEO-BT438-RED
				if style[-2:] == 'BT':
					style = style[-2:] + style[:3]
				# missing hyphen on some SKUs
				if style[:2] == 'ES':
					ES = style[:2]
					num = style[2:]
					style = ES + '-' + num
				# incorrect SKU: SS-2115 should be SS-2145
				if color == 'SS2115':
					color = style
					style = 'SS-2145'
				brand_and_style = rodeo_or_ace + '-' + style + '-' + color
				size = _size
			# ACE-WOM-BLU-ES5110-SML / ACE-HFK700-10-NVYBLU-3XL
			elif len(sku_array) == 5:
				# HFK700 / HFK200
				if sku_array[1] == 'HFK700' or sku_array[1] == 'HFK200':
					ace, hfk, style, color, _size = sku_array
					if hfk[3:] == '200':
						hfk = 'HFK-200'
					if hfk[3:] == '700':
						hfk = 'HFK-700'
					brand_and_style = ace + '-' + hfk + '-' + style + '-' + color
					size = _size
				# WOMENS
				else:
					ace, women, color, style, _size = sku_array
					brand_and_style = ace + '-' + women + '-' + style + '-' + color
					size = _size
		#--- BUCKEROO 
		elif brand == 'BUCK':
			# BUCK-WS6-BEGE/BRWN-LRG
			if len(sku_array) == 4:
				buck, style, color, _size = sku_array
				brand_and_style = buck + '-' + style + '-' + color
				size = _size
			# BUCK-WS100-01-BLACK/BLUE-SML / BUCK-WS200-01-BLACK/BLUE-SML
			elif len(sku_array) == 5:
				buck, style, number, color, _size = sku_array
				brand_and_style = buck + '-' + style + '-' + number + '-' + color
				size = _size
			# New Buckeroo LS/SS not in SKU MAP: ex) BUCK-WS200-SS-17-BURGBLK-XL
			elif len(sku_array) == 6:
				buck, style, LS_or_SS, number, color, _size = sku_array
				brand_and_style = buck + '-' + style + '-' + number + '-' + color
				size = _size
		#--- VICTORIOUS, ENVY, and SOCIETY JEANS
		elif brand == 'VIC' or brand == 'VICT' or brand == 'ENVY' or brand == 'SOCI':
			# VICT-DK211-XL / ENVY-41030-SML
			if len(sku_array) == 3:
				vic_or_envy, style, _size = sku_array
				brand_and_style = vic_or_envy + '-' + style
				size = _size
			# VICT-BLACK-1082-38X32 / ENVY-WHIT-18SS-XL / SOCI-BLU-80217-38X32
			elif len(sku_array) == 4:
				vic_or_envy_or_soci, color, style, _size = sku_array
				brand_and_style = vic_or_envy_or_soci + '-' + style + '-' + color
				size = _size
			# ENVY-LACEUP-WHT-41028-SML
			elif len(sku_array) == 5:
				envy, lace, color, style, _size = sku_array
				brand_and_style = envy + '-' + style + '-' + lace + '-' + color
				size = _size
			# VIC-100-DENIM-JACKET-DARK-INDIGO-XL
			elif len(sku_array) == 7:
				vic, style, denim, jacket, color1, color2, _size = sku_array
				brand_and_style = vic + '-' + style + '-' + denim + '-' + jacket + '-' + color1 + '-' + color2
				size = _size
		#--- VASSARI, BENZINI, GAVEL, and STEELO
		elif brand == 'VASS' or brand == 'BENZ' or brand == 'GAV' or brand == 'STEELO' or brand == 'BARA':
			# ex: VASS-LEOP-VS135-SML
			the_brand, color, style, _size = sku_array
			# incorrect SKU: BARA-B339-WHT/BLK should be BARA-B339-SIL
			if the_brand == 'BARA':
				if style == 'B339' and color == 'WHT/BLK':
					color = 'SIL'
			brand_and_style = the_brand + '-' + style + '-' + color
			size = _size
		#--- CANYON OF HEROES and NORTH-15
		elif brand == 'CAN' or brand == 'CANLADY':
			can_or_n15, style, color, _size = sku_array
			brand_and_style = can_or_n15 + '-' + style + '-' + color
			size = _size
		#--- EVERYTHING ELSE: remaining SKUs cannot be normalized
		else:
			cleaned_orders_dict[SKU] = str(quantity)
			continue

		if size == 'XXL':
			size = '2XL'

		size_and_quant = size + '-' + str(quantity)

		# add/update SKU in dictionary
		if brand_and_style not in cleaned_orders_dict:
			cleaned_orders_dict[brand_and_style] = [size_and_quant]
		else:
			cleaned_orders_dict[brand_and_style].append(size_and_quant)
					

def create_pick_list(cleaned_orders_dict, ORDERS_FILE):
	"""
	Generates the pick list file

		cleaned_orders_dict:	entry key is a string of an item's "brand-style" and entry value a string of the item's 
								"size-quantity" OR a list of the item's multiple "size-quantity" strings if multiple exist;
								example entry: {"PREM-612": "XL-1"} OR {"PREM-612": ["XL-1", "MED-2", "LRG-2"]}
		ORDERS_FILE: 			string of the name of the pick list file
	"""

	# dict for customized sorting; need to sort by clothing size 
	size_ordering = {
		'XS': 0,
		'SM': 1, 
		'ME': 2,
		'LA': 3,  # 'LARG'
		'LR': 4,  # 'LRG'
		'XL': 5, 
		'2X': 6, 
		'3X': 7, 
		'4X': 8, 
		'5X': 9, 
		'6X': 10, 
		'7X': 11, 
		'8X': 12, 
		'30': 13, 
		'32': 14, 
		'34': 15, 
		'36': 16, 
		'38': 17, 
		'40': 18, 
		'42': 19, 
		'44': 20, 
		'46': 21, 
		'48': 22, 
		'50': 23,
		'52': 24,
		'54': 25,
	}

	sorted_list_of_orders = []

	for key, value in cleaned_orders_dict.items():
		# if value is a list there are multiple sizes/quantities
		if type(value) is list:
			# sort by clothing size
			value.sort(key=lambda x: size_ordering[x[:2]])
			for i in range(len(value)):
				size, quant = value[i].split('-')
				# transform string of "size-quantity", and only include quantity in pick list if greater than one
				# ex: 'MED-1' -> 'MED'
				# ex: 'MED-2' -> 'MED (2)'
				if int(quant) == 1:
					value[i] = size
				else:
					value[i] = size + ' (' + quant + ')'

			# concat "->" for pick list
			key = key + ' -> '

			# concat sizes after the arrow; sizes are comma separated if applicable
			for i in range(len(value)):
				if i + 1 == len(value):
					key = key + str(value[i])
				else:
					key = key + str(value[i]) + ', '
			
			key = key + '\n'

			# formatting to read pick list more easily (left justification for some SKUs)
			L, R = key.split(' -> ')
			if L[:4] == 'BUCK':
				key = '{}{}'.format(L.ljust(33), R)
			elif L[:3] == 'ACE':
				key = '{}{}'.format(L.ljust(23), R)
			elif L[:3] == 'CAS':
				key = '{}{}'.format(L.ljust(23), R)
			elif L[:4] == 'STEX':
				key = '{}{}'.format(L.ljust(14), R)
			elif L[:4] == 'BARA':
				key = '{}{}'.format(L.ljust(21), R)
			elif L[:4] == 'VASS':
				key = '{}{}'.format(L.ljust(23), R)

		# if value is not a list there is just one size/quantity
		else:
			# only include quantity in pick list if greater than one 
			if int(value) > 1:
				key = key + ' ... (' + value + ')' + '\n'
			else:
				key = key + '\n'

		sorted_list_of_orders.append(key)

	# sorting the pick list
	sorted_list_of_orders.sort()

	# add newline between SKUs of different brands to read pick list more easily
	LEN = len(sorted_list_of_orders)
	if LEN > 1:
		brand = sorted_list_of_orders[0][:4]
		for i in range(LEN):
			if i + 1 == LEN:
				break
			_next = sorted_list_of_orders[i + 1][:4] 
			if _next != brand:
				brand = _next
				sorted_list_of_orders[i] += '\n'

	# generate the pick list
	with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
		for item in sorted_list_of_orders:
			f.write(item)
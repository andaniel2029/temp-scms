# from app import db, Order, OrderLineItem, easypost
#
# o = Order.query.get(22)
#
#
#
# # Note: This uses case weights, even for units (unit weights are calculated based on case weight and quantity in case, not obtained directly from data)
# packages = []
# total_packages = 0
# unit_weight_tally = 0
#
# for li in o.line_items:
# 	if li.item.case_weight > 150:
# 		raise ValueError("Weight over 150 lbs")
#
# 	# Rejoin individual units into cases where appropriate (this wasn't in original spec)
# 	if li.quantity_units > li.item.case_quantity:
# 		while li.quantity_units > li.item.case_quantity:
# 			li.quantity_units = li.quantity_units - li.item.case_quantity
# 			li.quantity_cases = li.quantity_cases + 1
#
# 	if li.quantity_cases > 0:
# 		total_packages = total_packages + li.quantity_cases
# 		print '%i packages at weight: %i because of a case.' % (li.quantity_cases, li.item.case_weight)
# 		for i in range(0,li.quantity_cases):
# 			packages.append([1, float(li.item.case_weight)])
# 	if li.quantity_units > 0:
# 		for i in range(0,li.quantity_units):
# 			# Projected weight if we were to add it to the current odd unit package
# 			p_unit_weight_tally = unit_weight_tally + (li.item.case_weight/li.item.case_quantity)
# 			print(p_unit_weight_tally)
# 			if p_unit_weight_tally > 150:
# 				# Would be too heavy if we added this to the current odd unit package, start a new one
# 				print 'plus a package of odd units at weight %i' % unit_weight_tally
# 				packages.append([1, float(unit_weight_tally)])
# 				total_packages = total_packages+1
# 				unit_weight_tally = (li.item.case_weight/li.item.case_quantity)
# 			else:
# 				# Can add.
# 				unit_weight_tally = p_unit_weight_tally
#
# if unit_weight_tally>0:
# 	total_packages = total_packages+1
# 	print 'plus a package of odd units at weight %i' % unit_weight_tally
# 	packages.append([1, float(unit_weight_tally)])
#
#
# print total_packages
# print(packages)
#
#
#
# shipments = []
# for i in packages:
# 	shipments.append({"parcel": {"weight": i[1]*16}}) # 16 oz per pound
#
# print(shipments)
#
# #other_address = easypost.Address.create(
# #                company='TARA STEINBACH - ALLEN & SON MOVING STORAGE - MDL 647 Maryland Live',
# #                street1 = '2901 DRUID PARK DR',
# #                street2 = '',
# #                city = 'BALTIMORE',
# #                state = 'MD',
# #                zip = '21215-8102',
# #                phone = '8557838547',
# #                country = 'US'
# #                )
#
# #warehouse_address = easypost.Address.create(
# #                        company='Vita Futura',
# #                        street1 = '660 Howard St',
# #                        city = 'Buffalo',
# #                        state = 'NY',
# #                        country = 'US',
# #                        zip = '14206-2209',
# #                        phone = '646-876-8482'
# #                )
# #
# #
# #order = easypost.Order.create(
# #                                to_address=other_address,
# #                                from_address = warehouse_address,
# #                                shipments = shipments#
# #			)
#
#
# #print(order)

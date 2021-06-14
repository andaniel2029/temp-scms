# import easypost
# easypost.api_key = "oY9cHs4xTSaoU30E9osj3Q"
#
# fromAddress = easypost.Address.create(
#   company='EasyPost',
#   street1='417 Montgomery Street',
#   street2='5th Floor',
#   city='San Francisco',
#   state='CA',
#   zip='94104',
#   phone='415-528-7555'
# )
#
# toAddress = easypost.Address.create(
#   name='George Costanza',
#   company='Vandelay Industries',
#   street1='1 E 161st St.',
#   city='Bronx',
#   state='NY',
#   zip='10451'
# )
#
# parcel = easypost.Parcel.create(
#   length=9,
#   width=6,
#   height=2,
#   weight=10
# )
#
# shipment = easypost.Shipment.create(
#   to_address=toAddress,
#   from_address=fromAddress,
#   parcel=parcel
# )
#
# print shipment
#
# for rate in shipment.rates:
#   print rate.carrier
#   print rate.service
#   print rate.rate
#   print rate.id
#

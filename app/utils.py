# How should this overall order be split into packages?
import csv
import sys
from datetime import datetime

from flask.json import JSONEncoder

from flask import request
from flask_login import current_user

from app.constants import carrier_services
from app.models import Order, Recipient, User, db
from app.models import OrderLineItem, Inventory


# Usually based on current_user unless superadmin or warehouse staff with a different sudo
def get_user_id():
    user_id = current_user.id
    if current_user.has_roles('superadmin') or current_user.has_roles('warehouse'):
        if request.cookies.get('sudo'):
            user_id = request.cookies.get('sudo')
    return user_id


def build_discount_table(user):
    discount_table = {}
    for c in carrier_services:
        if not c['carrier'] in discount_table:
            discount_table[c['carrier']] = {}
        discount_table[c['carrier']][c['service']] = 0
    for d in user.shipping_discounts:
        discount_table[d.carrier][d.service] = float(d.discount)
    return discount_table


# Creates/updates Inventory record from CSV data row
def inv_from_row(inv, row):
    inv.name = row['Item Name']
    inv.number = row['Item #']
    inv.case_quantity = row['Units in Case']
    inv.description = row['Unit Description']
    inv.qoh_case = row['Current Quantity Cases']
    inv.qoh_units = row['Current Quantity Units']
    inv.case_weight = row['Case Weight']
    if 'Re-order Quantity' in row:
        inv.reorder_quantity = row['Re-order Quantity']
    if 'Length' in row:
        inv.length = row['Length']
        if inv.length == '':
            inv.length = 0
    if 'Width' in row:
        inv.width = row['Width']
        if inv.width == '':
            inv.width = 0
    if 'Height' in row:
        inv.height = row['Height']
        if inv.height == '':
            inv.height = 0
    if 'Ship Ready' in row:
        # TODO: We don't have the spec for what this field *should* be.
        if row['Ship Ready'] == 'TRUE' or row['Ship Ready'] == '1' or row['Ship Ready'] == 'Yes' or row[
            'Ship Ready'] == 'Y':
            inv.ship_ready = True
        else:
            inv.ship_ready = False
    return inv


def parse_inventory_upload(filename, user_id=-1):
    if user_id == -1:
        user_id = get_user_id()

    errors = []
    required_columns = ["Units in Case", "Unit Description", "Current Quantity Cases", "Current Quantity Units",
                        "Item #", "Case Weight"]
    optional_columns = ["Item Name", "Re-order Quantity", "Length", "Width", "Height", "Ship Ready"]
    all_columns = required_columns + optional_columns
    csv_data = {}

    try:
        with open(filename, 'rU') as csvfile:
            reader = csv.DictReader(csvfile)
            r = 0
            for row in reader:
                r = r + 1

                # Even though these don't match the spec we were given, we want to be able to directly import inventory from the old system
                #### BEGIN ADJUSTMENTS TO LEGACY FILES
                if 'Transaction ID' in row or 'Shipping Method' in row:
                    errors.append(
                        "It looks like you might be trying to upload an order file as an inventory file. Don't do that.")
                if 'Units per Case' in row and not 'Units in Case' in row:
                    row['Units in Case'] = row['Units per Case']
                if 'Cases' in row and not 'Current Quantity Cases' in row:
                    row['Current Quantity Cases'] = row['Cases']
                if 'Units' in row and not 'Current Quantity Units' in row:
                    row['Current Quantity Units'] = row['Units']
                if 'Description' in row and not 'Unit Description' in row:
                    row['Unit Description'] = row['Description']
                if 'Item Name' not in row:
                    row['Item Name'] = row['Item #']
                #### END ADJUSTMENTS TO LEGACY FILES

                for col in required_columns:
                    if not col in row:
                        errors.append("Missing expected column: %s in row %i" % (col, r))

                inv = Inventory.query.filter(
                    (Inventory.name == row['Item Name']) | (Inventory.number == row['Item #'])).first()
                if inv:
                    # Update existing record
                    inv = inv_from_row(inv, row)
                    db.session.add(inv)
                    db.session.commit()
                else:
                    # Create new record
                    inv = Inventory()
                    inv.user_id = user_id
                    inv = inv_from_row(inv, row)
                    db.session.add(inv)
                    db.session.commit()
    except:
        errors.append("Unexpected error: %s %s" % (sys.exc_info()[0], sys.exc_info()[1]))
        return errors
    return errors


def parse_order_upload(filename, user_id):
    user = User.query.get(user_id)

    errors = []
    required_columns = ["Transaction ID", "Item", "Unit of Measure", "Quantity", "Insured Value", "Carrier",
                        "Shipping Method", "Contact Name", "Phone", "Address 1", "City", "State Code", "Zip",
                        "Country Code"]
    optional_columns = ["Company Name", "Email", "Address 2", "Residential", "Signature Option", "Blind Shipper Name",
                        "Blind Shipper Phone", "Blind Ship Company", "Blind Ship Company Phone", "Customs Value",
                        "Customs Description", "Send Tracking"]
    all_columns = required_columns + optional_columns

    csv_data = {}
    try:
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            r = 0
            skip_row = False
            for row in reader:
                r = r + 1
                for col in required_columns:
                    if not col in row:
                        errors.append("Missing expected column: %s in row %i" % (col, r))
                        skip_row = True

                if not skip_row and row['Transaction ID'] in csv_data:
                    # Add any additional line items
                    csv_data[row['Transaction ID']]['items'].append(
                        {'Item': row['Item'], 'Unit Of Measure': row['Unit of Measure'], 'Quantity': row['Quantity'],
                         'Insured Value': row['Insured Value']}
                    )
                elif not skip_row:
                    # Grab address, etc. from first line with a given transaction ID (others with this info are ignored)
                    csv_data[row['Transaction ID']] = {}
                    csv_data[row['Transaction ID']]['items'] = [
                        {'Item': row['Item'], 'Unit Of Measure': row['Unit of Measure'],
                         'Quantity': row['Quantity'], 'Insured Value': row['Insured Value']}
                    ]
                    for c in all_columns:
                        if c in row:
                            csv_data[row['Transaction ID']][c] = row[c]

    except:
        errors.append("Unexpected error: %s %s" % (sys.exc_info()[0], sys.exc_info()[1]))
    # TODO: Enforce some constraints documented in CSV Word file?

    # Create recipients (contacts) if they don't already exist.
    for o in csv_data:
        o = csv_data[o]
        r = Recipient.query.filter_by(user_id=user_id, name=o.get('Company Name'), contact=o.get('Contact Name'),
                                      phone=o.get('Phone'), email=o.get('Email'), street1=o.get('Address 1'),
                                      street2=o.get('Address 2'), city=o.get('City'), state=o.get('State Code'),
                                      postal=o.get('Zip').replace("'", ""), country=o.get('Country Code')).first()
        if not r:
            # Print creating new recipient and adding it to the database
            r = Recipient()
            r.user_id = user_id
            r.name = o.get('Company Name')
            r.contact = o.get('Contact Name')
            r.phone = o.get('Phone')
            r.email = o.get('Email')
            r.street1 = o.get('Address 1')
            r.street2 = o.get('Address 2')
            r.city = o.get('City')
            r.state = o.get('State Code')
            r.postal = o.get('Zip').replace("'", "")
            r.country = o.get('Country Code').replace("USA", "US").replace("United States", "US")
            try:
                db.session.add(r)
                db.session.commit()
            except:
                errors.append("Failure with recipient information. Bad data? %s %s" % (
                    o.get('Company Name'), o.get('Contact Name')))
                db.session.rollback()
        # Set up recipient in the data
        o['Recipient_ID'] = r.id

    # Create orders
    fail = False
    for o in csv_data:
        reference_id = o
        o = csv_data[o]

        rq = Order()
        rq.user_id = user_id
        try:
            r = Recipient.query.get(o.get('Recipient_ID'))
        except:
            errors.append("Cannot process order due to bad recipient data %s" % reference_id)
            fail = True
            continue
        rq.recipient_id = o.get('Recipient_ID')
        rq.customer_reference = reference_id

        # Blind shipping options
        if "Blind Ship Company" in o and len(o.get('Blind Ship Company').strip()) > 0:
            rq.blind_company = o.get('Blind Ship Company')
        if "Blind Ship Company Phone" in o and len(o.get('Blind Ship Company Phone').strip()) > 0:
            rq.blind_phone = o.get('Blind Ship Company Phone')
        if "Blind Shipper Name" in o and len(o.get('Blind Shipper Name').strip()) > 0:
            rq.blind_company = o.get('Blind Shipper Name')
        if "Blind Shipper Phone" in o and len(o.get('Blind Shipper Phone').strip()) > 0:
            rq.blind_phone = o.get('Blind Shipper Phone')

        # Customs Declarations (undocumented feature)
        if "Customs Value" in o:
            rq.customs_value = o.get("Customs Value")
        if "Customs Description" in o:
            rq.customs_description = o.get("Customs Description")

        if user.send_tracking_emails_by_default:
            rq.notify_recipient = True

        # Undocumented feature to override sending tracking emails to recipients
        if "Send Tracking" in o:
            if o.get("Send Tracking") == 'True':
                rq.notify_recipient = True
            else:
                rq.notify_recipient = False

        rq.recipient = r
        for li in o.get('items'):
            inv_item = Inventory.query.filter_by(user_id=user_id, number=li['Item']).first()
            if not inv_item:
                errors.append("Cannot find item %s in inventory for user %i" % (li['Item'], user_id))
                fail = True
            else:
                oli = OrderLineItem()
                oli.item_id = inv_item.id
                oli.quantity_cases = 0
                oli.quantity_units = 0
                if li['Unit Of Measure'].upper() == 'U':
                    oli.quantity_units = int(li['Quantity'])
                elif li['Unit Of Measure'].upper() == 'C':
                    oli.quantity_cases = int(li['Quantity'])
                else:
                    errors.append("Unrecognized unit of measure %s" % li['Unit Of Measure'])
                    fail = True

                # Rejoin/consolidate units into cases
                if oli.quantity_units >= inv_item.case_quantity:
                    while oli.quantity_units >= inv_item.case_quantity:
                        oli.quantity_units = oli.quantity_units - inv_item.case_quantity
                        oli.quantity_cases = oli.quantity_cases + 1

                # Check for sufficient inventory
                if inv_item.qoh_case < oli.quantity_cases:
                    if inv_item.qoh_case + int(inv_item.qoh_units / inv_item.case_quantity) < oli.quantity_cases:
                        errors.append("Not enough cases of %s for order %s" % (inv_item.number, reference_id))
                        fail = True
                    else:
                        # Someone split too many cases, need to rejoin them.
                        while inv_item.qoh_case < oli.quantity_cases:
                            inv_item.qoh_case = inv_item.qoh_case + 1
                            inv_item.qoh_units = inv_item.qoh_units - inv_item.case_quantity
                elif inv_item.qoh_units < oli.quantity_units:
                    # Split cases (if we have them, and, if we can get enough units that way)
                    if inv_item.qoh_case > 0 and inv_item.qoh_case * inv_item.case_quantity > oli.quantity_units:
                        while inv_item.qoh_units < oli.quantity_units:
                            inv_item.qoh_case = inv_item.qoh_case - 1
                            inv_item.qoh_units = inv_item.qoh_units + inv_item.case_quantity
                    # Nope
                    else:
                        errors.append("Not enough units of %s for order %s" % (inv_item.number, reference_id))
                        fail = True

                if not fail:
                    inv_item.qoh_units = inv_item.qoh_units - oli.quantity_units
                    inv_item.qoh_case = inv_item.qoh_case - oli.quantity_cases
                    rq.line_items.append(oli)
        if not fail:
            # TODO: Current behaviour doesn't fail on entire file if some orders can be completed.
            # It only fails on a per-order basis
            rq.status = 1

            rq.requested_carrier = o.get('Carrier')
            rq.requested_service = o.get('Shipping Method')

            # Map old PriorityBiz naming onto new naming
            if rq.requested_carrier == 'FEDEX':
                rq.requested_carrier = "FedEx"
            if rq.requested_service == 'FEDEXGROUND':
                rq.requested_service = "FEDEX_GROUND"
            elif rq.requested_service == 'FEDEX GROUND':  # There's a client who's doing this.
                rq.requested_service = "FEDEX_GROUND"
                # Below options are Added on 30-01-2021
            elif rq.requested_service == "FedExEnvelope":
                rq.requested_service = 'FedExEnvelope'
            elif rq.requested_service == "FedExPak":
                rq.requested_service = 'FedExPak'
            elif rq.requested_service == "FedExSmallBox":
                rq.requested_service = 'FedExSmallBox'
            elif rq.requested_service == "FedExMediumBox":
                rq.requested_service = 'FedExMediumBox'
                #Above options are Added on 30-01-2021
            elif rq.requested_service == "FEDEX2DAY":
                rq.requested_service = 'FEDEX_2_DAY'
            elif rq.requested_service == "FEDEX2DAYAM":
                rq.requested_service = 'FEDEX_2_DAY_AM'
            elif rq.requested_service == 'FEDEXEXPRESSSAVER':
                rq.requested_service = 'FEDEX_EXPRESS_SAVER'
            elif rq.requested_service == 'STANDARDOVERNIGHT':
                rq.requested_service = 'STANDARD_OVERNIGHT'
            elif rq.requested_service == 'FIRSTOVERNIGHT':
                rq.requested_service = 'FIRST_OVERNIGHT'
            elif rq.requested_service == 'PRIORITYOVERNIGHT':
                rq.requested_service = 'PRIORITY_OVERNIGHT'
            elif rq.requested_service == 'INTERNATIONALECONOMY':
                rq.requested_service = 'INTERNATIONAL_ECONOMY'
            elif rq.requested_service == 'INTERNATIONALFIRST':
                rq.requested_service = 'INTERNATIONAL_FIRST'
            elif rq.requested_service == 'INTERNATIONALPRIORITY':
                rq.requested_service = 'INTERNATIONAL_PRIORITY'
            elif rq.requested_service == 'GROUNDHOMEDELIVERY':
                rq.requested_service = 'GROUND_HOME_DELIVERY'
            elif rq.requested_service == 'SMARTPOST':
                rq.requested_carrier = 'FedExSmartPost'
                rq.requested_service = 'SMART_POST'
            elif rq.requested_service == 'SMART_POST':
                rq.requested_carrier = 'FedExSmartPost'
                rq.requested_service = 'SMART_POST'
            elif rq.requested_carrier == 'USPS':
                if rq.requested_service == 'First' or (
                        'FIRST' in rq.requested_service.upper() and 'INTERN' not in rq.requested_service.upper()):
                    rq.requested_service = 'First'
                elif rq.requested_service == 'Priority' or (
                        'PRIORITY' in rq.requested_service.upper() and 'INTERN' not in rq.requested_service.upper()):
                    rq.requested_service = 'Priority'
                elif rq.requested_service == 'Express' or (
                        'EXPRESS' in rq.requested_service.upper() and 'INTERN' not in rq.requested_service.upper()):
                    rq.requested_service = 'Express'
                elif rq.requested_service == 'ParcelSelect' or ('PARCEL' in rq.requested_service.upper()):
                    rq.requested_service = 'ParcelSelect'
                elif rq.requested_service == 'LibraryMail' or ('LIB' in rq.requested_service.upper()):
                    rq.requested_service = 'LibraryMail'
                elif rq.requested_service == 'MediaMail' or ('MEDIA' in rq.requested_service.upper()):
                    rq.requested_service = 'MediaMail'
                elif rq.requested_service == 'FirstClassMailInternational' or (
                        'FIRST' in rq.requested_service.upper() and 'INTERN' in rq.requested_service.upper() and 'PACK' not in rq.requested_service.upper()):
                    rq.requested_service = 'FirstClassMailInternational'
                elif rq.requested_service == 'FirstClassPackageInternationalService':
                    rq.requested_service = 'FirstClassPackageInternationalService'
                elif rq.requested_service == 'PriorityMailInternational' or (
                        'PRIORITY' in rq.requested_service.upper() and 'INTERN' in rq.requested_service.upper()):
                    rq.requested_service = 'PriorityMailInternational'
                elif rq.requested_service == 'ExpressMailInternational' or (
                        'EXPRESS' in rq.requested_service.upper() and 'INTERN' in rq.requested_service.upper()):
                    rq.requested_service = 'ExpressMailInternational'
                else:
                    errors.append(
                        "Warning: Unrecognized service '%s' with carrier USPS for transaction ID %s (Did you check "
                        "for typos? Extra spaces? Spaces instead of underscores, etc? Mismatch of requested carrier "
                        "and available services?). Will fall back to Priority. Available service levels: "
                        "https://www.easypost.com/docs/api/python#service-levels" % (
                            rq.requested_service, o['Transaction ID']))
                    rq.requested_service = 'Priority'
            else:
                rq.requested_carrier = 'FedEx'
                rq.requested_service = 'FEDEX_GROUND'
                errors.append(
                    "Warning: Unrecognized service '%s' for transaction ID %s (Did you check for typos? Extra spaces? "
                    "Spaces instead of underscores, etc?). Will fall back to FEDEXGROUND" % (
                        rq.requested_service, o['Transaction ID']))
            db.session.add(rq)
            db.session.commit()
        else:
            errors.append("Failure, skipping order with transaction ID %s" % o['Transaction ID'])
            db.session.rollback()
        fail = False

    return errors


# How should this overall order be split into packages?
def split_packages(order):  # order should be Order type
    # Unknown situation: what happens if a single case is > 150 lbs?
    # Answer: fail with error

    # Unknown situation: is this expected to optimize odd units across boxes? (Assuming: no, assuming just go in the
    # order of the line items)

    # Note: This uses case weights, even for units (unit weights are calculated based
    # on case weight and quantity in case, not obtained directly from data)
    packages = []
    total_packages = 0
    unit_weight_tally = 0

    for li in order.line_items:
        if li.item.case_weight > 150:
            raise ValueError("Weight over 150 lbs")

        # Rejoin/consolidate individual units into cases where appropriate (this wasn't in original spec; but,
        # is necessary to get desired result)
        if li.quantity_units >= li.item.case_quantity:
            while li.quantity_units > li.item.case_quantity:
                li.quantity_units = li.quantity_units - li.item.case_quantity
                li.quantity_cases = li.quantity_cases + 1

        if li.quantity_cases > 0:
            total_packages = total_packages + li.quantity_cases
            for i in range(0, li.quantity_cases):
                packages.append([1, float(li.item.case_weight)])

        if li.quantity_units > 0:
            for i in range(0, li.quantity_units):
                # Projected weight if we were to add it to the current odd unit package
                p_unit_weight_tally = unit_weight_tally + (li.item.case_weight / li.item.case_quantity)
                if p_unit_weight_tally > 150:
                    # Would be too heavy if we added this to the current odd unit package, start a new one
                    packages.append([1, float(unit_weight_tally)])
                    total_packages = total_packages + 1
                    unit_weight_tally = (li.item.case_weight / li.item.case_quantity)
                else:
                    # Can add.
                    unit_weight_tally = p_unit_weight_tally

    if unit_weight_tally > 0:
        total_packages = total_packages + 1
        packages.append([1, float(unit_weight_tally)])

    return packages


def sudo():
    sudo = current_user.username
    cookie = request.cookies.get('sudo')
    if cookie:
        u = User.query.get(cookie)
        if u:
            return "User: %s performing actions as: <strong>%s</strong>. <a href='/sudo'>Become someone else</a>" % (
            sudo, u.username)
        else:
            return "<a href='/sudo'>Become someone else</a>"
    else:
        return "<a href='/sudo'>Become someone else</a>"


def get_paginated(data, offset=0, per_page=10):
    return data.offset


class CustomJSONEncoder(JSONEncoder):
    "Add support for serializing timedeltas"

    def default(o):
        if type(o) == datetime.timedelta:
            return str(o)
        elif type(o) == datetime.datetime:
            return o.isoformat()
        else:
            return super().default(o)
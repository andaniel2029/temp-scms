import json
import os
import random
from datetime import time, timedelta

from sqlalchemy.sql import text
from werkzeug.utils import secure_filename

import easypost
from app import mail, user_manager
from app.forms import *
from app.models import *
from app.utils import *
from flask import (current_app, jsonify, make_response, render_template,
                   send_file)
from flask.json import dumps
from flask_mail import Message
from flask_paginate import Pagination, get_page_args, get_page_parameter
from flask_user import login_required


def sudo_form(message="", menu="", menutab=""):
    f = SudoForm()
    if 'sudo' in f:
        f.sudo.choices = [(u.id, "%s - %s - %s " % (u.username, u.first_name, u.last_name)) for u in
                          User.query.order_by('username')]
    if 'sudo' in request.values and (current_user.has_roles('superadmin') or current_user.has_roles('warehouse')):
        res = make_response("")
        res.set_cookie("sudo", request.values['sudo'], 60 * 60 * 24 * 15)
        res.headers['location'] = '/'
        return res, 302
    return render_template('form.html', form=f, message=message, menu=menu, menutab=menutab)


def form_crud_user_id(obj_id, user_id, model, form, message="", menu='', menutab='', rid=False):
    if obj_id:
        try:
            rq = model.query.filter_by(id=obj_id, user_id=user_id).first()
        except:
            # Users don't have a user_id reference
            rq = model.query.filter_by(id=obj_id).first()
    else:
        rq = None
    f = form(obj=rq)

    # Fill in recipients from the database
    if 'recipient' in f:
        f.recipient.choices = [(r.id, "%s - %s - %s " % (r.name, r.contact, r.street1)) for r in
                               Recipient.query.filter_by(user_id=user_id).order_by(text('id desc')).limit(25)]
        if rid:
            f.recipient.data = rid

    if f.validate_on_submit():
        # Username must be unique.
        if 'username' in f and ('id' not in f or f.id.data == '0'):
            username_exists = User.query.filter_by(username=f.username.data).first()
            if username_exists:
                errors = ["You cannot add a new user with the same username as an existing user.", ]
                return render_template('errors.html', errors=errors, menu='user', menutab='add-update')

        if 'email' in f and ('id' not in f or f.id.data == '0'):
            email_exists = User.query.filter_by(email=f.email.data).first()
            if email_exists:
                errors = ["You cannot add a new user with the same email as an existing user.", ]
                return render_template('errors.html', errors=errors, menu='user', menutab='add-update')
        
        if 'phone' in f and ('id' not in f or f.id.data == '0'):
            phone_exists = User.query.filter_by(phone=f.phone.data).first()
            if phone_exists:
                errors = ["You cannot add a new user with the same phone as an existing user.", ]
                return render_template('errors.html', errors=errors, menu='user', menutab='add-update')

        r = None
        # Edit
        if rq and (current_user.has_role('superadmin') or int(rq.user_id) == int(user_id)):
            r = rq
        # Create
        else:
            r = model()
            r.user_id = user_id
            db.session.add(r)

        if 'password' in f:
            if 'password' in f and f.password.data:
                r.password = user_manager.hash_password(f.password.data)
                f.password.data = r.password
            else:
                f._fields.pop('password')
        f.populate_obj(r)
        db.session.commit()

        # Allow redirecting (TODO: Secure this against external URLs, etc.? Make this more generic?)
        if 'next' in request.values and request.values['next']:
            n = request.values['next']
            if '?' in n:
                return redirect("%s&USE_MAX_RECIPIENT=1" % request.values['next'])
            else:
                return redirect("%s?USE_MAX_RECIPIENT=1" % request.values['next'])
        else:
            return render_template('done.html')
    return render_template('form.html', form=f, message=message, menu=menu, menutab=menutab)


@current_app.route('/recipient/add-update', methods=['GET', 'POST'])
@login_required
def recipient_form():
    if 'id' in request.values:
        return form_crud_user_id(request.values['id'], get_user_id(), Recipient, RecipientForm, menu='recipient',
                                 menutab='add-update')
    else:
        return form_crud_user_id(None, get_user_id(), Recipient, RecipientForm, menu='recipient', menutab='add-update')


@current_app.route('/inventory/add-update', methods=['GET', 'POST'])
@login_required
def inventory_form():
    if 'id' in request.values:
        return form_crud_user_id(request.values['id'], get_user_id(), Inventory, InventoryForm, menu='inventory',
                                 menutab='add-update')
    else:
        return form_crud_user_id(None, get_user_id(), Inventory, InventoryForm, menu='inventory', menutab='add-update')


@current_app.route('/order/add-update', methods=['GET', 'POST'])
@login_required
def order_form():
    if 'id' in request.values and request.values['id'] and (
            current_user.has_roles('superadmin') or current_user.has_roles('warehouse')):
        rq = Order.query.filter_by(id=request.values['id']).first()
    elif 'id' in request.values:
        rq = Order.query.filter_by(id=request.values['id'], user_id=get_user_id()).first()
    else:
        rq = None

    # TODO: This is a bit of a hack
    r = None
    if 'USE_MAX_RECIPIENT' in request.values:
        r = Recipient.query.order_by(text('id DESC')).first()

    if 'id' in request.values:
        if not rq:
            rq = Order()
            rq.user_id = get_user_id()
            if r:
                rq.recipient = r
                rq.recipient_id = r.id

        # Might be there on new or existing?
        if 'recipient' in request.values:
            r = Recipient.query.get(request.values['recipient'])
            rq.recipient_id = request.values['recipient']
            rq.recipient = r

        if 'customer_reference' in request.values:
            if len(request.values['customer_reference']) > 0:
                rq.customer_reference = request.values['customer_reference']
        if 'blind_company' in request.values:
            if len(request.values['blind_company']) > 0:
                rq.blind_company = request.values['blind_company']
            else:
                rq.blind_company = None
        if 'blind_phone' in request.values:
            if len(request.values['blind_phone']) > 0:
                rq.blind_phone = request.values['blind_phone']
            else:
                rq.blind_phone = None
        if 'notify_recipient' in request.values:
            if len(request.values['notify_recipient']) > 0:
                rq.notify_recipient = True
            else:
                rq.notify_recipient = False
        if 'additionally_notify' in request.values:
            if len(request.values['additionally_notify']) > 0:
                rq.additionally_notify = request.values['additionally_notify']
            else:
                rq.additionally_notify = None
        if 'insurance_value' in request.values:
            if len(request.values['insurance_value']) > 0:
                rq.insurance_value = request.values['insurance_value']
            else:
                rq.insurance_value = 0
        if 'signature_option' in request.values:
            if len(request.values['signature_option']) > 0:
                rq.signature_option = request.values['signature_option']
            else:
                rq.signature_option = "NO_SIGNATURE"
        db.session.add(rq)
        db.session.commit()

        if 'action' in request.values and request.values['action'] == 'add_to_order':
            rq.line_items.append(OrderLineItem(item_id=request.values['line_id'], order_id=rq.id))
            db.session.commit()
        elif 'action' in request.values and request.values['action'] == 'remove_line_item':
            li = OrderLineItem.query.filter_by(id=request.values['line_id']).first()
            if li.order.user_id == current_user.id or current_user.has_roles('superadmin') or current_user.has_roles(
                    'warehouse'):
                # Add inventory back.
                li.item.qoh_case = li.item.qoh_case + li.quantity_cases
                li.item.qoh_units = li.item.qoh_units + li.quantity_units
                db.session.commit()

                # Delete the line item
                db.session.delete(li)
                db.session.commit()
        elif 'action' in request.values and request.values['action'] == 'adjust_qty':
            li = OrderLineItem.query.filter_by(id=request.values['line_id']).first()
            if li.order.user_id == current_user.id or current_user.has_roles('superadmin') or current_user.has_roles(
                    'warehouse'):
                # Add old inventory count back
                li.item.qoh_case = li.item.qoh_case + li.quantity_cases
                li.item.qoh_units = li.item.qoh_units + li.quantity_units
                db.session.commit()

                # Subtract new inventory count
                if request.values['quantity_units'] != '':
                    li.quantity_units = int(request.values['quantity_units'])
                    li.item.qoh_units = li.item.qoh_units - li.quantity_units
                    while li.item.qoh_units < 0:
                        li.item.qoh_case = li.item.qoh_case - 1
                        li.item.qoh_units = li.item.qoh_units + li.item.case_quantity
                else:
                    li.quantity_units = 0
                if request.values['quantity_cases'] != '':
                    li.quantity_cases = int(request.values['quantity_cases'])
                    li.item.qoh_case = li.item.qoh_case - li.quantity_cases
                else:
                    li.quantity_cases = 0
                db.session.commit()
        elif 'action' in request.values and request.values['action'] == 'select_ship_method':
            message = ""

            # Calculate # and size of boxes, etc.
            packages = split_packages(rq)
            shipments = []

            insurance_cost = 0
            options = {
                'print_custom_1': "PB/%s" % rq.user.username,
                'delivered_duty_paid': 'false',
                'label_size': '4x6',
                'print_custom_2': rq.customer_reference,
                'print_custom_1_code': 'PO'
            }
            total_weight = 0
            total_packages = 0
            for i in packages:
                total_packages = total_packages + 1
                total_weight = total_weight + i[1]
                shipments.append({"parcel": {"weight": i[1] * 16}, "options": options})  # 16 oz per pound

            discounts = build_discount_table(rq.user)

            warehouse = easypost.Address.create(company="PriorityBiz", street1='247 Cayuga Rd', city='Buffalo',
                                                state='NY', zip='14225', phone='18663426733', country='US')
            to_address = easypost.Address.create(company=rq.recipient.name, street1=rq.recipient.street1,
                                                 street2=rq.recipient.street2, city=rq.recipient.city,
                                                 state=rq.recipient.state, zip=rq.recipient.postal,
                                                 phone=rq.recipient.phone, country=rq.recipient.country)
            ship = None
            try:
                ship = easypost.Order.create(to_address=to_address, from_address=warehouse, shipments=shipments,
                                             options=options, reference=rq.customer_reference)
            except:
                message = "Unexpected error: %s %s" % (sys.exc_info()[0], sys.exc_info()[1])
            if ship:
                rates = sorted(ship.rates, key=lambda k: float(k['rate']))
                carrier_error_messages = ship.messages
            else:
                rates = []
                carrier_error_messages = []
            if len(shipments) == 0:
                message = "Order is empty (there may be line items but they have no quantity) " + message
            return render_template('order-shipmethod.html', rates=rates, order=rq, total_weight=total_weight,
                                   total_packages=total_packages, insurance_cost=insurance_cost, discounts=discounts,
                                   menu='order', message=message, carrier_error_messages=carrier_error_messages,
                                   menutab='add-update')
        elif 'action' in request.values and request.values['action'] == 'pick_rate':
            rq.status = 1

            options = {
                'print_custom_1': "PB/%s" % rq.user.username,
                'delivered_duty_paid': 'false',
                'label_size': '4x6',
                'print_custom_2': rq.customer_reference,
                'print_custom_1_code': 'PO'
            }

            packages = split_packages(rq)
            total_weight = 0
            total_packages = 0
            for i in packages:
                total_packages = total_packages + 1
                total_weight = total_weight + i[1]


            if 'requested_carrier' in request.values and 'requested_service' in request.values:
                rq.requested_carrier = request.values['requested_carrier']
                rq.requested_service = request.values['requested_service']
            else:
                rq.requested_carrier = request.values['carrier_service'].split(',')[0]
                rq.requested_service = request.values['carrier_service'].split(',')[1]

            if rq.signature_option:
                if rq.signature_option == 'DIRECT_SIGNATURE':
                    options['delivery_confirmation'] = 'SIGNATURE'
                elif rq.signature_option == 'ADULT_SIGNATURE':
                    options['delivery_confirmation'] = 'ADULT_SIGNATURE'
            insurance_cost = 0
            if rq.insurance_value:
                insurance_cost = float(rq.insurance_value) * 0.01
                if insurance_cost < 1:
                    insurance_cost = 1
            db.session.commit()
            return render_template("order-created.html", order=rq, insurance_cost=insurance_cost,
                                   total_weight=total_weight,total_packages=total_packages,
                                   menu='order', menutab='add-update')
        elif 'action' in request.values and request.values['action'] == 'ship':
            # TODO: Restrict this to warehouse staff/admins
            message = ""
            if 'box_info' in request.values:
                packages = json.loads(request.values['box_info'])
            else:
                packages = split_packages(rq)
            shipments = []

            if rq.easypost_order_id:
                batch = False
                try:
                    ship = easypost.Order.retrieve(rq.easypost_order_id)
                    if ship.shipments[0].selected_rate:
                        message = "Shipping already purchased. Displaying original labels."
                        if ship.shipments[0].batch_id:
                            batch = easypost.Batch.retrieve(ship.shipments[0].batch_id)
                except:
                    message = 'Failed at reprinting labels. Shipping has already been purchased for this order. If you need to reprint labels, do this through Easypost.'
                    message = message + " Unexpected error: %s %s" % (sys.exc_info()[0], sys.exc_info()[1])
                return render_template('print-labels.html', shipment=ship, batch=batch, message=message, menu='order',
                                       menutab='add-update')

            insurance_cost = 0
            options = {
                'print_custom_1': "PB/%s" % rq.user.username,
                'delivered_duty_paid': 'false',
                'label_size': '4x6',
                'print_custom_2': rq.customer_reference,
                'print_custom_1_code': 'PO'
            }

            if rq.requested_service and rq.requested_carrier:
                if rq.requested_carrier.upper() == 'FEDEX':
                    if rq.requested_service == 'FEDEX_EXPRESS_SAVER':
                        options['bill_third_party_account'] = '308754227'
                        options['bill_third_party_country'] = 'US'
                    elif rq.requested_service == 'FEDEX_GROUND' or 'ground' in rq.requested_service.lower():  # Sometimes they don't specify correctly
                        payment = {
                            "type" : 'SENDER',
                            "account" : 291480179,
                            "country": "US"
                        }
                        options['payment'] = payment
                    elif rq.user.username == 'Buffalofoodproducts.com':  # TODO: Check this is satisfactory?
                        options['bill_third_party_account'] = '210128980'
                        options['bill_third_party_country'] = 'US'
                    # Below options are Added on 09-02-2021
                    elif rq.requested_service in ["FedExMediumBox" , "FedExSmallBox", "FedExPak", "FedExEnvelope"]:
                        payment = {
                            "type" : 'SENDER',
                            "account" : 242823303,
                            "country": "US"
                        }
                        options['payment'] = payment
                    # Above options are Added on 09-02-2021
                    else:
                        options['bill_third_party_account'] = '210128980'
                        options['bill_third_party_country'] = 'US'

            if rq.signature_option:
                if rq.signature_option == 'DIRECT_SIGNATURE':
                    options['delivery_confirmation'] = 'SIGNATURE'
                elif rq.signature_option == 'ADULT_SIGNATURE':
                    options['delivery_confirmation'] = 'ADULT_SIGNATURE'
            if rq.insurance_value:
                insurance_cost = float(rq.insurance_value) * 0.01
                if insurance_cost < 1:
                    insurance_cost = 1
            total_weight = 0
            total_packages = 0
            shipments2 = shipments.copy()
            for i in packages:
                total_packages = total_packages + 1
                total_weight = total_weight + i[1]
                if rq.requested_service in ["FedExMediumBox" , "FedExSmallBox", "FedExPak", "FedExEnvelope"]:
                    shipments2.append({"parcel": {"weight": i[1] * 16, "predefined_package": rq.requested_service, }, "options": options})  # 16 oz per pound
                shipments.append({"parcel": {"weight": i[1] * 16 }, "options": options})  # 16 oz per pound

            warehouse = easypost.Address.create(company=rq.blind_company or rq.user.company or "PriorityBiz",
                                                street1='247 Cayuga Rd', city='Buffalo', state='NY', zip='14225-1911',
                                                phone=rq.blind_phone or rq.user.phone or "18663426733", country='US')
            to_address = easypost.Address.create(company="%s %s" % (rq.recipient.contact, rq.recipient.name),
                                                 street1=rq.recipient.street1, street2=rq.recipient.street2,
                                                 city=rq.recipient.city, state=rq.recipient.state,
                                                 zip=rq.recipient.postal, phone=rq.recipient.phone,
                                                 country=rq.recipient.country)
            ship = None
            ship2 = None
            try:
                if rq.requested_service in ["FedExMediumBox" , "FedExSmallBox", "FedExPak", "FedExEnvelope"]:
                    ship2 = easypost.Order.create(to_address=to_address, from_address=warehouse, shipments=shipments2, reference=rq.customer_reference)
                ship = easypost.Order.create(to_address=to_address, from_address=warehouse, shipments=shipments, reference=rq.customer_reference)
            except:
                message = "Unexpected error: %s %s" % (sys.exc_info()[0], sys.exc_info()[1])
            if ship:
                rates = []
                rates += ship.rates
                for rate in rates:
                    rate["custom_shipment_id"] = ship.id
                rates = sorted(rates, key=lambda k: float(k['rate']))
                if rq.requested_service in ["FedExMediumBox" , "FedExSmallBox", "FedExPak", "FedExEnvelope"]:
                    filteredRate = []
                    for rate in ship2.rates:
                        if rate["service"] == "FEDEX_2_DAY":
                            rate["custom_shipment_id"] = ship2.id
                            rate["custom_predefined_package"] = True
                            filteredRate.append(rate)
                    rates += filteredRate
                ship_id = ship.id
                carrier_error_messages = ship.messages
            else:
                rates = []
                ship_id = "NONE"
                carrier_error_messages = []
            if len(shipments) == 0:
                message = "Order is empty (there may be line items but they have no quantity) " + message
            return render_template('order-ship.html', rates=rates, shipment_id=ship_id, order=rq,
                                   insurance_cost=insurance_cost, message=message,
                                   carrier_error_messages=carrier_error_messages, options=options, easypost_order=ship,
                                   packages=packages, menu='order', menutab='add-update')
        elif 'action' in request.values and request.values['action'] == 'do_ship':
            message = ""
            rq.status = 2
            rq.actual_carrier = request.values['actual_carrier']
            rq.actual_service = request.values['actual_service']
            rq.shipped = datetime.now()
            manual = True
            ship = None
            batch = None
            if 'rate_id' in request.values:
                # They picked an Easypost rate (vs. manually doing things on their own)
                manual = False

                # Allow reprinting of labels
                if rq.easypost_order_id:
                    try:
                        ship = easypost.Order.retrieve(rq.easypost_order_id)
                        if ship.shipments[0].selected_rate:
                            message = "Shipping already purchased. Displaying original labels."
                            if ship.shipments[0].batch_id:
                                batch = easypost.Batch.retrieve(ship.shipments[0].batch_id)
                    except:
                        message = message + " Unexpected error: %s %s" % (sys.exc_info()[0], sys.exc_info()[1])

                if not message:
                    try:
                        old_ship = easypost.Order.retrieve(request.values['shipment_id'])
                        # TODO: Create new order based on previous data but with selected rate.
                        options = {
                            'print_custom_1': "PB/%s" % rq.user.username,
                            'delivered_duty_paid': 'false',
                            'label_size': '4x6',
                            'print_custom_2': rq.customer_reference,
                            'print_custom_1_code': 'PO'
                        }
                        if rq.actual_service and rq.actual_carrier:
                            if rq.actual_carrier.upper() == 'FEDEX':
                                if rq.actual_service == 'FEDEX_EXPRESS_SAVER':
                                    options['bill_third_party_account'] = '308754227'
                                    options['bill_third_party_country'] = 'US'
                                elif rq.actual_service == 'FEDEX_GROUND' or 'ground' in rq.actual_service.lower():  # Sometimes they don't specify correctly
                                    payment = {
                                        "type" : 'SENDER',
                                        "account" : 291480179,
                                        "country": "US"
                                    }
                                    options['payment'] = payment
                                elif rq.user.username == 'Buffalofoodproducts.com':  # TODO: Check this is satisfactory?
                                    options['bill_third_party_account'] = '210128980'
                                    options['bill_third_party_country'] = 'US'
                                # Below options are Added on 09-02-2021
                                elif rq.requested_service in ["FedExMediumBox" , "FedExSmallBox", "FedExPak", "FedExEnvelope"]:
                                    payment = {
                                        "type" : 'SENDER',
                                        "account" : 242823303,
                                        "country": "US"
                                    }
                                    options['payment'] = payment
                                # Above options are Added on 09-02-2021
                                else:
                                    options['bill_third_party_account'] = '210128980'
                                    options['bill_third_party_country'] = 'US'

                        if rq.signature_option:
                            if rq.signature_option == 'DIRECT_SIGNATURE':
                                options['delivery_confirmation'] = 'SIGNATURE'
                            elif rq.signature_option == 'ADULT_SIGNATURE':
                                options['delivery_confirmation'] = 'ADULT_SIGNATURE'

                        # Build shipment data from old shipment data (this is because Easypost doesn't allow changing options like customs data or 3rd party billing)
                        # ...so, as a result we need to re-create the shipment.
                        international = False
                        customs_forms = []
                        if 'box_info' in request.values:
                            packages = json.loads(request.values['box_info'])
                            for i in packages:
                                # TODO: make this work properly (right now the UI allows additional items but they aren't passed to the label)
                                if len(i) > 3:
                                    international = True
                                    citems = []
                                    for ci in range(2, len(i), 2):
                                        citems.append(
                                            easypost.CustomsItem.create(description=i[ci], quantity=1, value=i[ci + 1],
                                                                        weight=i[1] / (len(i) - 2) / 2,
                                                                        origin_country='US'))
                                    customs_forms.append(
                                        easypost.CustomsInfo.create(eel_pfc='NOEEI 30.37(a)', customs_certify=True,
                                                                    customs_signer='Ray', contents_type='merchandise',
                                                                    customs_items=citems))
                        new_shipments = []
                        indx = 0
                        for i in old_ship.shipments:
                            if international:
                                new_shipments.append({"parcel": i.parcel, "options": options, "customs_info": customs_forms[indx]})
                            else:
                                new_shipments.append({"parcel": i.parcel, "options": options})  # 16 oz per pound
                            indx = indx + 1

                        ship = None
                        try:
                            ship = easypost.Order.create(to_address=old_ship.to_address,
                                                         from_address=old_ship.from_address, shipments=new_shipments,
                                                         reference=rq.customer_reference)
                        except:
                            message = "Unexpected error: %s %s" % (sys.exc_info()[0], sys.exc_info()[1])

                        rq.easypost_order_id = ship.id
                        ship.buy(carrier=request.values['actual_carrier'], service=request.values['actual_service'])
                        rq.shipping_cost = ship.shipments[0].selected_rate.rate
                        shipments = []
                        for s in ship.shipments:
                            s.label(file_format='zpl')
                            s.label(file_format='pdf')
                            shipments.append({"id": s.id})
                        if len(ship.shipments) > 1:
                            batch = easypost.Batch.create(shipments=shipments)
                            batch.label(file_format='zpl')
                        # TODO: Handle and buy insurance
                        rq.tracking = ship.shipments[0].tracking_code
                    except:
                        if message:
                            message = message + "\n Unexpected error: %s %s" % (sys.exc_info()[0], sys.exc_info()[1])
                        else:
                            message = "Unexpected error: %s %s" % (sys.exc_info()[0], sys.exc_info()[1])
            else:
                rq.tracking = request.values['tracking']
            db.session.commit()

            # TODO: Make this not fire again on repeats/reloads
            try:
                if rq.notify_recipient:
                    msg = Message("Your %s Order %s will be shipped today" % (rq.blind_company or rq.user.company or "", rq.customer_reference or rq.id), recipients=[rq.recipient.email],
                                  sender="%s <no-reply@prioritybiz.com>" % (rq.blind_company or rq.user.company or ""))
                    msg.body = render_template('email/shipped.txt', order=rq, shipment=ship)
                    mail.send(msg)
            except:
                message = message + ". Sending recipient email failed. %s %s" % (sys.exc_info()[0], sys.exc_info()[1])

            # TODO: Make this not fire again on repeats/reloads
            try:
                if rq.additionally_notify:
                    msg = Message("Your %s Order %s will be shipped today" % (rq.blind_company or rq.user.company or "", rq.customer_reference or rq.id), recipients=[rq.additionally_notify],
                                  sender="%s <no-reply@prioritybiz.com>" % (rq.blind_company or rq.user.company or ""))
                    msg.body = render_template('email/shipped.txt', order=rq, shipment=ship)
                    mail.send(msg)
            except:
                message = message + ". Sending notify additionally email failed. %s %s" % (
                    sys.exc_info()[0], sys.exc_info()[1])
            
            return render_template('print-labels.html', shipment=ship, batch=batch, order=rq, message=message,
                                   manual=manual, menu='order', menutab='add-update')

        inventory = Inventory.query.filter_by(user_id=get_user_id()).all()
        return render_template('order-form.html', inventory=inventory, order=rq, menu='order', menutab='add-update')
    else:
        if r:
            return form_crud_user_id(None, get_user_id(), Order, OrderForm, menu='order', menutab='add-update', rid=r.id)
        else:
            return form_crud_user_id(None, get_user_id(), Order, OrderForm, menu='order', menutab='add-update')


@current_app.route('/files/<file_id>')
@login_required
def get_file(file_id):
    u = Upload.query.get(file_id)
    if int(u.user_id) != int(get_user_id()):
        return "Forbidden"
    else:
        return send_file(u.filename, as_attachment=True, attachment_filename=os.path.basename(u.filename))


@current_app.route('/labels/<batch_id>')
@login_required
def get_batch_label(batch_id):
    try:
        batch = easypost.Batch.retrieve(batch_id)
        return redirect(batch.label_url)
    except:
        return "Not ready yet"


@current_app.route('/order/history', methods=['GET'])
@login_required
def order_history():
    filters = {}
    uploads = Upload.query.filter_by(user_id=get_user_id(), kind='order').order_by(Upload.created.desc())

    # Allow filtering results
    if 'date-range-start' in request.values and request.values['date-range-start']:
        start_time = request.values['date-range-start']
        filters['date-range-start'] = start_time
    else:
        start_time = datetime.now() - timedelta(days=30)
        filters['date-range-start'] = start_time.strftime("%Y-%m-%d")
    uploads = uploads.filter(Upload.created > start_time)

    if 'date-range-end' in request.values and request.values['date-range-end']:
        end_time = request.values['date-range-end']
        uploads = uploads.filter(Upload.created < end_time)
        filters['date-range-end'] = end_time

    for u in uploads:
        u.filename = os.path.basename(u.filename)
    return render_template('history.html', uploads=uploads, menu='order', menutab='history', filters=filters)


@current_app.route('/recipient/history', methods=['GET'])
@login_required
def recipient_history():
    filters = {}
    uploads = Upload.query.filter_by(user_id=get_user_id(), kind='recipient').order_by(Upload.created.desc())

    # Allow filtering results
    if 'date-range-start' in request.values and request.values['date-range-start']:
        start_time = request.values['date-range-start']
        filters['date-range-start'] = start_time
    else:
        start_time = datetime.now() - timedelta(days=365)
        filters['date-range-start'] = start_time.strftime("%Y-%m-%d")
    uploads = uploads.filter(Upload.created > start_time)

    if 'date-range-end' in request.values and request.values['date-range-end']:
        end_time = request.values['date-range-end']
        uploads = uploads.filter(Upload.created < end_time)
        filters['date-range-end'] = end_time

    for u in uploads:
        u.filename = os.path.basename(u.filename)
    return render_template('history.html', uploads=uploads, menu='recipient', menutab='history', filters=filters)


@current_app.route('/inventory/history', methods=['GET'])
@login_required
def inventory_history():
    filters = {}
    uploads = Upload.query.filter_by(user_id=get_user_id(), kind='inventory').order_by(Upload.created.desc())

    # Allow filtering results
    if 'date-range-start' in request.values and request.values['date-range-start']:
        start_time = request.values['date-range-start']
        filters['date-range-start'] = start_time
    else:
        start_time = datetime.now() - timedelta(days=365)
        filters['date-range-start'] = start_time.strftime("%Y-%m-%d")
    uploads = uploads.filter(Upload.created > start_time)

    if 'date-range-end' in request.values and request.values['date-range-end']:
        end_time = request.values['date-range-end']
        uploads = uploads.filter(Upload.created < end_time)
        filters['date-range-end'] = end_time

    for u in uploads:
        u.filename = os.path.basename(u.filename)
    return render_template('history.html', uploads=uploads, menu='inventory', menutab='history', filters=filters)


@current_app.route('/recipient/json/<recipient_id>')
@login_required
def recipient_json(recipient_id):
    if current_user.has_roles('superadmin') or current_user.has_roles('warehouse'):
        r = Recipient.query.filter_by(id=recipient_id).first()
    else:
        r = Recipient.query.filter_by(user_id=get_user_id(), id=recipient_id).first()

    if not r:
        return json.dumps({})
    else:
        return json.dumps(
            {'id': r.id, 'name': r.name, 'contact': r.contact, 'phone': r.phone, 'email': r.email, 'street1': r.street1,
             'street2': r.street2, 'city': r.city, 'state': r.state, 'postal': r.postal, 'country': r.country})


@current_app.route('/recipient/search')
@current_app.route('/recipient/search/')
@login_required
def recipient_search():
    q = request.args.get('q')
    search = "%{}%".format(q)
    if current_user.has_roles('superadmin') or current_user.has_roles('warehouse'):
        r = Recipient.query
    else:
        r = Recipient.query.filter_by(user_id=get_user_id())

    if not q:
        r = r.limit(25).all()
    else:
        r = r.filter(Recipient.name.like(search) | Recipient.contact.like(search)).limit(25).all()

    if not r:
        return json.dumps({})
    else:
        return json.dumps({'results': [row.as_search_dict() for row in r]})


@current_app.route('/user/add-update', methods=['GET', 'POST'])
@login_required
def user_form():
    if not current_user.has_roles('superadmin'):
        errors = ["You are not a superadmin. You cannot create/edit users"]
        return render_template("errors.html", errors=errors, menu='user', menutab='add-update')

    if 'id' in request.values:
        return form_crud_user_id(request.values['id'], get_user_id(), User, UserForm, menu='user', menutab='add-update')
    else:
        return form_crud_user_id(None, get_user_id(), User, UserForm, menu='user', menutab='add-update')


@current_app.route('/user/discounts', methods=['GET', 'POST'])
@login_required
def user_discounts():
    errors = []
    if not current_user.has_roles('superadmin'):
        errors = ["You are not a superadmin. You cannot create/edit user discounts"]
        return render_template("errors.html", errors=errors, menu='user', menutab='add-update')

    if 'id' in request.values:
        u = User.query.filter_by(id=request.values['id']).first()
        if not u:
            errors = ["Could not find that user"]
    else:
        errors = ["No user specified"]

    if errors:
        return render_template("errors.html", errors=errors, menu='user', menutab='add-update')

    if 'carrier' in request.values:
        dis = Discount.query.filter_by(user_id=request.values['id'], carrier=request.values['carrier'],
                                       service=request.values['service']).first()
        if dis:
            # Update it
            dis.discount = request.values['discount']
        else:
            # Create it
            dis = Discount()
            dis.carrier = request.values['carrier']
            dis.service = request.values['service']
            dis.discount = request.values['discount']
            u.shipping_discounts.append(dis)
            db.session.add(dis)
        db.session.commit()

    return render_template('discounts.html', user=u, carrier_services=carrier_services)


@current_app.route('/sudo', methods=['GET', 'POST'])
@login_required
def sudo_page():
    if current_user.has_roles('superadmin') or current_user.has_roles('warehouse'):
        return sudo_form()
    else:
        return 'Unauthorized'


@current_app.route('/order/packing-slip')
@login_required
def packing_slip():
    if 'id' in request.values:
        if current_user.has_roles('warehouse') or current_user.has_roles('superadmin'):
            o = Order.query.filter_by(id=request.values['id']).first()
        else:
            o = Order.query.filter_by(user_id=get_user_id(), id=request.values['id']).first()
        if not o:
            errors = ["Could not find a packing slip with that order ID or you don't have permission to see it."]
            return render_template('errors.html', errors=errors, menu='order', menutab='index')
        else:
            return render_template('packing-slip.html', order=o)
    else:
        errors = ["No order ID specified"]
        return render_template('errors.html', errors=errors, menu='order', menutab='index')


@current_app.route('/order/pick-ticket')
@login_required
def pick_ticket():
    if 'id' in request.values:
        if current_user.has_roles('warehouse') or current_user.has_roles('superadmin'):
            o = Order.query.filter_by(id=request.values['id']).first()
        else:
            o = Order.query.filter_by(user_id=get_user_id(), id=request.values['id']).first()
        if not o:
            errors = ["Could not find a pick ticket with that order ID or you don't have permission to see it."]
            return render_template('errors.html', errors=errors, menu='order', menutab='index')
        else:
            return render_template('pick-ticket.html', order=o)
    else:
        errors = ["No order ID specified"]
        return render_template('errors.html', errors=errors, menu='order', menutab='index')


@current_app.route('/inventory/import', methods=['GET', 'POST'])
@login_required
def inventory_import():
    if 'id' in request.values:
        file = request.files['name']
        filename = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        # Enforce filename uniqueness constraint
        if os.path.isfile(filename):
            errors = ['Filename must be unique (this filename has been used before)', ]
            return render_template("errors.html", errors=errors, menu='inventory', menutab='import')
        file.save(filename)

        u = Upload()
        u.user_id = get_user_id()
        u.filename = filename
        u.kind = 'inventory'
        db.session.add(u)
        db.session.commit()

        errors = parse_inventory_upload(filename, get_user_id())
        if not errors:
            return redirect('/inventory')
        else:
            return render_template("errors.html", errors=errors, menu='inventory', menutab='import')
    else:
        return form_crud_user_id(None, get_user_id(), Inventory, InventoryImportForm,
                                 message="This expects plain vanilla CSV files, not UTF-8 encoded CSV files, not Excel files.",
                                 menu='inventory', menutab='import')


@current_app.route('/recipient/import', methods=['GET', 'POST'])
@login_required
def recipient_import():
    if 'id' in request.values:
        file = request.files['name']
        filename = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        # Enforce filename uniqueness constraint
        if os.path.isfile(filename):
            errors = ['Filename must be unique (this filename has been used before)', ]
            return render_template("errors.html", errors=errors, menu='recipient', menutab='import')
        file.save(filename)

        u = Upload()
        u.user_id = get_user_id()
        u.filename = filename
        u.kind = 'recipient'
        db.session.add(u)
        db.session.commit()

        # TODO: Implement this
        #		errors = parse_recipient_upload(filename, get_user_id())
        errors = ['Recipient import is not supported yet.']
        if not errors:
            return redirect('/recipient')
        else:
            return render_template("errors.html", errors=errors, menu='recipient', menutab='import')
    else:
        return form_crud_user_id(None, get_user_id(), Recipient, RecipientImportForm,
                                 message="This expects plain vanilla CSV files, not UTF-8 encoded CSV files, not Excel files.",
                                 menu='recipient', menutab='import')


@current_app.route('/order/import', methods=['GET', 'POST'])
@login_required
def order_import():
    if 'id' in request.values:
        file = request.files['name']
        filename = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        # Enforce filename uniqueness constraint
        if os.path.isfile(filename):
            errors = ['Filename must be unique (this filename has been used before)', ]
            return render_template("errors.html", errors=errors, menu='order', menutab='import')
        file.save(filename)

        u = Upload()
        u.user_id = get_user_id()
        u.filename = filename
        u.kind = 'order'
        db.session.add(u)
        db.session.commit()

        orders_before_import = Order.query.filter_by(user_id=get_user_id()).all()
        errors = parse_order_upload(filename, u.user_id)
        orders_after_import = Order.query.filter_by(user_id=get_user_id()).all()
        orders_imported = []
        for o in orders_after_import:
            found = False
            for ob in orders_before_import:
                if ob.id == o.id:
                    found = True
            if not found:
                orders_imported.append(o)

        if not errors:
            return render_template("orders-imported.html", filename=os.path.basename(filename), orders=orders_imported,
                                   menu='order', menutab='import')
        else:
            return render_template("errors.html", errors=errors, menu='order', menutab='import')
    else:
        return form_crud_user_id(None, get_user_id(), Order, OrderImportForm,
                                 message="This expects plain vanilla CSV files, not UTF-8 encoded CSV files, not Excel files.",
                                 menu='order', menutab='import')


@current_app.route('/order/export')
@login_required
def order_export():
    if 'filter' in request.values:
        end_time = False
        f = request.values['filter']
        if f == '24 hours':
            start_time = datetime.now() - timedelta(hours=24)
        elif f == '7 days':
            start_time = datetime.now() - timedelta(days=7)
        elif f == '30 days':
            start_time = datetime.now() - timedelta(days=30)
        elif f == '60 days':
            start_time = datetime.now() - timedelta(days=60)
        elif f == 'range':
            start_time = request.values['range-start']
            end_time = request.values['range-end']
        else:  # mostly "all"
            start_time = 0

        if not end_time:
            orders = Order.query.filter(Order.user_id == get_user_id(), Order.shipped >= start_time).all()
        else:
            end_time = end_time + " 11:59:59"
            orders = Order.query.filter(Order.user_id == get_user_id(), Order.shipped >= start_time, Order.shipped <= end_time).all()
    else:
        orders = Order.query.filter_by(user_id=get_user_id()).all()

    output = make_response(render_template('order.csv', orders=orders))
    output.headers["Content-Disposition"] = "attachment; filename=order-export_%s.csv" % datetime.now().strftime(
        "%Y-%m-%d")
    output.headers["Content-type"] = "text/csv"
    return output


@current_app.route('/')
@login_required
def home_page():
    all_pending_orders = None
    low_stock = None
    filters = {}

    if current_user.has_roles('superadmin') or current_user.has_roles('warehouse'):
        orders = Order.query.filter(Order.status == 1).order_by('user_id').order_by('id')

        # Allow filtering results
        if 'date-range-start' in request.values and request.values['date-range-start']:
            start_time = request.values['date-range-start']
            filters['date-range-start'] = start_time
        else:
            start_time = datetime.now() - timedelta(days=30)
            filters['date-range-start'] = start_time.strftime("%Y-%m-%d")

        orders = orders.filter(Order.created > start_time)

        if 'date-range-end' in request.values and request.values['date-range-end']:
            end_time = request.values['date-range-end']
            orders = orders.filter(Order.created < end_time)
            filters['date-range-end'] = end_time

        all_pending_orders = orders.all()

    elif current_user.is_authenticated:
        all_pending_orders = Order.query.filter_by(status=1, user_id=current_user.id).all()
        low_stock = Inventory.query.filter(Inventory.reorder_quantity >= Inventory.qoh_case,
                                           Inventory.user_id == current_user.id).all()
    # ,Inventory.user_id=current_user.id
    return render_template("home.html", orders=all_pending_orders, inventory=low_stock, filters=filters)


# The Members page is only accessible to authenticated users
@current_app.route('/members')
@login_required
def members_page():
    return render_template('members.html')


@current_app.route('/recipient')
@login_required
def recipients_page():
    recipients = Recipient.query.filter_by(user_id=get_user_id()).all()
    return render_template('recipient.html', recipients=recipients, menu='recipient', menutab='index')


@current_app.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory_page():
    user_id = get_user_id()
    if 'id' in request.values and 'action' in request.values:
        if request.values['action'] == 'split':
            errors = []
            inv = Inventory.query.filter_by(user_id=user_id, id=request.values['id']).first()
            if not inv:
                errors.append("Cannot find inventory with that id or it doesn't belong to you. Can't split it.")
            elif inv.qoh_case <= 0:
                errors.append("Can't split something you don't have any cases of.")
            else:
                inv.qoh_case = inv.qoh_case - 1
                inv.qoh_units = inv.qoh_units + inv.case_quantity
                db.session.commit()
            if errors:
                return render_template("errors.html", errors=errors, menu='inventory', menutab='index')

    inventory = Inventory.query.filter_by(user_id=user_id).all()
    return render_template('inventory.html', inventory=inventory, menu='inventory', menutab='index')


@current_app.route('/order', methods=['GET', 'POST'])
@login_required
def order_page():
    user_id = get_user_id()
    filters = {}
    if 'id' in request.values and 'action' in request.values:
        if request.values['action'] == 'cancel' or request.values['action'] == 'restore':
            errors = []
            order = Order.query.filter_by(user_id=user_id, id=request.values['id']).first()
            if not order:
                errors.append("Cannot find an order with that id or it doesn't belong to you. Can't cancel/revive it.")
            else:
                if request.values['action'] == 'cancel':
                    order.status = 3  # Cancelled
                else:
                    order.status = 1  # Pending (restored)
                db.session.commit()
            if errors:
                return render_template("errors.html", errors=errors, menu='order', menutab='index')

    orders = Order.query.filter(Order.user_id == user_id).order_by(Order.id.desc())

    # Allow filtering results
    enable_date_filter = True

    if 'recipient' in request.values and request.values['recipient']:
        search = "%{}%".format(request.values['recipient'])
        orders = orders.filter((Order.recipient.has(Recipient.name.like(search))) | (Order.recipient.has(Recipient.contact.like(search))))
        filters['recipient'] = request.values['recipient']
        enable_date_filter = False

    if 'customer_reference' in request.values and request.values['customer_reference']:
        search = "%{}%".format(request.values['customer_reference'])
        orders = orders.filter(Order.customer_reference.like(search))
        filters['customer_reference'] = request.values['customer_reference']
        enable_date_filter = False

    if 'tracking' in request.values and request.values['tracking']:
        search = "%{}%".format(request.values['tracking'])
        orders = orders.filter(Order.tracking.like(search))
        filters['tracking'] = request.values['tracking']
        enable_date_filter = False

    if enable_date_filter:
        if 'date-range-start' in request.values and request.values['date-range-start']:
            start_time = request.values['date-range-start']
            filters['date-range-start'] = start_time
        else:
            start_time = datetime.now() - timedelta(days=30)
            filters['date-range-start'] = start_time.strftime("%Y-%m-%d")

        orders = orders.filter(Order.created > start_time)

        if 'date-range-end' in request.values and request.values['date-range-end']:
            end_time = request.values['date-range-end']
            filters['date-range-end'] = end_time
            end_time_obj = datetime.strptime(end_time, '%Y-%m-%d') + timedelta(days=1)
            orders = orders.filter(Order.created <= end_time_obj)
        else:
            end_time = datetime.now()
            filters['date-range-end'] = end_time.strftime("%Y-%m-%d")


    # page, per_page, offset = get_page_args()
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 25
    offset = (page-1) * per_page
    paginated_orders = orders.offset(offset).limit(per_page)

    pagination = Pagination(page=page, per_page=per_page, total=orders.count(), record_name='order', css_framework='bootstrap3')

    return render_template('order.html', orders=paginated_orders, menu='order', menutab='index', filters=filters, pagination=pagination)


@current_app.route('/user', methods=['GET', 'POST'])
@login_required
def user_page():
    status = 'Active'
    filters = {'status': status}

    if not current_user.has_roles('superadmin'):
        errors = ["You are not a superadmin. You cannot create/edit users"]
        return render_template("errors.html", errors=errors, menu='user', menutab='index')

    # Allow filtering results
    users = User.query

    if 'status' in request.values and request.values['status']:
        status = request.values['status']
        filters['status'] = status
    print(status)
    if status.lower() == "inactive":
        users = users.filter(User.is_enabled == False)
    if status.lower() == "active":
        users = users.filter(User.is_enabled == True)

    # users = users.all()
    return render_template('user.html', users=users, menu='user', menutab='index', filters=filters)


# Make a test label
@current_app.route('/test-label')
@login_required
def easypost_test_label():
    fromAddress = easypost.Address.create(
        company='EasyPost',
        street1='417 Montgomery Street',
        street2='5th Floor',
        city='San Francisco',
        state='CA',
        zip='94104',
        phone='415-528-7555'
    )

    toAddress = easypost.Address.create(
        name='George Costanza',
        company='Vandelay Industries',
        street1='1 E 161st St.',
        city='Bronx',
        state='NY',
        zip='10451'
    )
    parcel = easypost.Parcel.create(
        length=9,
        width=6,
        height=2,
        weight=10
    )

    reference = random.randint(0, 10000000)
    reference = "PB" + str(reference)

    shipment = easypost.Shipment.create(
        to_address=toAddress,
        from_address=fromAddress,
        parcel=parcel,
        reference=reference
    )
    shipment.buy(rate=shipment.lowest_rate())
    #
    #
    # options = {
    #     'print_custom_1': "PB/%s" % "Test User",
    #     'delivered_duty_paid': 'false',
    #     'label_size': '4x6',
    #     'print_custom_2': "PB/%s" % reference,
    #     'print_custom_1_code': 'PO'
    # }

    # options['bill_third_party_account'] = '308754227'
    # options['bill_third_party_country'] = 'US'
    # options['delivery_confirmation'] = 'SIGNATURE'



    # ship = None
    # try:
    # ship = easypost.Order.create(to_address=toAddress, from_address=fromAddress, shipments=[shipment],
    #                              options=options, reference=reference)
    # # ship.buy(rate=shipment.lowest_rate())
    # shipment.buy(rate=shipment.lowest_rate())

    # except:
    #     message = "Unexpected error: %s %s" % (sys.exc_info()[0], sys.exc_info()[1])

    # ship.buy(rate=shipment.lowest_rate())

    # return render_template('test-label.html', label=ship.shipment.postage_label.label_url,
    #                        tracking_code=ship.shipment.tracking_code)

    return render_template('test-label.html', label=shipment.postage_label.label_url,
                           tracking_code=shipment.tracking_code)


@current_app.errorhandler(500)
def server_error(e):
    return "Server error. Try again or contact support.", 500

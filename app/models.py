from flask import redirect, url_for, request, abort
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from flask_user import UserMixin
from flask_user import current_user
from sqlalchemy.sql import func

db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    # User Authentication information
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, default='')

    # User Email information
    email = db.Column(db.String(255), nullable=False, unique=True)
    confirmed_at = db.Column(db.DateTime())

    # User information
    is_enabled = db.Column(db.Boolean(), nullable=False, default=False)
    send_tracking_emails_by_default = db.Column(db.Boolean(), nullable=False, default=True)
    first_name = db.Column(db.String(50), nullable=False, default='')
    last_name = db.Column(db.String(50), nullable=False, default='')
    company = db.Column(db.String(255), nullable=False, default='Company')
    phone = db.Column(db.String(25), nullable=False, default='')
    roles = db.relationship('Role', secondary='user_roles',
                            backref=db.backref('users', lazy='dynamic'))
    shipping_discounts = db.relationship('Discount',
                                         backref='users', lazy='dynamic')

    def is_active(self):
        if self.is_enabled:
            return "Active"
        else:
            return "Inactive"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# Define the Role DataModel
class Role(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)


class UserRoles(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE'))


# Shipping discounts off carrier list rates.
class Discount(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'), index=True)
    carrier = db.Column(db.String(50), nullable=False, default='FedEx')  # These match EasyPost for case, values, etc.
    service = db.Column(db.String(50), nullable=False,
                        default='FEDEX_GROUND')  # These match EasyPost for case, values, etc.
    discount = db.Column(db.Numeric, nullable=False, default=0)  # May be negative for a markup


class Recipient(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(),
                        db.ForeignKey('user.id', ondelete='CASCADE'))  # Contacts are associated with users
    name = db.Column(db.String(50), nullable=False, default='')
    contact = db.Column(db.String(50), nullable=False, default='')
    phone = db.Column(db.String(50), nullable=False, default='')
    email = db.Column(db.String(50), nullable=False, default='')
    street1 = db.Column(db.String(50), nullable=False, default='')
    street2 = db.Column(db.String(50), nullable=False, default='')
    city = db.Column(db.String(50), nullable=False, default='')
    state = db.Column(db.String(50), nullable=False, default='')
    postal = db.Column(db.String(50), nullable=False, default='')
    country = db.Column(db.String(50), nullable=False, default='US')

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def as_text(self):
        return self.name + " - " +  self.contact + " - " + self.street1

    def as_search_dict(self):
        return {'id': self.id, 'text': self.as_text()}


class Upload(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(),
                        db.ForeignKey('user.id', ondelete='CASCADE'))  # Contacts are associated with users
    filename = db.Column(db.String(255), nullable=False, default='')
    kind = db.Column(db.String(20), nullable=False, default='order')
    created = db.Column(db.DateTime, server_default=func.now())
    user = db.relationship('User')


class Order(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))  # Orders are associated with users
    recipient_id = db.Column(db.Integer(),
                             db.ForeignKey('recipient.id', ondelete='CASCADE'))  # Orders are associated with users
    created = db.Column(db.DateTime, server_default=func.now())
    last_modified = db.Column(db.DateTime, onupdate=func.now())
    blind_company = db.Column(db.String(255))
    blind_phone = db.Column(db.String(25))
    customer_reference = db.Column(db.String(255))
    shipped = db.Column(db.DateTime)
    status = db.Column(db.Integer, index=True)
    requested_carrier = db.Column(db.String(50))
    requested_service = db.Column(db.String(100))
    actual_carrier = db.Column(db.String(50))
    actual_service = db.Column(db.String(100))
    insurance_value = db.Column(db.Numeric, nullable=True, default=0)
    shipping_cost = db.Column(db.Numeric, nullable=False, default=0)
    customs_value = db.Column(db.Numeric, nullable=False, default=0)
    customs_description = db.Column(db.String(255), nullable=False, default="")
    notify_recipient = db.Column(db.Boolean, nullable=False, default=False)
    additionally_notify = db.Column(db.String(100), nullable=True)  # email address
    easypost_order_id = db.Column(db.String(50), nullable=True, default="")
    signature_option = db.Column(db.String(50), nullable=True)
    tracking = db.Column(db.String(50))
    line_items = db.relationship('OrderLineItem', backref='order', lazy='dynamic')
    recipient = db.relationship('Recipient')
    user = db.relationship('User')


# A line item on the order (these are for products, but not for shipping, a minor difference from StoneEdge)
class OrderLineItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity_cases = db.Column(db.Integer, default=0)
    quantity_units = db.Column(db.Integer, default=0)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), index=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), index=True)
    item = db.relationship('Inventory')


class Inventory(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(),
                        db.ForeignKey('user.id', ondelete='CASCADE'))  # Inventory is associated with users
    name = db.Column(db.String(255), nullable=False, default='')
    number = db.Column(db.String(255), nullable=False, default='')
    case_quantity = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.String(255), nullable=False, default='')
    qoh_case = db.Column(db.Integer, nullable=False, default=0)
    qoh_units = db.Column(db.Integer, nullable=False, default=0)
    case_weight = db.Column(db.Numeric, nullable=False, default=0)
    reorder_quantity = db.Column(db.Integer, nullable=False, default=0)
    length = db.Column(db.Numeric, nullable=False, default=0)
    width = db.Column(db.Numeric, nullable=False, default=0)
    height = db.Column(db.Numeric, nullable=False, default=0)
    ship_ready = db.Column(db.Boolean, nullable=False, default=True)


class MyModelView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False

    def is_accessible(self):
        if not current_user.is_authenticated or not current_user.is_enabled:
            return False

        if current_user.has_roles('superadmin'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('user.login', next=request.url))


class MyOrderModelView(MyModelView):
    inline_models = [OrderLineItem, ]

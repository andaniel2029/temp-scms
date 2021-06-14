from datetime import datetime

import wtforms.validators as validators
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField, IntegerField, DecimalField, BooleanField, FileField, \
    SelectField, DateTimeField, PasswordField
from wtforms.validators import InputRequired


class RecipientForm(FlaskForm):
    id = HiddenField(default=0)
    name = StringField('Recipient name (company)', validators=(validators.Optional(),))
    contact = StringField('Contact name', validators=(validators.Optional(),))
    phone = StringField('Phone number')
    email = StringField('Email', validators=(validators.Optional(),))
    street1 = StringField('Street 1', validators=[InputRequired()])
    street2 = StringField('Street 2', validators=(validators.Optional(),))
    city = StringField('City')
    state = StringField('State')
    postal = StringField('Zip or Postal Code')
    country = StringField('Country', default='US')
    go = SubmitField()


class InventoryForm(FlaskForm):
    id = HiddenField(default=0)
    name = StringField('Item Name')
    number = StringField('Item Number')
    case_quantity = IntegerField('Case Quantity')
    description = StringField('Unit Description')
    qoh_case = IntegerField('Quantity - Case', validators=(validators.Optional(),))
    qoh_units = IntegerField('Quantity - Units', validators=(validators.Optional(),))
    case_weight = DecimalField('Case Weight (pounds)')
    reorder_quantity = IntegerField('Re-order Quantity', validators=(validators.Optional(),))
    length = DecimalField('Length (inches)', validators=(validators.Optional(),))
    width = DecimalField('Width (inches)', validators=(validators.Optional(),))
    height = DecimalField('Height (inches)', validators=(validators.Optional(),))
    ship_ready = BooleanField('Ship Ready?', validators=(validators.Optional(),))
    go = SubmitField()


class LineItemForm(FlaskForm):
    name = StringField()


class OrderForm(FlaskForm):
    id = HiddenField(default=0)
    # customer_reference = StringField('Reference ID (PO# or Order#)', validators=(validators.Optional(),
    # )) blind_company = StringField('Blind shipping company (leave blank to use default)', validators=(
    # validators.Optional(),)) blind_phone = StringField('Blind shipping phone (leave blank to use default)',
    # validators=(validators.Optional(),))
    recipient = SelectField(u'Recipient', coerce=int)
    go = SubmitField()


class UserForm(FlaskForm):
    id = HiddenField(default=0)
    username = StringField('Username (must be unique)', validators=[InputRequired()])
    first_name = StringField('First name', validators=[InputRequired()])
    last_name = StringField('Last name', validators=[InputRequired()])
    company = StringField('Company Name (used on labels)', validators=[InputRequired()])
    phone = StringField('Phone Number (used on labels) (must be unique)', validators=[InputRequired()])
    email = StringField('Email (must be unique)', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    confirmed_at = DateTimeField('Confirmed At', format="%Y-%m-%dT%H:%M:%S", default=datetime.today)
    # is_enabled = BooleanField('Is Enabled?')
    # is_enabled = SelectField('Status',
    #                 choices=[(False, 'Inactive'), (True, 'Active')],
    #                 validators=[InputRequired()],
    #                 coerce=lambda x: x == 'True'
    #             )
    is_enabled = BooleanField('Is Active?')
    send_tracking_emails_by_default = BooleanField('Send tracking emails to customers by default')
    go = SubmitField("Submit")


class InventoryImportForm(FlaskForm):
    id = HiddenField(default=0)
    name = FileField(u'Inventory File (csv)', [validators.regexp(u'^\.*\.csv$')])
    go = SubmitField()


class RecipientImportForm(FlaskForm):
    id = HiddenField(default=0)
    name = FileField(u'Recipients File (csv)', [validators.regexp(u'^\.*\.csv$')])
    go = SubmitField()


class OrderImportForm(FlaskForm):
    id = HiddenField(default=0)
    name = FileField(u'Orders File (csv)', [validators.regexp(u'^\.*\.csv$')])
    go = SubmitField()


class SudoForm(FlaskForm):
    id = HiddenField(default=0)
    sudo = SelectField(u'Perform Operation as...', validators=[InputRequired()])
    go = SubmitField()

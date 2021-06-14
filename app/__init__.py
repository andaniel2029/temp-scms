import easypost
import flask_login as login
from flask import Flask
from flask_admin import Admin
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_migrate import Migrate
from flask_user import UserManager, SQLAlchemyAdapter
from flask_wtf.csrf import CSRFProtect

from app.models import *
from app.utils import sudo, CustomJSONEncoder
from config import Config

bootstrap = Bootstrap()
mail = Mail()
csrf_protect = CSRFProtect()
db_adapter = SQLAlchemyAdapter(db, User)  # Register the User model
user_manager = UserManager(db_adapter)  # Initialize Flask-User
migrate = Migrate(db)



def create_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    app.jinja_env.globals.update(sudo=sudo)

    from app.models import db
    db.init_app(app)

    bootstrap.init_app(app)
    csrf_protect.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    user_manager.init_app(app)

    easypost.api_key = Config.EASYPOST_API_KEY  # Test API key (PriorityBiz)

    app.json_encoder = CustomJSONEncoder

    with app.app_context():
        # Include our Routes
        from app import views

        # Register Blueprints
        # app.register_blueprint(auth.auth_bp)

        admin = Admin(app, name="PriorityBiz", template_mode="bootstrap3")

        admin.add_view(MyModelView(User, db.session))
        admin.add_view(MyModelView(Recipient, db.session))
        admin.add_view(MyModelView(Inventory, db.session))
        admin.add_view(MyOrderModelView(Order, db.session))
        admin.add_view(MyModelView(OrderLineItem, db.session))

        def init_login():
            login_manager = login.LoginManager()
            login_manager.init_app(app)

            # Create user loader function
            @login_manager.user_loader
            def load_user(user_id):
                return db.session.query(User).get(user_id)

        init_login()

        if not app.debug:
            import logging
            from logging import FileHandler

            file_handler = FileHandler('errors.txt')
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

        return app

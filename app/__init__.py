from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFError, CSRFProtect
from config import Config

db = SQLAlchemy()

migrate = Migrate()

socketio = SocketIO()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")
    csrf.init_app(app)
    limiter.init_app(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return f"CSRF validation failed: {error.description}", 400
    
    from app.models import allocation, complaint, event, review, surplus, user

    # Register Blueprints
    from app.routes.auth_routes import auth
    app.register_blueprint(auth)

    from app.routes.provider_routes import provider
    app.register_blueprint(provider)

    from app.routes.ngo_routes import ngo
    app.register_blueprint(ngo)

    from app.routes.admin_routes import admin
    app.register_blueprint(admin)

    from app.routes.common_routes import common
    app.register_blueprint(common)

    return app
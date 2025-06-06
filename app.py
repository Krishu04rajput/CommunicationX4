import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from urllib.parse import urlparse

# Configure logging with reduced verbosity for performance
logging.basicConfig(
    level=logging.WARNING,  # Reduced from INFO to WARNING
    format='%(levelname)s - %(message)s'  # Simplified format
)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Security configurations
app.config['WTF_CSRF_ENABLED'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Configure the database with fallback
database_url = os.environ.get("DATABASE_URL")
if database_url:
    try:
        # Test the connection first
        import psycopg2
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password
        ).close()
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        logging.info("Successfully connected to PostgreSQL database")
    except Exception as e:
        logging.warning(f"Failed to connect to PostgreSQL: {e}")
        logging.info("Falling back to SQLite database")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///communicationx.db"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///communicationx.db"
    logging.info("Using SQLite database (no DATABASE_URL found)")

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_reset_on_return": "commit"
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Simplified rate limiting for better performance
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]  # Simplified single limit
)

# Initialize extensions
db.init_app(app)
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='threading',
                   logger=False, 
                   engineio_logger=False,
                   ping_timeout=60,
                   ping_interval=25)

# Lazy initialization - only create tables when needed
def init_database():
    """Initialize database tables only when first needed"""
    with app.app_context():
        import models  # noqa: F401
        db.create_all()
        logging.info("Database tables created on demand")

# Import models but don't create tables immediately
import models  # noqa: F401

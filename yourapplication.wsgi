import sys
sys.path.append('/var/www/')
from app import create_app
application = create_app()

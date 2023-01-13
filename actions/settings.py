import os

# LOGGING
SERVICE_NAME = os.getenv('SERVICE_NAME', 'harp-actions')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
LOKI_SERVER = os.getenv('LOKI_SERVER', 'loki-dev.harpia.io')
LOKI_PORT = os.getenv('LOKI_PORT', 80)
# Flask settings
FLASK_SERVER_PORT = os.getenv('FLASK_SERVER_PORT', 8081)
FLASK_SERVER_NAME = os.getenv('FLASK_SERVER_NAME', '0.0.0.0')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', True)
FLASK_THREADED = os.getenv('FLASK_THREADED', True)
URL_PREFIX = os.getenv('URL_PREFIX', '/harp-actions')
SERVICE_NAMESPACE = os.getenv('SERVICE_NAMESPACE', 'dev')
SCENARIOS_HOST = os.getenv('SCENARIOS_HOST', 'http://harp-scenarios:8081/harp-scenarios/api/v1/scenarios')

# DB settings
DBUSER = os.getenv('DBUSER', 'harpia')
DBPASS = os.getenv('DBPASS', 'harpia')
DBHOST = os.getenv('DBHOST', '127.0.0.1')
DBPORT = os.getenv('DBPORT', '3306')
DBSCHEMA = os.getenv('DBSCHEMA', 'harp_dev')

# SQLAlchemy settings
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://{0}:{1}@{2}:{3}/{4}'.format(DBUSER, DBPASS, DBHOST, DBPORT, DBSCHEMA)
SQLALCHEMY_TRACK_MODIFICATIONS = False
TOKEN_EXPIRE_HOURS = 148

ENVIRONMENTS_HOST = os.getenv('ENVIRONMENTS_HOST', 'dev.harpia.io/harp-environments')
BRIDGE_HOST = os.getenv('BRIDGE_HOST', 'dev.harpia.io/harp-bridge')
USERS_HOST = os.getenv('USERS_HOST', 'dev.harpia.io/harp-users')

AUTO_USERS = []

TIME_LIMIT_ALERTS_HISTORY_DAYS = 120


JIRA_SERVER = 'https://jira.com'
JIRA_USER = 'user'
JIRA_PASSWORD = 'password'
JIRA_TIMEOUT = 60
JIRA_WATCHERS = ['some_user']
JIRA_TODO_ISSUE_ID = '391'
JIRA_ONGOING_TASK_COMPONENT_ID = '25602'
JIRA_STUDIO_SUPPORT_COMPONENT_ID = '28401'
JIRA_EPIC = 'JIRA_EPIC'

# Auth
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'khFw8H5hP3gQ9kKS')
JWT_DECODE_ALGORITHMS = os.getenv('JWT_DECODE_ALGORITHMS', ['RS256'])
JWT_IDENTITY_CLAIM = os.getenv('JWT_IDENTITY_CLAIM', 'sub')
JWT_USER_CLAIMS = os.getenv('JWT_USER_CLAIMS', 'authorities')
PROPAGATE_EXCEPTIONS = os.getenv('PROPAGATE_EXCEPTIONS', True)

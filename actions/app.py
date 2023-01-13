import traceback
from actions.settings import FLASK_SERVER_NAME, FLASK_SERVER_PORT, FLASK_THREADED, URL_PREFIX, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, ENVIRONMENTS_HOST
from apscheduler.schedulers.background import BackgroundScheduler
from actions.api.restplus import api
import logging
from flask import Flask, Blueprint
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_flask_exporter import PrometheusMetrics
import requests
import actions.settings as settings
import logging_loki
from multiprocessing import Queue
from flask_restx.apidoc import apidoc

# Logging
harp_logger = logging.getLogger('default')
harp_logger.setLevel(settings.LOG_LEVEL)
log_format = logging.Formatter('[%(levelname)s] - %(message)s')

loki_handler = logging_loki.LokiQueueHandler(
    Queue(-1),
    url=f"http://{settings.LOKI_SERVER}:{settings.LOKI_PORT}/loki/api/v1/push",
    tags={"service": settings.SERVICE_NAME, "namespace": settings.SERVICE_NAMESPACE},
    version="1",
)
loki_handler.setFormatter(log_format)
console_handler = logging.StreamHandler()
harp_logger.addHandler(loki_handler)
harp_logger.addHandler(console_handler)
#

async_mode = None

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

metrics = PrometheusMetrics(app)

app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SQLALCHEMY_POOL_RECYCLE'] = 300
app.config['SECRET_KEY'] = 'secret!'

studios = requests.get(f'http://{ENVIRONMENTS_HOST}/api/v1/environments/all').json()
config = {'studios_dict': studios}


def update_studio_dict(old_config):
    try:
        studios_dict = requests.get(f'http://{ENVIRONMENTS_HOST}/api/v1/environments/all').json()
        if studios_dict:
            old_config['studios_dict'] = studios_dict
            harp_logger.info(f"Studios dictionary from Zergus updated with: {studios_dict}")
    except Exception as exc:
        harp_logger.error(f"Can't collect studios dictionary from Zergus. Error: {exc}\nTrace: {traceback.format_exc()}")
        if not studios:
            raise Exception("Can't collect studios dictionary from Zergus")


def register_namespaces():
    from actions.api.endpoints.home import ns as home
    from actions.api.endpoints.procedures import ns as procedures
    from actions.api.endpoints.actions import ns as actions
    from actions.api.endpoints.alerts import ns as alerts
    from actions.api.endpoints.history import ns as history
    from actions.api.endpoints.health import ns as health

    api.add_namespace(home)
    api.add_namespace(procedures)
    api.add_namespace(actions)
    api.add_namespace(alerts)
    api.add_namespace(history)
    api.add_namespace(health)


def configure_app():
    app.config['JWT_SECRET_KEY'] = settings.JWT_SECRET_KEY
    app.config['JWT_DECODE_ALGORITHMS'] = settings.JWT_DECODE_ALGORITHMS
    app.config['JWT_IDENTITY_CLAIM'] = settings.JWT_IDENTITY_CLAIM
    app.config['JWT_USER_CLAIMS'] = settings.JWT_USER_CLAIMS
    app.config['PROPAGATE_EXCEPTIONS'] = settings.PROPAGATE_EXCEPTIONS
    JWTManager(app)


def initialize_app():
    os.environ['TZ'] = 'UTC'
    update_studio_dict(config)
    configure_app()
    apidoc.url_prefix = settings.URL_PREFIX
    blueprint = Blueprint('api', __name__, url_prefix=URL_PREFIX)
    blueprint_main = Blueprint('main', __name__)
    api.init_app(blueprint)
    app.register_blueprint(blueprint)
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/metrics': make_wsgi_app()})
    register_namespaces()
    scheduler_jobs()


def scheduler_jobs():
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_studio_dict, 'interval', args=[config], seconds=60)
    scheduler.start()


def main():
    from actions.logic.db import db
    db.init_app(app)
    db.app = app
    db.create_all()
    initialize_app()
    app.run(port=FLASK_SERVER_PORT, host=FLASK_SERVER_NAME,  debug=False, threaded=FLASK_THREADED)
    harp_logger.info('>>>>> Starting development server at http://{0}:{1}{2}/ <<<<<'.format(FLASK_SERVER_NAME, FLASK_SERVER_PORT, URL_PREFIX))


if __name__ == '__main__':
    try:
        main()
    except Exception as err:
        logging.error(msg=f"{traceback.format_exc()}")

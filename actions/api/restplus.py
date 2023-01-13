import logging
import traceback

from flask_restx import Api
from actions.settings import FLASK_DEBUG

logger = logging.getLogger('default')

api = Api(version='1.0', title='Harp Actions REST API')


@api.errorhandler
def default_error_handler(e):
    logger.error(msg=f"An unhandled exception occurred: {e}. Traceback: {traceback.format_exc()}")

    if not FLASK_DEBUG:
        return {'message': traceback.format_exc()}, 500

import logging
from flask_restx import Resource, reqparse
from actions.api.restplus import api
from actions.logic.db import NotificationHistory, Notifications
from actions.logic.auth_decorator import token_required
from flask import request
import traceback


logger = logging.getLogger('default')
ns = api.namespace('api/v1/history', description='Bridge actions')


@ns.route('/')
class History(Resource):
    @token_required()
    def post(self):
        """
            Returns history with provided filters.
            ```
            {
                "environment_id": [],
                "notification_type": [],
                "pattern": "",
                "monitoring_system": "",
                "service": "",
                "source": "",
                "name": "",
                "object": "",
                "from": "",
                "to": "",
                "scenario_id": ""
            }
            ```
        """
        try:
            data = request.get_json()
            logger.info(msg=f"Received request to get history: {data}")
            if data['from'] == "":
                return {"msg": "'from' field can`t be empty"}, 500

            if data['to'] == "":
                return {"msg": "'to' field can`t be empty"}, 500

            object_ = Notifications.history(data)
            return object_, 200
        except Exception as err:
            logger.error(msg=f"Can`t collect alerts history. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t collect alerts history. Error - {err}"}, 500


@ns.route('/timeline')
class TimeLineHistory(Resource):
    @token_required()
    def post(self):
        """
            Returns history with provided filters.
        """
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('alert_ids', type=list, required=True, location='json', help='List of alerts to collect history.')
        parser.add_argument('from', type=str, required=True, location='json', help='Start time to search.')
        parser.add_argument('to', type=str, required=True, location='json', help='End time to search.')
        data = parser.parse_args()
        body = []
        logger.info(msg=f"History request: {data}")
        for alert_id in data['alert_ids']:
            alert_stats = Notifications.obj_exist(alert_id)
            if alert_stats:
                body.append({
                    "notification_id": alert_id,
                    "name": alert_stats.name,
                    "history": NotificationHistory.history(alert_id, data)
                })
        return {"msg": body}, 200

import logging
from flask_restx import Resource, reqparse
from actions.api.restplus import api
from flask_jwt_extended import get_jwt_identity
from actions.logic.db import Notifications, Procedures, Statistics, NotificationHistory, UsersDB, ActionsHistory, Assign
import json
import traceback
from actions.logic.auth_decorator import token_required
from actions.logic.scenarios import get_scenario_by_id

logger = logging.getLogger('default')
ns = api.namespace('api/v1/notifications', description='Alert details and history.')


@ns.route('/notification-details-short/<obj_id>')
class NotificationSimple(Resource):
    @token_required()
    def get(self, obj_id):
        """
        Simple Notification details for specific ID
        """
        try:
            alert = Notifications.obj_exist(obj_id)

            if alert:
                alert_details = alert.json_self_short()

                return {'msg': alert_details}, 200
            else:
                return {'msg': "Object id with specified id is not found."}, 404
        except Exception as err:
            logger.error(msg=f"Failed request. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Failed request. Error - {err}"}, 500


@ns.route('/notification-details/<obj_id>')
class NotificationDetails(Resource):
    @token_required()
    def get(self, obj_id):
        """
        Notification details for specific ID
        """
        try:
            alert = Notifications.obj_exist(obj_id)

            if alert:
                alert_details = alert.json_self()
                procedure_id = alert_details['procedure_id']
                procedure = get_scenario_by_id(scenario_id=procedure_id)

                if procedure:
                    alert_details['notification_procedure'] = procedure
                else:
                    logger.error(msg=f"Procedure is not found with id {procedure_id} for alert with id: {obj_id}. Default procedure will be displayed")
                    alert_details['notification_procedure'] = {
                        "procedure_id": 1,
                        "procedure_details": {}
                    }

                if alert_details['assign_status'] == 1:
                    assigned = Assign.obj_exist(obj_id)
                    if assigned:
                        alert_details['assigned'] = assigned.json()
                    else:
                        alert_details['assigned'] = {}
                        logger.error(msg=f"Assigned row is not found in assign table for alert_id: {obj_id}")
                else:
                    alert_details['assigned'] = {}
                alert_details['history'] = {
                    "statistics": Statistics.statistic(obj_id),
                    "body": NotificationHistory.history(obj_id)
                }
                return {'msg': alert_details}, 200
            else:
                return {'msg': "Object id with specified id is not found."}, 404
        except Exception as err:
            logger.error(msg=f"Failed request. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Failed request. Error - {err}"}, 500


@ns.route('/notification-details-main/<obj_id>')
class NotificationDetailsMain(Resource):
    @token_required()
    def get(self, obj_id):
        """
        Notification details for specific ID without history
        """
        try:
            alert = Notifications.obj_exist(obj_id)
            # active_alerts = ActiveAlerts.obj_exist(obj_id)

            if alert:
                alert_details = alert.json_self()
                alert_details['notification_state'] = alert_details['notification_status']

                procedure_id = alert_details['procedure_id']
                procedure = get_scenario_by_id(scenario_id=procedure_id)

                if procedure:
                    alert_details['notification_procedure'] = procedure
                else:
                    logger.error(msg=f"Procedure is not found with id {procedure_id} for alert with id: {obj_id}. Default procedure will be displayed")
                    alert_details['notification_procedure'] = {
                        "procedure_id": 1,
                        "procedure_details": {}
                    }

                if alert_details['assign_status'] == 1:
                    assigned = Assign.obj_exist(obj_id)
                    if assigned:
                        alert_details['assigned'] = assigned.json()
                    else:
                        alert_details['assigned'] = {}
                        logger.error(msg=f"Assigned row is not found in assign table for alert_id: {obj_id}")
                else:
                    alert_details['assigned'] = {}
                return {'msg': alert_details}, 200
            else:
                return {'msg': "Object id with specified id is not found."}, 404
        except Exception as err:
            logger.error(msg=f"Failed request. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Failed request. Error - {err}"}, 500


@ns.route('/notification-details-history/<obj_id>')
class NotificationDetailsHistory(Resource):
    @token_required()
    def get(self, obj_id):
        """
        Notification history for specific ID
        """
        try:
            alert = Notifications.obj_exist(obj_id)

            if alert:
                alert_history = {
                    "history": {
                        "statistics": Statistics.statistic(obj_id),
                        "body": NotificationHistory.history(obj_id)
                    }
                }
                return {'msg': alert_history}, 200
            else:
                return {'msg': "Object id with specified id is not found."}, 404
        except Exception as err:
            logger.error(msg=f"Failed request. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Failed request. Error - {err}"}, 500


@ns.route('/assign-procedure-to-notification')
class AssignProcedureToAlert(Resource):
    @token_required()
    def post(self):
        """
            Assign procedure to notification.
        """
        try:
            parser = reqparse.RequestParser(bundle_errors=True)
            parser.add_argument('notification_id', type=int, required=True, location='json', help='Describes notification_id the procedure should be assigned to.')
            parser.add_argument('procedure_id', type=int, required=True, location='json', help='Describes procedure_id assigne to the notification.')

            user_name = get_jwt_identity()
            user_id = UsersDB.find_user_id_by_username(user_name)
            data = parser.parse_args()
            obj_id = data['notification_id']
            logger.info(f"Request body: {json.dumps(data)}")
            object_ = Notifications.obj_exist(obj_id)
            if object_:
                procedure = Procedures.obj_exist(data['procedure_id'])
                if procedure:
                    object_.procedure_id = data['procedure_id']
                    object_.save_to_db()
                    ActionsHistory.add_action_to_history("assign procedure to alert", "alerts", obj_id, user_name, user_name, json.dumps({'Data': data}))
                    logger.info(msg=f"Request body: {json.dumps(data)}")
                    return {"msg": procedure.json_self()}, 200
                else:
                    logger.error(msg=f"The procedure doesn't exist. Request body: {json.dumps(data)}")
                    return {"msg": f"Procedure with id '{data['procedure_id']}' does not exist."}, 404
            else:
                logger.error(msg=f"The alert doesn't exist. Request body: {json.dumps(data)}")
                return {"msg": f"Object with id '{obj_id}' does not exist."}, 404
        except Exception as err:
            logger.error(msg=f"Failed request. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Failed request. Error - {err}"}, 500


@ns.route('/active-notifications-for-source/<source>')
class ActiveNotificationsForSource(Resource):
    @token_required()
    def get(self, source):
        """
        Rerurn list of notifications assigned to the source
        """
        try:
            notifications = Notifications.active_notifications_for_source(source)
            return notifications, 200
        except Exception as err:
            logger.error(msg=f"Failed request. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Failed request. Error - {err}"}, 500


@ns.route('/active-notifications-for-object/<source_object>')
class ActiveNotificationsForObject(Resource):
    @token_required()
    def get(self, source_object):
        """
        Rerurn list of notifications assigned to the object
        """
        try:
            notifications = Notifications.active_notifications_for_object(source_object)
            return notifications, 200
        except Exception as err:
            logger.error(msg=f"Failed request. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Failed request. Error - {err}"}, 500

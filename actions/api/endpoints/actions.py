import logging
import traceback
from actions.logic.force_update import ForceUpdate
from flask_restx import Resource, reqparse
from flask import request
from actions.settings import BRIDGE_HOST
from actions.api.restplus import api
from actions.logic.db import Notifications, ActionsHistory, NotificationHistory, ActiveAlerts, Statistics, Assign
import json
import requests
import datetime
from actions.tools.prometheus_metrics import Prom
from actions.logic.auth_decorator import token_required
from actions.logic.auth_decorator import get_user_id_by_token
from actions.logic.user_info import get_user_info, get_user_info_by_id


logger = logging.getLogger('default')
ns = api.namespace('api/v1/actions', description='Actions')


@ns.route('/add-comment')
class ActionComment(Resource):
    @token_required()
    def post(self):
        """
            Adding comment to alerts list.
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)
            obj_id = []
            data = request.json
            logger.info(f"Receive request to add-comment: {username}\nObject ID: {obj_id}\nBody: {json.dumps(data)}")
            for alert_id in data['alert_ids']:
                NotificationHistory.add_new_event({'alert_id': alert_id, 'notification_action': 'Adding comment', 'comments': json.dumps({'comment': data['comment'], 'author': username})})
                ActionsHistory.add_action_to_history_({'name': 'Add comment', 'obj_type': 'alert', 'obj_id': alert_id, 'username': username, 'notes': json.dumps(data['comment'])})
                Prom.notification_statistics_by_alert_name.labels(
                    alert_id=alert_id,
                    event_name='Adding comment',
                    user_name=username
                ).inc(1)
            return {"msg": "Comment added."}, 200
        except Exception as err:
            logger.error(msg=f"Can`t add-comment. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t add-comment. Error - {err}"}, 500


@ns.route('/add-description')
class ActionDescription(Resource):
    @token_required()
    def post(self):
        """
            Adding description to list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            obj_id = []
            data = request.json
            logger.info(f"Receive request to add-description: {username}\nobject_id: {obj_id}\nBody: {json.dumps(data)}")
            for alert_id in data['alert_ids']:
                Notifications.update_description(alert_id, data['description'])
                ActionsHistory.add_action_to_history_({'name': 'Change description.', 'obj_type': 'alert', 'obj_id': alert_id, 'username': username, 'notes': json.dumps({'description': data['description']})})
                Prom.notification_statistics_by_alert_name.labels(
                    alert_id=alert_id,
                    event_name='Add description',
                    user_name=username
                ).inc(1)
            return {"msg": "Data collected"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t add-description. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t add-description. Error - {err}"}, 500


@ns.route('/resolve')
class ActionResolve(Resource):
    @token_required()
    def post(self):
        """
            Resolving list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)
            obj_id = []
            data = request.json
            logger.info(msg=f"Receive request to Resolve alert: {username}\nobject_id: {obj_id}\nBody: {json.dumps(data)}")
            for alert_id in data['alert_ids']:
                ActiveAlerts.delete_exist_event(alert_id)
                Notifications.update_notification_status(alert_id, 0)
                NotificationHistory.add_new_event({'alert_id': alert_id, 'notification_output': Notifications.current_output(alert_id), 'notification_action': 'Resolve alert', 'comments': json.dumps({'author': username, 'comment': data['comment']})})
                current_count = Statistics.get_counter(alert_id)
                if current_count:
                    Statistics.update_counter(alert_id, {'close': current_count.close + 1})
                ActionsHistory.add_action_to_history_({'name': 'Resolving alert', 'obj_type': 'alert', 'obj_id': alert_id, 'username': username, 'notes': json.dumps({'description': data['comment']})})
                Prom.notification_statistics_by_alert_name.labels(
                    alert_id=alert_id,
                    event_name='Resolve alert',
                    user_name=username
                ).inc(1)

            force_update = ForceUpdate(alert_ids=data['alert_ids'])
            force_update.main()
            try:
                result = requests.get(f'http://{BRIDGE_HOST}/api/v1/bridge-actions/update_cache/0', timeout=5).json()
            except:
                result = {}
            logger.info(msg=f"Receive request to update cache - {username}\nobject_id: {obj_id}\nBody: {json.dumps(result)}")
            return {"msg": "Alerts resolved."}, 200
        except Exception as err:
            logger.error(msg=f"Can`t resolve alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t resolve alert. Error - {err}"}, 500


@ns.route('/jira')
class ActionJira(Resource):
    @token_required()
    def post(self):
        """
            Create Jira for list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            obj_id = []
            data = request.json
            logger.info(msg=f"Receive request to create JIRA: {username}\nobject_id: {obj_id}\nBody: {json.dumps(data)}")
            return {"msg": "Data collected"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t create JIRA. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t create JIRA. Error - {err}"}, 500


@ns.route('/snooze')
class ActionSnooze(Resource):
    @token_required()
    def post(self):
        """
            Snoozing list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)
            user_info = get_user_info(username)

            parser = reqparse.RequestParser(bundle_errors=True)
            parser.add_argument('alert_ids', type=list, required=True, location='json', help='List of alerts to snooze.')
            parser.add_argument('action_ts', type=str, required=True, location='json', help='Snoozed till timestamp')
            parser.add_argument('comment', type=str, required=True, location='json', default='',
                                help='Reason of snooze.')
            parser.add_argument('sticky_severity', type=int, required=True, location='json',
                                help='Disable snooze once alert changed its severity. False: 0, True: 1')
            parser.add_argument('sticky_output', type=int, required=True, location='json',
                                help='Disable snooze once alert changed its value in output. False: 0, True: 1')
            data = parser.parse_args()
            logger.info(msg=f"Received request to snooze alert - {username}\nBody: {json.dumps(data)}")
            action_ts = datetime.datetime.strptime(data['action_ts'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")

            for alert_id in data['alert_ids']:
                ActiveAlerts.update_exist_event(alert_id, {
                    'snooze_expire_ts': action_ts,
                    'handle_expire_ts': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'action_by': json.dumps(user_info)
                })
                Notifications.update_exist_event(alert_id, {'snooze_expire_ts': action_ts,
                                                            'sticky': (2 if data['sticky_severity'] else 0) +
                                                                      (3 if data['sticky_output'] else 0),
                                                            'action_by': json.dumps(user_info)
                                                            }
                                                 )
                NotificationHistory.add_new_event({'alert_id': alert_id,
                                                   'notification_output': Notifications.current_output(alert_id),
                                                   'notification_action': 'Snooze alert',
                                                   'comments': json.dumps({
                                                       'author': username,
                                                       'comment': data['comment'],
                                                       'till': action_ts})
                                                   })
                ActionsHistory.add_action_to_history_({
                    'name': 'Snooze alert',
                    'obj_type': 'alert',
                    'obj_id': alert_id,
                    'username': username,
                    'notes': json.dumps({'description': data['comment']})
                })
                current_count = Statistics.get_counter(alert_id)
                if current_count:
                    Statistics.update_counter(alert_id, {'snooze': current_count.snooze + 1})
                Prom.notification_statistics_by_alert_name.labels(
                    alert_id=alert_id,
                    event_name='Snooze alert',
                    user_name=username
                ).inc(1)
                logger.info(msg=f"Alert was snoozed: {alert_id}. Username: {username}")

            force_update = ForceUpdate(alert_ids=data['alert_ids'])
            force_update.main()
            return {"msg": "Alert snoozed"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t snooze alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t snooze alert. Error - {err}"}, 500


@ns.route('/cancel-snooze')
class ActionCancelSnooze(Resource):
    @token_required()
    def post(self):
        """
            Cancel snoozing for list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            parser = reqparse.RequestParser(bundle_errors=True)
            parser.add_argument('alert_ids', type=list, required=True, location='json', help='List of alerts to snooze.')
            parser.add_argument('comment', type=str, required=True, location='json', default='', help='Reason of snooze.')
            data = parser.parse_args()
            logger.info(msg=f"Receive request to cancel snooze. User: {username}\nBody: {json.dumps(data)}")
            for alert_id in data['alert_ids']:
                ActiveAlerts.update_exist_event(alert_id,
                                                {'snooze_expire_ts': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                Notifications.update_exist_event(alert_id,
                                                 {'snooze_expire_ts': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                NotificationHistory.add_new_event({'alert_id': alert_id,
                                                   'notification_output': Notifications.current_output(alert_id),
                                                   'notification_action': 'Cancel snooze',
                                                   'comments': json.dumps({'author': username,
                                                                           'comment': data['comment']
                                                                           })
                                                   })
                ActionsHistory.add_action_to_history_({'name': 'Cancel snooze', 'obj_type': 'alert',
                                                       'obj_id': alert_id, 'username': username,
                                                       'notes': json.dumps({'description': data['comment']})
                                                       })
                Prom.notification_statistics_by_alert_name.labels(
                    alert_id=alert_id,
                    event_name='Cancel snooze',
                    user_name=username
                ).inc(1)
                logger.info(msg=f"Snooze was canceled: {alert_id}. Username: {username}")
            return {"msg": "Snooze canceled"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t cancel snooze for alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t cancel snooze for alert. Error - {err}"}, 500


@ns.route('/handle')
class ActionHandle(Resource):
    @token_required()
    def post(self):
        """
            Handling list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            parser = reqparse.RequestParser(bundle_errors=True)
            parser.add_argument('alert_ids', type=list, required=True, location='json', help='List of alerts to snooze.')
            parser.add_argument('action_ts', type=str, required=True, location='json', help='Handled till timestamp')
            parser.add_argument('assign_to', type=str, required=True, location='json', help='Assign to')

            data = parser.parse_args()
            logger.info(msg=f"Receive request to handle alert - {username}\nBody: {json.dumps(data)}")
            action_ts = datetime.datetime.strptime(data['action_ts'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")
            user_info = get_user_info_by_id(int(data['assign_to']))

            for alert_id in data['alert_ids']:
                ActiveAlerts.update_exist_event(
                    event_id=alert_id,
                    data={
                        'handle_expire_ts': action_ts,
                        'assigned_to': json.dumps(user_info)
                    }
                )

                Notifications.update_exist_event(alert_id, {'assigned_to': json.dumps(user_info)})

                NotificationHistory.add_new_event({'alert_id': alert_id,
                                                   'notification_output': Notifications.current_output(alert_id),
                                                   'notification_action': 'Handle alert',
                                                   'comments': json.dumps({
                                                       'author': username, 'till': action_ts})})
                ActionsHistory.add_action_to_history_({
                    'name': 'Handle alert', 'obj_type': 'alert', 'obj_id': alert_id,
                    'username': username,
                    'notes': f'Handled till: {action_ts}'})
                Prom.notification_statistics_by_alert_name.labels(
                    alert_id=alert_id,
                    event_name='Handle alert',
                    user_name=username
                ).inc(1)
                logger.info(msg=f"Alert was handled: {alert_id}. Username: {username}")

            force_update = ForceUpdate(alert_ids=data['alert_ids'])
            force_update.main()

            return {"msg": "Alert handled"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t handle alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t handle alert. Error - {err}"}, 500


@ns.route('/cancel-handle')
class ActionCancelHandle(Resource):
    @token_required()
    def post(self):
        """
            Cancel handling for list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            parser = reqparse.RequestParser(bundle_errors=True)
            parser.add_argument('alert_ids', type=list, required=True, location='json',
                                help='List of alerts to cancel handle.')
            data = parser.parse_args()
            logger.info(msg=f"Receive request to cancel handle for alert: {username}\nBody{json.dumps(data)}")
            for alert_id in data['alert_ids']:
                ActiveAlerts.update_exist_event(alert_id,
                                                {'handle_expire_ts': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                NotificationHistory.add_new_event({'alert_id': alert_id,
                                                   'notification_output': Notifications.current_output(alert_id),
                                                   'notification_action': 'Cancel handling',
                                                   'comments': json.dumps({'author': username})})
                ActionsHistory.add_action_to_history_({'name': 'Cancel handling', 'obj_type': 'alert',
                                                       'obj_id': alert_id, 'username': username, 'notes': ''})
                Prom.notification_statistics_by_alert_name.labels(
                    alert_id=alert_id,
                    event_name='Cancel handling',
                    user_name=username
                ).inc(1)
                logger.info(msg=f"Cancel handling: {alert_id}. Username: {username}")
            return {"msg": "Handling canceled"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t cancel handle for alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t cancel handle for alert. Error - {err}"}, 500


@ns.route('/acknowledge')
class ActionAcknowledge(Resource):
    @token_required()
    def post(self):
        """
            Acknowledging list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)
            user_info = get_user_info(username)

            parser = reqparse.RequestParser(bundle_errors=True)
            parser.add_argument('alert_ids', type=list, required=True, location='json', help='List of alerts to snooze.')
            parser.add_argument('comment', type=str, required=True, location='json', default='', help='Reason of acknowledge.')
            data = parser.parse_args()
            logger.info(f"Receive request to acknowledge alert - {username}\nBody: {json.dumps(data)}")
            for alert_id in data['alert_ids']:
                ActiveAlerts.update_exist_event(alert_id, {
                    'acknowledged': 1,
                    'handle_expire_ts': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'action_by': json.dumps(user_info)
                })

                NotificationHistory.add_new_event(
                    {
                        'alert_id': alert_id,
                        'notification_output': Notifications.current_output(alert_id),
                        'notification_action': 'Acknowledge',
                        'comments': json.dumps({'author': username, 'comment': data['comment']})
                    }
                )

                ActionsHistory.add_action_to_history_(
                    {
                        'name': 'Acknowledge alert',
                        'obj_type': 'alert',
                        'obj_id': alert_id,
                        'username': username,
                        'notes': json.dumps({'description': data['comment']})
                    }
                )

                current_count = Statistics.get_counter(alert_id)
                if current_count:
                    Statistics.update_counter(alert_id, {'acknowledge': current_count.acknowledge + 1})
                Prom.notification_statistics_by_alert_name.labels(
                    alert_id=alert_id,
                    event_name='Acknowledge alert',
                    user_name=username
                ).inc(1)

                logger.info(msg=f"Alert acknowledged: {alert_id}. Username: {username}")

            force_update = ForceUpdate(alert_ids=data['alert_ids'])
            force_update.main()

            return {"msg": "Acknowledged"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t acknowledge alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t acknowledge alert. Error - {err}"}, 500


@ns.route('/cancel-acknowledge')
class ActionCancelAcknowledge(Resource):
    @token_required()
    def post(self):
        """
            Cancel acknowledging for list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            parser = reqparse.RequestParser(bundle_errors=True)
            parser.add_argument('alert_ids', type=list, required=True, location='json', help='List of alerts to snooze.')
            parser.add_argument('comment', type=str, required=True, location='json', default='', help='Reason of acknowledge.')
            data = parser.parse_args()
            logger.info(f"Receive request to cancel acknowledge - {username}\nBody: {json.dumps(data)}")
            for alert_id in data['alert_ids']:
                ActiveAlerts.update_exist_event(alert_id, {'acknowledged': 0})
                NotificationHistory.add_new_event(
                    {
                        'alert_id': alert_id,
                        'notification_output': Notifications.current_output(alert_id),
                        'notification_action': 'Cancel acknowledge',
                        'comments': json.dumps({'author': username, 'comment': data['comment']})
                    }
                )
                ActionsHistory.add_action_to_history_(
                    {
                        'name': 'Cancel acknowledge',
                        'obj_type': 'alert',
                        'obj_id': alert_id,
                        'username': username,
                        'notes': json.dumps({'description': data['comment']})
                    }
                )
                Prom.notification_statistics_by_alert_name.labels(
                    alert_id=alert_id,
                    event_name='Cancel acknowledge',
                    user_name=username
                ).inc(1)
                logger.info(msg=f"Cancel alert acknowledge: {alert_id}. Username: {username}")
            return {"msg": "Acknowledge canceled"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t cancel acknowledge for alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t cancel acknowledge for alert. Error - {err}"}, 500


@ns.route('/downtime')
class ActionDowntime(Resource):
    @token_required()
    def post(self):
        """
            Downtime list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            obj_id = []
            data = request.json
            logger.info(f"Receive request to downtime alert - {username}\nObject_id: {obj_id}\nBody: {json.dumps(data)}")

            return {"msg": "Data collected"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t downtime alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t downtime alert. Error - {err}"}, 500


@ns.route('/cancel-downtime')
class ActionCancelDowntime(Resource):
    @token_required()
    def post(self):
        """
            Cancelling downtime for list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            obj_id = []
            data = request.json
            logger.info(f"Receive request to cancel downtime alert - {username}\nObject_id: {obj_id}\nBody: {json.dumps(data)}")

            return {"msg": "Data collected"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t cancel downtime alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t cancel downtime alert. Error - {err}"}, 500


@ns.route('/assign')
class ActionAssign(Resource):
    @token_required()
    def post(self):
        """
            Assign list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            parser = reqparse.RequestParser(bundle_errors=True)
            parser.add_argument('alert_ids', type=list, required=True, location='json', help='List of alerts to snooze.')
            parser.add_argument('description', type=str, required=True, location='json', default='', help='Some description.')
            parser.add_argument('resubmit', type=int, required=True, location='json', default=1, help='Resubmit period.')
            parser.add_argument('time_to', type=str, required=True, location='json', help='Assign end timestamp')
            parser.add_argument('notification_type', type=int, required=True, location='json', default={}, help='Type of notification.')
            parser.add_argument('notification_fields', type=dict, required=True, location='json', default={}, help='Jira notification details.')
            # parser.add_argument('skype_fields', type=dict, required=False, location='json', default={}, help='Skype notification details.')
            # parser.add_argument('teams_fields', type=dict, required=False, location='json', default={}, help='Teams notification details.')
            # parser.add_argument('telegram_fields', type=dict, required=False, location='json', default={}, help='Telegram notification details.')
            parser.add_argument('sticky_severity', type=int, required=True, location='json', help='Disable assign once alert changed its severity. False: 0, True: 1')
            parser.add_argument('sticky_output', type=int, required=True, location='json', help='Disable assign once alert changed its value in output. False: 0, True: 1')
            data = parser.parse_args()

            logger.info(f"Receive request to assign alert - {username}\nBody: {json.dumps(data)}")

            for alert_id in data['alert_ids']:
                ActiveAlerts.update_exist_event(alert_id, {
                    'assign_status': 1,
                    'handle_expire_ts': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                Notifications.update_exist_event(alert_id, {'assign_status': 1})
                current_assign = Assign.obj_exist(alert_id)
                if current_assign:
                    current_assign.delete_from_db()
                body = {
                    'alert_id': alert_id,
                    'notification_type': data['notification_type'],
                    'notification_fields': json.dumps(data['notification_fields']),
                    'description': data['description'],
                    'resubmit': data['resubmit'],
                    'sticky': (2 if data['sticky_severity'] else 0) + (3 if data['sticky_output'] else 0),
                    'recipient_id': '',
                    'time_to': datetime.datetime.strptime(data['time_to'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")}
                Assign.add_new_event(body)
                description = f"{data['description']}"
                NotificationHistory.add_new_event(
                    {
                        'alert_id': alert_id,
                        'notification_output': Notifications.current_output(alert_id),
                        'notification_action': 'Assign',
                        'comments': json.dumps({'author': username, 'comment': description, 'till': datetime.datetime.strptime(data['time_to'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")})
                    }
                )
                ActionsHistory.add_action_to_history_(
                    {
                        'name': 'Assign alert',
                        'obj_type': 'alert',
                        'obj_id': alert_id,
                        'username': username,
                        'notes': json.dumps(body)
                     }
                )
                current_count = Statistics.get_counter(alert_id)
                if current_count:
                    Statistics.update_counter(alert_id, {'assign': current_count.assign + 1})
                Prom.notification_statistics_by_alert_name.labels(
                    alert_id=alert_id,
                    event_name='Assign alert',
                    user_name=username
                ).inc(1)

                logger.info(msg=f"Alert assign: {alert_id}. Username: {username}")

                force_update = ForceUpdate(alert_ids=data['alert_ids'])
                force_update.main()

                return {"msg": "Alert assigned."}, 200
        except Exception as err:
            logger.error(msg=f"Can`t assign alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t assign alert. Error - {err}"}, 500


@ns.route('/cancel-assign')
class ActionAssign(Resource):
    @token_required()
    def post(self):
        """
            Cancel assigning for list of alerts
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            parser = reqparse.RequestParser(bundle_errors=True)
            parser.add_argument('alert_ids', type=list, required=True, location='json', help='List of alerts to snooze.')
            parser.add_argument('comment', type=str, required=True, location='json', default='', help='Comment.')
            data = parser.parse_args()
            logger.info(f"Receive request to cancel assign: {username}\n Body: {json.dumps(data)}")

            for alert_id in data['alert_ids']:
                ActiveAlerts.update_exist_event(alert_id, {'assign_status': 0})
                Notifications.update_exist_event(alert_id, {'assign_status': 0})
                current_assign = Assign.obj_exist(alert_id)
                if current_assign:
                    current_assign.delete_from_db()
                    NotificationHistory.add_new_event(
                        {
                            'alert_id': alert_id,
                            'notification_output': Notifications.current_output(alert_id),
                            'notification_action': 'Cancel assign',
                            'comments': json.dumps({'author': username, 'comment': data['comment']})
                        }
                    )
                    ActionsHistory.add_action_to_history_(
                        {
                            'name': 'Cancel assign',
                            'obj_type': 'alert',
                            'obj_id': alert_id,
                            'username': username,
                            'notes': json.dumps({'description': data['comment']})
                         }
                    )
                    logger.debug(msg=f"Cancel assign: {alert_id}. Username: {username}")
                    return {"msg": "Cancel assign."}, 200
        except Exception as err:
            logger.error(msg=f"Can`t cancel assign alert. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t cancel assign alert. Error - {err}"}, 500


@ns.route('/recheck-action')
class RecheckAction(Resource):
    @token_required()
    def post(self):
        """
            Recheck object with specified id.
        """
        try:
            auth_token = request.headers.get('AuthToken')
            username = get_user_id_by_token(auth_token)

            obj_id = []
            data = request.json
            logger.info(f"Receive request to recheck action - {username}\nBody: {json.dumps(data)}\nObject_id: {obj_id}")
            return {"msg": "Data collected"}, 200
        except Exception as err:
            logger.error(msg=f"Can`t recheck action. Error: {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Can`t recheck action. Error - {err}"}, 500

import logging
from flask_restx import Resource, reqparse
from actions.api.restplus import api
from flask_jwt_extended import get_jwt_identity
from actions.logic.db import Procedures, UsersDB, ActionsHistory, Storage
from actions.logic.jira import GenerateJira
from sqlalchemy.sql import func
import json
from werkzeug.exceptions import NotFound
from actions.logic.auth_decorator import token_required

logger = logging.getLogger('default')
ns = api.namespace('api/v1/procedures', description='Procedures')


@ns.route('/tags')
class Tags(Resource):

    @staticmethod
    @token_required()
    def get():
        """
            Returns list of tags for procedures
        """
        return {'data': Storage.values_by_type('tags')}, 200


@ns.route('/search')
class ProceduresSearch(Resource):
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('pattern', type=str, required=False, location='json', default='',
                        help='The pattern is used for filtering by procedure name.')
    parser.add_argument('name', type=str, required=False, location='json', default='',
                        help='The name is used for filtering by procedure name.')
    parser.add_argument('studio_id', type=int, required=False, location='json', default=-1,
                        help='Filtering by Studio name.')
    parser.add_argument('procedure_type', type=str, required=False, location='json', help='Search by procedure type',
                        default='-1')
    parser.add_argument('procedure_id', type=int, required=False, location='json', help='Search by procedure id',
                        default=None)
    parser.add_argument('tags', type=str, required=False, location='json', default=None, help='Filtering by tags.')
    parser.add_argument('alert_fields', type=bool, required=False, location='json', default=False,
                        help='Filtering by configured Alert notifications .')
    parser.add_argument('email_fields', type=bool, required=False, location='json', default=False,
                        help='Filtering by configured e-mail notifications.')
    parser.add_argument('jira_fields', type=bool, required=False, location='json', default=False,
                        help='Filtering by configured Jira notifications.')
    parser.add_argument('skype_fields', type=bool, required=False, location='json', default=False,
                        help='Filtering by configured Skype notifications.')
    parser.add_argument('teams_fields', type=bool, required=False, location='json', default=False,
                        help='Filtering by configured Teams notifications.')
    parser.add_argument('telegram_fields', type=bool, required=False, location='json', default=False,
                        help='Filtering by configured Telegram notifications.')
    parser.add_argument('pagerduty_fields', type=bool, required=False, location='json', default=False,
                        help='Filtering by configured PagerDuty notifications.')
    parser.add_argument('sms_fields', type=bool, required=False, location='json', default=False,
                        help='Filtering by configured SMS notifications.')
    parser.add_argument('voice_fields', type=bool, required=False, location='json', default=False,
                        help='Filtering by configured Voice notifications.')
    parser.add_argument('whatsapp_fields', type=bool, required=False, location='json', default=False,
                        help='Filtering by configured WhatsApp notifications.')
    parser.add_argument('recipient_pattern', type=str, required=False, location='json', default='',
                        help='Filtering by recipient.')

    @token_required()
    def post(self, department=None):
        """
        Search procedures by name with pattern, by alert, email, jira, skype, teams and telegram fields
        """
        data = ProceduresSearch.parser.parse_args()
        logger.info(f"Request body: {json.dumps(data)}")
        result = Procedures.search(data)
        return {'msg': result}, 200


@ns.route('/direct-search')
class DirectProceduresSearch(Resource):
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('pattern', type=str, required=False, location='json', default='',
                        help='The pattern is used for filtering by procedure name.')
    parser.add_argument('studio_ids', type=list, required=True, location='json', default=None,
                        help='Filtering by Studio names.')
    parser.add_argument('tag', type=str, required=False, location='json', default=None,
                        help='Filtering by tag.')

    @token_required()
    def post(self):
        """
        Direct search procedures by name with pattern and studio ids. The endpoint is used by Zergus.
        """
        data = DirectProceduresSearch.parser.parse_args()
        logger.info(f"Request body: {json.dumps(data)}")
        result = Procedures.direct_search(data['pattern'], data['studio_ids'], data['tag'])
        return {'data': result}, 200


@ns.route('/edit/<int:obj_id>')
class ProceduresEdit(Resource):
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('id', type=int, required=True, location='json', help='Id of the procedure')
    parser.add_argument('name', type=str, required=True, location='json', help='Name of the procedure')
    parser.add_argument('studio_id', type=list, required=True, location='json',
                        help='List of studios the procedure should be assigned to.')
    parser.add_argument('description', type=str, required=True, location='json', help='Description of the procedure.')
    parser.add_argument('wiki', type=str, required=True, location='json', help='Link to wiki page')
    parser.add_argument('requested_by', type=str, required=True, location='json',
                        help='Reason of adding the procedure.')
    parser.add_argument('thresholds', type=str, required=False, location='json', default='',
                        help='Thresholds for the unique procedure.')
    parser.add_argument('tags', type=list, required=False, location='json', default='', help='List of tags.')
    parser.add_argument('procedure_type', type=int, required=True, location='json',
                        help='Type of the procedure: 0 - shared, 1 - unique, 2 - OPS(example)')
    parser.add_argument('alert_fields', type=dict, required=True, location='json', help='Alerts related fields.')
    parser.add_argument('email_fields', type=dict, required=True, location='json', help='Email related fields.')
    parser.add_argument('jira_fields', type=dict, required=True, location='json', help='Jira related fields.')
    parser.add_argument('skype_fields', type=dict, required=True, location='json', help='Skype related fields.')
    parser.add_argument('teams_fields', type=dict, required=True, location='json', help='Teams related fields.')
    parser.add_argument('telegram_fields', type=dict, required=True, location='json', help='Telegram related fields.')
    parser.add_argument('pagerduty_fields', type=dict, required=True, location='json', help='Pagerduty related fields.')
    parser.add_argument('sms_fields', type=dict, required=True, location='json', help='SMS related fields.')
    parser.add_argument('voice_fields', type=dict, required=True, location='json', help='Voice related fields.')
    parser.add_argument('whatsapp_fields', type=dict, required=True, location='json', help='WhatsApp related fields.')

    @token_required()
    def get(self, obj_id):
        """
            Edit object by provided id.
        """
        obj = Procedures.obj_exist(obj_id=obj_id)
        if not obj:
            return {"msg": "Object is not found."}, 500
        result = obj.json_self()
        return result, 200

    @token_required()
    def post(self, obj_id, department=None):
        """
            Update object by provided id.
        """

        user_name = department if department else get_jwt_identity()
        user_id = UsersDB.find_user_id_by_username(user_name)
        parser = ProceduresEdit.parser.copy()
        parser.remove_argument('studio_id')
        data = parser.parse_args()
        logger.info(f"Request body: {json.dumps(data)}")
        obj_id = data.get('id', None)
        object_ = Procedures.obj_exist(obj_id)
        tags = data.get('tags', [])
        if len(tags) > 0:
            Storage.add_new_event(user_name, 'tags', tags)

        if object_:
            object_.name = data.get('name', None)
            object_.description = data.get('description', None)
            object_.wiki = data.get('wiki', None)
            object_.thresholds = data.get('thresholds', None)
            object_.tags = json.dumps(data.get('tags', []))
            object_.procedure_type = data.get('procedure_type', None)
            object_.requested_by = data.get('requested_by', None)
            object_.alert_fields = json.dumps(data.get('alert_fields', {}))
            object_.email_fields = json.dumps(data.get('email_fields', {}))
            object_.jira_fields = json.dumps(data.get('jira_fields', {}))
            object_.skype_fields = json.dumps(data.get('skype_fields', {}))
            object_.teams_fields = json.dumps(data.get('teams_fields', {}))
            object_.telegram_fields = json.dumps(data.get('telegram_fields', {}))
            object_.pagerduty_fields = json.dumps(data.get('pagerduty_fields', {}))
            object_.sms_fields = json.dumps(data.get('sms_fields', {}))
            object_.voice_fields = json.dumps(data.get('voice_fields', {}))
            object_.whatsapp_fields = json.dumps(data.get('whatsapp_fields', {}))
            object_.edited_by = user_id
            object_.last_update_ts = func.now()
            object_.save_to_db()
            ActionsHistory.add_action_to_history("edit procedure", "procedures", obj_id, user_name, "",
                                                 json.dumps({'Procedure name': data['name']}))
            return {"msg": object_.json_self()}, 200
        else:
            return {"msg": f"Object with id '{obj_id}' does not exist."}, 404

    @token_required()
    def put(self, obj_id, department=None):
        """
            Create new object.
        """
        user_name = department if department else get_jwt_identity()
        if not user_name:
            return {"msg": "User is None", "description": ""}, 400
        user = UsersDB.find_by_username(user_name)
        user_type = user.user_type
        parser = ProceduresEdit.parser.copy()
        parser.remove_argument('id')
        data = parser.parse_args()
        logger.info(f"Request body: {json.dumps(data)}")
        name = data.get('name', None)
        studios = data.get('studio_id', [])
        adding_summary = {'Already exist procedures': []}
        ignored_procedures = []
        last_added_object = None
        for studio_id in studios:
            exist_procedure = Procedures.obj_exist_with_name_for_studio_id(name, studio_id)
            if exist_procedure:
                adding_summary['Already exist procedures'].append({'name': f"{studio_id}: {name}",
                                                                   'id': exist_procedure.id})
                continue
            object_ = Procedures(
                name=data.get('name', None),
                studio_id=studio_id,
                description=data.get('description', None),
                wiki=data.get('wiki', None),
                requested_by=data.get('requested_by', None),
                thresholds=data.get('thresholds', None),
                tags=json.dumps(data.get('tags', [])),
                procedure_type=data.get('procedure_type', None),
                alert_fields=json.dumps(data.get('alert_fields', {})),
                email_fields=json.dumps(data.get('email_fields', {})),
                jira_fields=json.dumps(data.get('jira_fields', {})),
                skype_fields=json.dumps(data.get('skype_fields', {})),
                teams_fields=json.dumps(data.get('teams_fields', {})),
                telegram_fields=json.dumps(data.get('telegram_fields', {})),
                pagerduty_fields=json.dumps(data.get('pagerduty_fields', {})),
                sms_fields=json.dumps(data.get('sms_fields', {})),
                voice_fields=json.dumps(data.get('voice_fields', {})),
                whatsapp_fields=json.dumps(data.get('whatsapp_fields', {})),
                edited_by=user.id,
                last_update_ts=func.now()
            )
            object_.save_to_db()
            last_added_object = object_.json_self()
            if user_type not in [1, 2, 7] and data.get('alert_fields', []):
                try:
                    jira = GenerateJira(reporter=user_name, procedure_name=last_added_object['name'],
                                        procedure_id=last_added_object['id'])
                    jira_id = jira.create_jira()
                except Exception as jira_exc:
                    return {"msg": "Can't create Jira", "description": str(jira_exc)}, 450
                else:
                    object_.procedure_review_status = str(jira_id)
                    object_.save_to_db()
                    last_added_object = object_.json_self()
                    ActionsHistory.add_action_to_history(
                        "add new procedure", "procedures", last_added_object['id'], user_name, "",
                        json.dumps({'Procedure name': last_added_object['name'], 'Studio': studio_id, 'data': data}))
        if ignored_procedures:
            adding_summary['Ignored procedures (denied to add): '] = " ,".join(ignored_procedures)
        if last_added_object:
            return {"msg": last_added_object, "description": adding_summary}, 200
        else:
            return {"msg": "Nothing added to DB.", "description": adding_summary}, 400

    @token_required()
    def delete(self, obj_id):
        """
            Delete object by provided id.
        """
        user_name = get_jwt_identity()
        user = UsersDB.find_user_id_by_username(user_name)
        obj = Procedures.obj_exist(obj_id)
        if obj:
            obj.delete_from_db()
            ActionsHistory.add_action_to_history("delete procedure", "procedures", obj_id, user_name, "", "")
            return {"msg": "Deleted."}, 200
        return {"msg": "The query does not exist."}, 404


@ns.route('/<string:scenario_name>')
class GetScenario(Resource):
    @staticmethod
    def get(scenario_name):
        """
            Return Scenario object by name
        """
        if not scenario_name:
            return {'msg': 'scenario_name should be specified'}, 404
        obj = Procedures.get_scenario_by_name(scenario_name)
        if not obj:
            raise NotFound('object with scenario_name is not found')
        result = obj.json_self()
        return {"msg": result}, 200

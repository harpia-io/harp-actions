import logging
import json
from flask_restx import Resource, reqparse
from flask import request
from actions.logic.db import UsersDB, ActionsHistory
from actions.app import config
from actions.api.restplus import api
from flask_jwt_extended import get_jwt_identity
from actions.settings import AUTO_USERS
import traceback
from actions.logic.auth_decorator import token_required

logger = logging.getLogger('default')
ns = api.namespace('api/v1/home', description='Home page')


@ns.route('/')
class Home(Resource):
    def get(self):
        """
        Get home JSON
        """
        return {'status': 'success', 'msg': '++'}, 200


@ns.route('/login')
class Login(Resource):

    def get(self):
        """
        Get home JSON
        """
        return {}, 200

    def post(self):
        """
        User's login
        """

        data = request.json
        username = data.get('username', None)
        password = data.get('password', None)

        try:
            if not username:
                return {"msg": "Missing username parameter"}, 401
            if not password:
                return {"msg": "Missing password parameter"}, 401

            if username in AUTO_USERS:
                return UsersDB.authenticate(username)
            else:
                return UsersDB.authenticate(username)

        except Exception as exc:
            logger.error(
                msg=f"Login exception: {data}, \n {exc}, \n {traceback.format_exc()}, \n {self.__class__.__name__}"
            )


@ns.route('/user-schema-edit')
class UserEdit(Resource):
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('user_schema', type=dict, required=True, location='json', help='User schema')

    @token_required()
    def get(self):
        """
            GET object by provided id.
        """
        user_name = get_jwt_identity()
        obj_id = UsersDB.find_user_id_by_username(user_name)
        obj = UsersDB.obj_exist(obj_id=obj_id)
        if not obj:
            return {"msg": "Object is not found."}, 500
        result = obj.json_self()['user_schema']
        return {'msg': result}, 200

    @token_required()
    def post(self):
        """
            Update object by provided id.
        """

        user_name = get_jwt_identity()
        obj_id = UsersDB.find_user_id_by_username(user_name)
        data = UserEdit.parser.parse_args()
        logger.info(f"Request body: {json.dumps(data)}")
        object_ = UsersDB.obj_exist(obj_id)
        if object_:
            object_.user_schema = json.dumps(data['user_schema'])
            object_.save_to_db()
            ActionsHistory.add_action_to_history("edit user_schema", "users", obj_id, user_name, "", json.dumps({'User schema': data['user_schema']}))
            return {"msg": object_.json_self()['user_schema']}, 200
        else:
            return {"msg": f"Object with id '{obj_id}' does not exist."}, 404


@ns.route('/dictionaries-types')
class DictionariesTypes(Resource):

    @token_required()
    def get(self):
        """
        Get dictionary types
        """
        types = {
            'list': ['item1', 'item2', 'item1', 'item4'],
            'list-distinct': ['item1', 'item2', 'item4'],
            'list-dict-id-name': [{'id': 2, 'name': 'Name of object 1'}, {'id': 3, 'name': 'Name of object 2'}, {'id': 4, 'name': 'Name of object 3'}],
            'list-dict-detailed': [{'id': 2, 'name': 'Name of object 1', 'service': 'Factory', 'studio': 'Slotomania'},
                                   {'id': 3, 'name': 'Name of object 2', 'service': 'Flask', 'studio': 'Caesars Casino'},
                                   {'id': 4, 'name': 'Name of object 3', 'service': 'Storm', 'studio': 'VDS'}]
        }
        return {'status': 'success', 'msg': types}, 200


@ns.route('/dictionaries/<string:dict_name>/<string:dict_type>')
class Dictionaries(Resource):

    @token_required()
    def get(self, dict_type, dict_name):
        """
        Get dictionary by provided type and name
        """
        dictionaries = {
            'procedures-types': {
                'list-dict-id-name': [
                    {'id': '0', 'name': 'Shared'},
                    {'id': '1', 'name': 'Unique'},
                    {'id': '2', 'name': 'OPS team related'},
                    {'id': '3', 'name': 'ENG team related'}
                ]
            },
            'applications': {
                'list-distinct': ['Slotomania', 'Caesars Casino', 'Bingo Blitz', 'VDS', 'ME', 'House of Fun'],
            },
            'environment': {
                'dict-id-name': {**config['studios_dict'], **{-1: 'All', -2: 'URGENT'}}
            }

        }
        if dict_name in dictionaries:
            if dict_type in dictionaries[dict_name]:
                return {'msg': dictionaries[dict_name][dict_type]}, 200
            else:
                return {'msg': 'Dictionary type doesn\'t exist for provided dictionary name.'}, 404
        else:
            return {'msg': 'Dictionary with provided name doesn\'t exist'}, 404

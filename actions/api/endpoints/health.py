from actions.api.restplus import api
from flask_restx import Resource

ns = api.namespace('health', description='Harpia Actions Health')


@ns.route('')
class Health(Resource):

    @staticmethod
    def get():
        """
        Health of Harpia Actions
        """
        return {'status': 'UP'}, 200



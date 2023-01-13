import actions.settings as settings
import logging
import requests
import traceback

logger = logging.getLogger('default')


def get_scenario_by_id(scenario_id):
    url = f"{settings.SCENARIOS_HOST}/{int(scenario_id)}"
    try:
        req = requests.get(
            url=url,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=10
        )
        if req.status_code == 200:
            logger.info(
                msg=f"Requested Scenario by ID - {scenario_id}\nReceived response: {req.json()}"
            )
            return req.json()['msg']
        elif req.status_code == 404:
            logger.info(
                msg=f"Requested Scenario by ID is not found - {scenario_id}\nReceived response: {req.json()}"
            )
            return None
        else:
            logger.error(
                msg=f"Can`t connect to Scenario service to get Scenario by ID - {int(scenario_id)}\nStatus code: {req.status_code}\nJSON: {req.json()}"
            )
            return None
    except Exception as err:
        logger.error(
            msg=f"Error: {err}, stack: {traceback.format_exc()}"
        )
        return None

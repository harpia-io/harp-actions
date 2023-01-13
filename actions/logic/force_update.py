import json
from actions.logic.db import Notifications
import actions.settings as settings
import requests
import logging
import traceback

logger = logging.getLogger('default')


class ForceUpdate(object):
    def __init__(self, alert_ids: list):
        self.alert_ids = alert_ids

    def get_alert_details(self):
        alert_list = []

        for single_alert in self.alert_ids:
            alert = Notifications.obj_exist(single_alert)

            if alert:
                alert_details = {
                    'studio_id': alert.json_self()['studio_id'],
                    'alert_id': single_alert
                }
                alert_list.append(alert_details)

        return alert_list

    def post_update(self):
        data = self.get_alert_details()
        url = f"http://{settings.BRIDGE_HOST}/api/v1/bridge/force_update"
        logger.info(msg=f"Received request to alert force update:\nURL: {url}\nData: {data}")
        try:
            req = requests.post(
                data=json.dumps(data),
                url=url,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10
            )
            if req.status_code == 200:
                logger.info(msg=f"Force update was successful - {data}")
            else:
                logger.error(msg=f"Can`t force update - {data}")
        except Exception as err:
            logger.error(msg=f"Can`t force update - {data}\nError: {err}\nTrace: {traceback.format_exc()}")
            return {'msg': None}

    def main(self):
        self.post_update()


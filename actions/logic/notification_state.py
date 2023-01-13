import logging
from datetime import datetime

logger = logging.getLogger('default')


def time_to_seconds(input_time):
    current_time = int(input_time.strftime('%s'))

    return current_time


def add_notification_state(alert_body):
    try:
        logger.info(f"Alert Details: {alert_body}")
        if time_to_seconds(alert_body['snooze_expire_ts']) < time_to_seconds(datetime.now()) and \
                int(alert_body['acknowledged']) == 0 and \
                int(alert_body['assign_status']) == 0 and \
                time_to_seconds(alert_body['handle_expire_ts']) < time_to_seconds(datetime.now()):
            logger.info("Alert is ACTIVE")
            return 'active'

        elif time_to_seconds(alert_body['snooze_expire_ts']) >= time_to_seconds(datetime.now()):
            logger.info("Alert is SNOOZED")
            return 'snoozed'

        elif int(alert_body['acknowledged']) != 0:
            logger.info("Alert is ACKNOWLEDGED")
            return 'acknowledged'

        elif time_to_seconds(alert_body['downtime_expire_ts']) >= time_to_seconds(datetime.now()):
            logger.info("Alert is in DOWNTIME")
            return 'in_downtime'

        elif int(alert_body['assign_status']) == 1:
            logger.info("Alert is ASSIGNED")
            return 'assigned'

        elif time_to_seconds(alert_body['handle_expire_ts']) >= time_to_seconds(datetime.now()):
            logger.info("Alert is HANDLED")
            return 'handled'

        else:
            logger.error(f'Unknown Alert Notification State: \n{alert_body}')
            return 'active'
    except Exception as err:
        logger.error(msg=f"Can`t update notification state\nAlert Body: {alert_body}\nError: {err}")


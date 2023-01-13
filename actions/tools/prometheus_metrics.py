from prometheus_client import Counter


class Prom:
    notification_statistics_by_alert_name = Counter('notification_statistics_by_alert_name', 'Amount of actions', [
        'alert_id', 'event_name', 'user_name'
    ])

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy import or_, desc
from flask_jwt_extended import create_access_token, create_refresh_token
import datetime
import json
import time
import logging
from actions.app import config
from actions.settings import TOKEN_EXPIRE_HOURS, TIME_LIMIT_ALERTS_HISTORY_DAYS
from actions.logic.common_func import convert_json_simple_to_dict
from actions.logic.jira import GenerateJira

db = SQLAlchemy()
logger = logging.getLogger('default')


class Procedures(db.Model):
    __tablename__ = 'procedures'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.VARCHAR(256), nullable=False)
    studio_id = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    wiki = db.Column(db.String(200), nullable=True)
    requested_by = db.Column(db.String(100), nullable=False)
    thresholds = db.Column(db.String(400))
    tags = db.Column(db.String(200), nullable=False, default='[]')
    procedure_type = db.Column(db.Integer, nullable=False, default=0)
    procedure_review_status = db.Column(db.String(50), default=None)
    alert_fields = db.Column(db.String(1000))
    jira_fields = db.Column(db.String(1000))
    email_fields = db.Column(db.String(1000))
    skype_fields = db.Column(db.String(1000))
    teams_fields = db.Column(db.String(1000))
    telegram_fields = db.Column(db.String(1000))
    pagerduty_fields = db.Column(db.String(1000))
    sms_fields = db.Column(db.String(1000))
    voice_fields = db.Column(db.String(1000))
    whatsapp_fields = db.Column(db.String(1000))

    edited_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    last_update_ts = db.Column(db.DateTime, default=func.now())

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Name %r>' % self.name

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    def json_self(self):
        json_obj = {
            "id": self.id,
            "name": self.name,
            "studio_id": self.studio_id,
            "description": self.description,
            "wiki": self.wiki,
            "requested_by": self.requested_by,
            "thresholds": self.thresholds,
            "tags": convert_json_simple_to_dict(self.tags),
            "procedure_type": self.procedure_type,
            "procedure_review_status": self.procedure_review_status,
            "alert_fields": convert_json_simple_to_dict(self.alert_fields) if self.alert_fields else {},
            "jira_fields": convert_json_simple_to_dict(self.jira_fields) if self.jira_fields else {},
            "email_fields": convert_json_simple_to_dict(self.email_fields) if self.email_fields else {},
            "skype_fields": convert_json_simple_to_dict(self.skype_fields) if self.skype_fields else {},
            "teams_fields": convert_json_simple_to_dict(self.teams_fields) if self.teams_fields else {},
            "telegram_fields": convert_json_simple_to_dict(self.telegram_fields) if self.telegram_fields else {},
            "pagerduty_fields": convert_json_simple_to_dict(self.pagerduty_fields) if self.pagerduty_fields else {},
            "sms_fields": convert_json_simple_to_dict(self.sms_fields) if self.sms_fields else {},
            "voice_fields": convert_json_simple_to_dict(self.voice_fields) if self.voice_fields else {},
            "whatsapp_fields": convert_json_simple_to_dict(self.whatsapp_fields) if self.whatsapp_fields else {},
            "edited_by": self.user.username if self.user.username else "Unknown",
            "last_update_ts": str(self.last_update_ts)
        }
        return json_obj

    def json_self_alert_details(self):
        json_obj = {
            "procedure_id": self.id,
            "procedure_details": self.json_self()
        }
        return json_obj

    @classmethod
    def obj_exist(cls, obj_id):
        return cls.query.filter_by(id=obj_id).one_or_none()

    @classmethod
    def get_scenario_by_name(cls, scenario_name):
        return cls.query.filter_by(name=scenario_name).one_or_none()

    @classmethod
    def obj_exist_with_name_for_studio_id(cls, name, studio_id):
        return cls.query.filter_by(name=name).filter_by(studio_id=studio_id).one_or_none()

    @classmethod
    def search(cls, data):
        result = []
        objects = cls.query
        if data['name']:
            objects = objects.filter_by(name=data['name'])
        if data['pattern']:
            objects = objects.filter(cls.name.like("%{}%".format(data['pattern'])))
        if data['studio_id'] != -1:
            objects = objects.filter_by(studio_id=data['studio_id'])
        if data['tags']:
            objects = objects.filter(cls.tags.like('%"{}"%'.format(data['tags'])))
        if data['procedure_type'] != '-1':
            objects = objects.filter_by(procedure_type=data['procedure_type'])
        if data['procedure_id']:
            objects = objects.filter_by(id=data['procedure_id'])

        y = []
        if data['alert_fields']:
            y.append(cls.alert_fields != '{}')
        if data['email_fields']:
            y.append(cls.email_fields != '{}')
        if data['jira_fields']:
            y.append(cls.jira_fields != '{}')
        if data['skype_fields']:
            y.append(cls.skype_fields != '{}')
        if data['teams_fields']:
            y.append(cls.teams_fields != '{}')
        if data['telegram_fields']:
            y.append(cls.telegram_fields != '{}')
        if data['pagerduty_fields']:
            y.append(cls.pagerduty_fields != '{}')
        if data['sms_fields']:
            y.append(cls.sms_fields != '{}')
        if data['voice_fields']:
            y.append(cls.voice_fields != '{}')
        if data['whatsapp_fields']:
            y.append(cls.whatsapp_fields != '{}')
        if y:
            expression = tuple(y)
            objects = objects.filter(or_(*expression))
        if data['recipient_pattern']:
            expression = tuple([
                cls.alert_fields.like("%{}%".format(data['recipient_pattern'])),
                cls.email_fields.like("%{}%".format(data['recipient_pattern'])),
                cls.jira_fields.like("%{}%".format(data['recipient_pattern'])),
                cls.skype_fields.like("%{}%".format(data['recipient_pattern'])),
                cls.teams_fields.like("%{}%".format(data['recipient_pattern'])),
                cls.telegram_fields.like("%{}%".format(data['recipient_pattern'])),
                cls.pagerduty_fields.like("%{}%".format(data['recipient_pattern'])),
                cls.sms_fields.like("%{}%".format(data['recipient_pattern'])),
                cls.voice_fields.like("%{}%".format(data['recipient_pattern'])),
                cls.whatsapp_fields.like("%{}%".format(data['recipient_pattern']))
            ])
            objects = objects.filter(or_(*expression))

        for item in objects.all():
            if item.procedure_review_status:
                jira_obj = GenerateJira(jira_id=item.procedure_review_status)
                if jira_obj.check_jira_status():
                    item.procedure_review_status = None
                    item.save_to_db()

            result.append({
                'id': item.id,
                'name': item.name,
                'studio_id': item.studio_id,
                'procedure_review_status': item.procedure_review_status,
                "alert_fields": True if item.alert_fields != '{}' else False,
                "jira_fields": True if item.jira_fields != '{}' else False,
                "email_fields": True if item.email_fields != '{}' else False,
                "skype_fields": True if item.skype_fields != '{}' else False,
                "teams_fields": True if item.teams_fields != '{}' else False,
                "telegram_fields": True if item.telegram_fields != '{}' else False,
                "pagerduty_fields": True if item.pagerduty_fields != '{}' else False,
                "sms_fields": True if item.sms_fields != '{}' else False,
                "voice_fields": True if item.voice_fields != '{}' else False,
                "whatsapp_fields": True if item.whatsapp_fields != '{}' else False,
                "edited_by": item.user.username,
                "last_update_ts": str(item.last_update_ts),
            })

        return result

    @classmethod
    def direct_search(cls, pattern, studio_ids, tag):
        result = {}
        objects = cls.query
        if pattern:
            objects = objects.filter(cls.name.like("%{}%".format(pattern)))
        if studio_ids:
            objects = objects.filter(cls.studio_id.in_(studio_ids))
        if tag:
            objects = objects.filter(cls.tags.like('%"{}"%'.format(tag)))
        for item in objects.all():
            result[item.id] = item.name
        return result


class NotificationHistory(db.Model):
    __tablename__ = 'notification_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alert_id = db.Column(db.Integer, nullable=False)
    notification_output = db.Column(db.Text(4294000000))
    notification_action = db.Column(db.String(255), nullable=False)
    comments = db.Column(db.Text(4294000000))
    time_stamp = db.Column(db.TIMESTAMP, default=datetime.datetime.utcnow, nullable=False)

    def json(self):
        return {
            'alert_id': self.alert_id,
            'notification_output': self.notification_output,
            'notification_action': self.notification_action,
            'comments': self.comments,
            'time_stamp': self.time_stamp,
        }

    @classmethod
    def history(cls, obj_id, data=None):
        history = []
        if data == 0:
            history_events = cls.query.filter_by(alert_id=obj_id).filter(
                cls.last_update_ts >= data['from'],
                cls.last_create_ts <= data['to']
            ).order_by(cls.time_stamp.desc()).all()

        else:
            # '1970-01-01 00:00:01'
            time_limit = (datetime.datetime.now() - datetime.timedelta(days=TIME_LIMIT_ALERTS_HISTORY_DAYS))\
                .strftime("%Y/%m/%d %H:%M:%S")
            history_events = cls.query.filter_by(alert_id=obj_id).filter(cls.time_stamp >= time_limit)\
                .order_by(cls.time_stamp.desc()).all()
        if history_events:
            not_comments_count = 0
            for history_event in history_events:
                if not history_event.comments:
                    not_comments_count += 1
                    if not_comments_count > 15:
                        continue
                    comments = {}
                else:
                    comments = json.loads(history_event.comments)

                history.append({
                    "last_change_ts": int(history_event.time_stamp.strftime('%s')),
                    "notification_action": history_event.notification_action,
                    "notification_output": history_event.notification_output,
                    "comments": comments
                })
        return history

    @classmethod
    def add_new_event(cls, data: dict):
        notification = cls(**data)
        db.session.add(notification)
        db.session.commit()


class Notifications(db.Model):
    __tablename__ = 'notifications'
    __table_args__ = (
        db.UniqueConstraint(
            'name', 'studio', 'ms', 'source', 'object_name', 'ms_alert_id', 'service',
            name='unique_component_commit'
        ),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    studio = db.Column(db.Integer, nullable=False, unique=True)
    ms = db.Column(db.String(40), nullable=False, unique=True)
    source = db.Column(db.String(100), nullable=False, unique=True)
    object_name = db.Column(db.String(100), nullable=False, unique=True)
    service = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.Integer, nullable=False)
    department = db.Column(db.String(100), default=json.dumps([]))
    output = db.Column(db.Text(4294000000))
    additional_fields = db.Column(db.Text(4294000000))
    additional_urls = db.Column(db.Text(4294000000))
    actions = db.Column(db.Text(4294000000))
    description = db.Column(db.Text(4294000000))
    ms_alert_id = db.Column(db.String(100), unique=True)
    recipient_id = db.Column(db.String(255))
    assigned_to = db.Column(db.String(255), default=json.dumps({}))
    action_by = db.Column(db.String(255), default=json.dumps({}))
    image = db.Column(db.Text(4294000000))
    total_duration = db.Column(db.BigInteger, default=0, nullable=False)
    notification_status = db.Column(db.Integer, default=0, nullable=False)
    assign_status = db.Column(db.Integer, default=0, nullable=False)
    snooze_expire_ts = db.Column(db.TIMESTAMP, default='1970-01-01 00:00:01', nullable=False)
    sticky = db.Column(db.Integer, default=0, nullable=False)
    procedure_id = db.Column(db.Integer, nullable=False)
    last_update_ts = db.Column(db.TIMESTAMP, default=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), onupdate=datetime.datetime.utcnow, nullable=False)
    last_create_ts = db.Column(db.TIMESTAMP, default=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), nullable=False)

    def json_self(self):
        return {
            'id': self.id,
            'name': self.name,
            'studio': config['studios_dict'][str(self.studio)],
            'studio_id': self.studio,
            'monitoring_system': self.ms,
            'source': self.source,
            'object': self.object_name,
            'service': self.service,
            'severity': self.severity,
            'department': convert_json_simple_to_dict(self.department),
            'output': convert_json_simple_to_dict(self.output),
            'additional_fields': convert_json_simple_to_dict(self.additional_fields),
            'additional_urls': convert_json_simple_to_dict(self.additional_urls),
            'actions': convert_json_simple_to_dict(self.actions),
            'description': self.description,
            'image': convert_json_simple_to_dict(self.image) if self.image else None,
            'recipient_id': self.recipient_id,

            'current_duration': 0 if self.notification_status == 0 else int(time.time() - int(self.last_create_ts.strftime('%s'))),
            'total_duration': self.total_duration + (int(time.time() - int(self.last_create_ts.strftime('%s')))),

            'notification_status': self.notification_status,
            'assign_status': self.assign_status,
            'snooze_expire_ts': int(self.snooze_expire_ts.strftime('%s')),
            'sticky': self.sticky,
            'procedure_id': self.procedure_id,
            'last_update_ts': int(self.last_update_ts.strftime('%s')),
            'assigned_to': convert_json_simple_to_dict(self.assigned_to),
            'action_by': convert_json_simple_to_dict(self.action_by)
        }

    def json_self_short(self):
        return {
            'id': self.id,
            'monitoring_system': self.ms,
            'output': convert_json_simple_to_dict(self.output),
            'additional_fields': convert_json_simple_to_dict(self.additional_fields),
            'additional_urls': convert_json_simple_to_dict(self.additional_urls),
            'description': self.description,
        }

    @classmethod
    def get_notification_by_id(cls, event_id):
        db.session.commit()
        queries = cls.query.filter_by(id=event_id).all()

        return queries

    @classmethod
    def obj_exist(cls, obj_id):
        return cls.query.filter_by(id=obj_id).one_or_none()

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def current_output(cls, obj_id):
        obj = cls.query.filter_by(id=obj_id).one_or_none()
        if obj:
            return convert_json_simple_to_dict(obj.output)['current']
        return ""

    @classmethod
    def update_description(cls, obj_id, description):
        alert = cls.query.filter_by(id=obj_id).one_or_none()
        if alert:
            alert.description = description
            db.session.commit()

    @classmethod
    def update_notification_status(cls, obj_id, notification_status):
        alert = cls.query.filter_by(id=obj_id).one_or_none()
        if alert:
            alert.notification_status = notification_status
            alert.last_update_ts = func.now()
            db.session.commit()
            logger.info(msg=f"Changing notification status of alert.")

    @classmethod
    def active_notifications_for_source(cls, source):
        notifications_list = []
        notifications = cls.query.filter_by(source=source).\
            filter(cls.notification_status != 0).all()
        for notification in notifications:
            notifications_list.append(notification.json_self())
        return notifications_list

    @classmethod
    def active_notifications_for_object(cls, source_object):
        notifications_list = []
        notifications = cls.query.filter_by(object_name=source_object).\
            filter(cls.notification_status != 0).all()
        for notification in notifications:
            notifications_list.append(notification.json_self())
        return notifications_list

    @classmethod
    def history(cls, data):
        job_start_ts = time.time()
        notifications_list = []
        env_statistics = {}
        notifications = cls.query.filter(
            cls.last_update_ts >= data['from'],
            cls.last_create_ts <= data['to']
        )

        # if data['notification_type']:
        #     notifications = notifications.filter(cls.notification_type.in_(data['notification_type']))

        if data['environment_id']:
            notifications = notifications.filter(cls.studio.in_(data['environment_id']))

        if data['monitoring_system']:
            notifications = notifications.filter(cls.ms.like("%{}%".format(data['monitoring_system'])))

        if data['scenario_id']:
            notifications = notifications.filter_by(procedure_id=data['procedure_id'])

        if data['service']:
            notifications = notifications.filter(cls.service.like("%{}%".format(data['service'])))

        if data['source']:
            notifications = notifications.filter(cls.source.like("%{}%".format(data['source'])))

        if data['name']:
            notifications = notifications.filter(cls.name.like("%{}%".format(data['name'])))

        if data['object']:
            notifications = notifications.filter(cls.object_name.like("%{}%".format(data['object'])))

        if data['pattern']:
            notifications = notifications\
                .filter(or_(cls.service.like("%{}%".format(data['pattern'])),
                            (cls.source.like("%{}%".format(data['pattern']))),
                            (cls.object_name.like("%{}%".format(data['pattern']))),
                            (cls.name.like("%{}%".format(data['pattern']))),
                            (cls.ms.like("%{}%".format(data['pattern'])))
                            )
                        )

        notifications = notifications.order_by(desc(cls.last_update_ts)).limit(100)

        for notification in notifications.all():
            notifications_list.append(
                {
                    'body': notification.json_self(),
                    'last_change_ts': str(notification.last_update_ts),
                    'notification_id': notification.id,
                    'panel_type': 'single_alert',
                    'notification_status': notification.notification_status
                 }
            )

            if notification.json_self()['studio_id'] in env_statistics:
                env_statistics[notification.json_self()['studio_id']] += 1
            else:
                env_statistics[notification.json_self()['studio_id']] = 1

        logger.info(msg=f"Objects found: {len(notifications_list)}. Time spend (seconds): {int(time.time() - job_start_ts)}. Request: {data}")

        return {"notifications": notifications_list, "notification_statistics": env_statistics}

    @classmethod
    def update_exist_event(cls, event_id: int, data: dict):
        cls.query.filter_by(id=event_id).update(data)
        db.session.commit()


class ActiveAlerts(db.Model):
    __tablename__ = 'active_alerts'
    __table_args__ = (
        db.UniqueConstraint(
            'alert_id',
            name='unique_component_commit'
        ),
    )

    alert_id = db.Column(db.Integer, nullable=False, primary_key=True, unique=True)
    alert_name = db.Column(db.String(255), nullable=False)
    studio = db.Column(db.Integer, nullable=False)
    ms = db.Column(db.String(255), nullable=False)
    source = db.Column(db.String(255), nullable=False)
    service = db.Column(db.String(255), nullable=False)
    object_name = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.Integer, nullable=False)
    notification_type = db.Column(db.Integer, nullable=False, primary_key=True, unique=True)
    notification_status = db.Column(db.Integer, default=0, nullable=False)
    department = db.Column(db.String(255), default=json.dumps([]))
    additional_fields = db.Column(db.Text(4294000000))
    ms_alert_id = db.Column(db.String(255))
    total_duration = db.Column(db.BigInteger, default=0, nullable=False)
    acknowledged = db.Column(db.Integer, default=0, nullable=False)
    assign_status = db.Column(db.Integer, default=0, nullable=False)
    assigned_to = db.Column(db.String(255), default=json.dumps({}))
    action_by = db.Column(db.String(255), default=json.dumps({}))
    consolidation_name = db.Column(db.String(40))
    consolidation_state = db.Column(db.Integer, default=0, nullable=False)
    consolidation_id = db.Column(db.BigInteger, default=0)
    consolidation_ts = db.Column(db.TIMESTAMP, default='1970-01-01 00:00:01', nullable=False)
    created_ts = db.Column(db.TIMESTAMP, nullable=False, default=datetime.datetime.utcnow)
    downtime_expire_ts = db.Column(db.TIMESTAMP, nullable=False, default='1970-01-01 00:00:01')
    snooze_expire_ts = db.Column(db.TIMESTAMP, nullable=False, default='1970-01-01 00:00:01')
    handle_expire_ts = db.Column(db.TIMESTAMP, nullable=False, default='1970-01-01 00:00:01')

    def json(self):
        return {
            'alert_id': self.alert_id,
            'alert_name': self.alert_name,
            'studio': self.studio,
            'ms': self.ms,
            'source': self.source,
            'service': self.service,
            'object_name': self.object_name,
            'severity': self.severity,
            'notification_type': self.notification_type,
            'notification_status': self.notification_status,
            'department': self.department,
            'ms_alert_id': self.ms_alert_id,
            'total_duration': self.total_duration,
            'acknowledged': self.acknowledged,
            'assign_status': self.assign_status,
            'consolidation_name': self.consolidation_name,
            'consolidation_state': self.consolidation_state,
            'consolidation_id': self.consolidation_id,
            'consolidation_ts': self.consolidation_ts,
            'created_ts': self.created_ts,
            'downtime_expire_ts': self.downtime_expire_ts,
            'snooze_expire_ts': self.snooze_expire_ts,
            'handle_expire_ts': self.handle_expire_ts
        }

    @classmethod
    def add_new_event(cls, data: dict):
        notification = ActiveAlerts(**data)
        db.session.add(notification)
        db.session.commit()

    @classmethod
    def get_active_event_by_id(cls, event_id):
        db.session.commit()
        queries = cls.query.filter_by(alert_id=event_id).all()

        return queries

    @classmethod
    def update_exist_event(cls, event_id: int, data: dict):
        cls.query.filter_by(alert_id=event_id).update(data)
        db.session.commit()

    @classmethod
    def obj_exist(cls, obj_id):
        return cls.query.filter_by(alert_id=obj_id).one_or_none()

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def delete_exist_event(cls, event_id: int):
        cls.query.filter_by(alert_id=event_id).delete()
        db.session.commit()
        logger.info(msg=f"Row with alert_id: {event_id} has been removed.")


class UsersDB(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.VARCHAR(50))
    passwd = db.Column(db.VARCHAR(18))
    user_type = db.Column(db.Integer)
    user_schema = db.Column(db.VARCHAR(2000))
    studios = db.Column(db.VARCHAR(300), default='[]')
    notes = db.Column(db.VARCHAR(255))
    last_login_ts = db.Column(db.DateTime, default=func.now())

    user4procedure = db.relationship('Procedures', backref='user', lazy=True)
    # user4actions = db.relationship('ActionsHistory', backref='user', lazy=True)
    # user4app = db.relationship('Applications', backref='user', lazy=True)
    # user4mon_env = db.relationship('MonEnv', backref='user', lazy=True)
    # # user4host = db.relationship('Host', backref='user', lazy=True)
    # user4roles = db.relationship('Roles', backref='user', lazy=True)
    # user4syncer = db.relationship('Syncer', backref='user', lazy=True)

    @classmethod
    def authenticate(cls, username):
        user = cls.query.filter_by(username=username).one_or_none()
        if not user:
            user = UsersDB(
                username=username,
                passwd=0,
                user_type=0,
                user_schema=json.dumps({}),
                notes='Auto added user.'
            )
            db.session.add(user)
            db.session.commit()
        if user.user_type == 7:
            expires = datetime.timedelta(days=10000)
        else:
            expires = datetime.timedelta(hours=TOKEN_EXPIRE_HOURS)
        access_token = create_access_token(identity=username, expires_delta=expires)
        refresh_token = create_refresh_token(identity=username, expires_delta=expires)
        logger.info(msg=f"User login: {username}")
        user.last_login_ts = func.now()
        db.session.commit()
        return {
                   'msg': "Logged in as '{}'".format(username),
                   'access_token': access_token,
                   'refresh_token': refresh_token,
                   'user_type': user.user_type,
                   'user_schema': convert_json_simple_to_dict(user.user_schema)
               }, 200

    # @classmethod
    # def identity(cls, payload):
    #     user_id = payload['identity']
    #     user = cls.query.filter_by(id=user_id)
    #     if user:
    #         return {'id': user.id, 'username': user.username, 'password': user.passwd}
    #     else:
    #         return None

    @classmethod
    def find_by_username(cls, username):
        return cls.query.filter_by(username=username).first()


    # @classmethod
    # def user_group_by_username(cls, username):
    #     return cls.query.filter_by(username=username).first()


    @classmethod
    def user_type_by_id(cls, user_id):
        user = cls.query.filter_by(id=user_id).one_or_none()
        if user:
            return user.user_type
        return 3

    @classmethod
    def find_user_id_by_username(cls, username):
        user = cls.query.filter_by(username=username).one_or_none()
        return user.id if user else 1

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    def json_self(self):
        json_obj = {
            "id": self.id,
            "username": self.username,
            "user_type": self.user_type,
            "user_schema": convert_json_simple_to_dict(self.user_schema),
            "notes": self.notes,
            "last_login_ts": str(self.last_login_ts)
        }
        return json_obj

    @classmethod
    def obj_exist(cls, obj_id):
        return cls.query.filter_by(id=obj_id).one_or_none()


    # @staticmethod
    # def generate_hash(password):
    #     return sha256.hash(password)
    #
    # @staticmethod
    # def verify_hash(password, hash_):
    #     return sha256.verify(password, hash_)


class ActionsHistory(db.Model):
    __tablename__ = 'actions_history'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.VARCHAR(50))
    obj_type = db.Column(db.VARCHAR(50))
    obj_id = db.Column(db.Integer)
    username = db.Column(db.VARCHAR(50))
    comment = db.Column(db.String(1000))
    notes = db.Column(db.String(1000))
    created_ts = db.Column(db.DateTime, default=func.now())

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def add_action_to_history(name, obj_type, obj_id, username, comment, notes):
        object_ = ActionsHistory(
            name=name,
            obj_type=obj_type,
            obj_id=obj_id,
            username=username,
            comment=comment,
            notes=str(notes[:998]),
            created_ts=func.now()
        )
        object_.save_to_db()

    @classmethod
    def add_action_to_history_(cls, data: dict):
        object_ = cls(**data)
        object_.save_to_db()


class Statistics(db.Model):
    __tablename__ = 'statistics'
    __table_args__ = (
        db.UniqueConstraint(
            'alert_id',
            name='unique_component_commit'
        ),
    )

    alert_id = db.Column(db.Integer, nullable=False, primary_key=True)
    close = db.Column(db.Integer, default=0)
    create = db.Column(db.Integer, default=0)
    reopen = db.Column(db.Integer, default=0)
    update = db.Column(db.Integer, default=0)
    change_severity = db.Column(db.Integer, default=0)
    snooze = db.Column(db.Integer, default=0)
    acknowledge = db.Column(db.Integer, default=0)
    assign = db.Column(db.Integer, default=0)
    update_ts = db.Column(db.TIMESTAMP, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    def json(self):
        return {
            'alert_id': self.alert_id,
            'close': self.close,
            'create': self.create,
            'reopen': self.reopen,
            'update': self.update,
            'change_severity': self.change_severity,
            'snooze': self.snooze,
            'acknowledge': self.acknowledge,
            'assign': self.assign,
            'update_ts': self.update_ts
        }

    @classmethod
    def statistic(cls, obj_id):
        alert_stats = cls.query.filter_by(alert_id=obj_id).one_or_none()
        if alert_stats:
            return {'snoozed': alert_stats.snooze, 'reopen': alert_stats.reopen}
        return {'snoozed': 0, 'reopen': 0}

    @classmethod
    def add_new_event(cls, data: dict):
        notification = Statistics(**data)
        db.session.add(notification)
        db.session.commit()

    @classmethod
    def update_counter(cls, event_id: int, data: dict):
        cls.query.filter_by(alert_id=event_id).update(data)
        db.session.commit()

    @classmethod
    def get_counter(cls, event_id: int):
        db.session.commit()
        query = cls.query.filter_by(alert_id=event_id).one_or_none()

        return query


class Assign(db.Model):
    __tablename__ = 'assign'
    __table_args__ = (
        db.UniqueConstraint(
            'alert_id',
            name='unique_component_commit'
        ),
    )

    alert_id = db.Column(db.Integer, nullable=False, primary_key=True)
    notification_type = db.Column(db.Integer, nullable=False)
    notification_fields = db.Column(db.Text(4294000000))
    description = db.Column(db.Text(4294000000))
    resubmit = db.Column(db.Integer, default=0)
    sticky = db.Column(db.Integer, default=0)
    recipient_id = db.Column(db.String(100))
    notification_count = db.Column(db.Integer, default=0)
    time_to = db.Column(db.TIMESTAMP, nullable=False)
    create_ts = db.Column(db.TIMESTAMP, default=datetime.datetime.utcnow, nullable=False)

    def json(self):
        return {
            'alert_id': self.alert_id,
            'notification_type': self.notification_type,
            'notification_fields': json.loads(self.notification_fields),
            'description': self.description,
            'resubmit': self.resubmit,
            'sticky': self.sticky,
            'recipient_id': self.recipient_id,
            'notification_count': self.notification_count,
            'time_to': str(self.time_to),
            'create_ts': str(self.create_ts)
        }

    @classmethod
    def get_assign_info(cls, event_id: int):
        db.session.commit()
        query = cls.query.filter_by(alert_id=event_id).all()

        return query

    @classmethod
    def add_new_event(cls, data: dict):
        notification = cls(**data)
        db.session.add(notification)
        db.session.commit()

    @classmethod
    def delete_exist_event(cls, event_id: int):
        cls.query.filter_by(alert_id=event_id).delete()
        db.session.commit()
        logger.info(msg=f"Row with alert_id: {event_id} has been removed.")

    @classmethod
    def obj_exist(cls, obj_id):
        return cls.query.filter_by(alert_id=obj_id).one_or_none()

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()


class Storage(db.Model):

    id = db.Column(db.Integer, nullable=False, primary_key=True)
    item_type = db.Column(db.VARCHAR(40), nullable=False)
    item_value = db.Column(db.VARCHAR(2000), nullable=False)
    added_by = db.Column(db.VARCHAR(40), nullable=False)
    update_ts = db.Column(db.TIMESTAMP, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    def json(self):
        return {
            'id': self.id,
            'item_type': self.item_type,
            'item_value': self.item_value,
            'added_by': self.added_by,
            'update_ts': self.update_ts
        }

    @classmethod
    def add_new_event(cls, username, item_type: str, data: list):
        for item_value in data:
            obj = cls.query.filter_by(item_type=item_type, item_value=item_value).all()
            if obj:
                continue
            else:
                new_item = cls(
                    item_type=item_type,
                    item_value=item_value,
                    added_by=username
                )
                db.session.add(new_item)
                db.session.commit()

    @classmethod
    def values_by_type(cls, item_type: str):
        values = cls.query.filter_by(item_type=item_type).all()
        if values:
            return [item.item_value for item in values]
        else:
            return []


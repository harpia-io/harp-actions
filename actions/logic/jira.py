import logging
from jira import JIRA
import jira.exceptions as jira_exceptions
import actions.settings as settings
import os

logger = logging.getLogger('default')


class GenerateJira(object):
    def __init__(self, reporter=None, procedure_name='', procedure_id=None, jira_id=None):
        self.reporter = reporter
        self.procedure_name = procedure_name
        self.procedure_id = procedure_id
        self.jira_id = jira_id
        self.watchers = settings.JIRA_WATCHERS
        self.todo_issue_id = settings.JIRA_TODO_ISSUE_ID
        self.component_id = settings.JIRA_ONGOING_TASK_COMPONENT_ID
        self.category = settings.JIRA_STUDIO_SUPPORT_COMPONENT_ID
        self.epic = settings.JIRA_EPIC
        os.environ['https_proxy'] = ''
        os.environ['http_proxy'] = ''
        self.jira = JIRA(
            options={'server': settings.JIRA_SERVER, 'verify': False},
            basic_auth=(settings.JIRA_USER, settings.JIRA_PASSWORD),
            timeout=settings.JIRA_TIMEOUT
        )

    def create_jira(self):
        watchers = f"[~{self.reporter}] " + " ".join([f"[~{watcher}]" for watcher in self.watchers])
        jira_body = {
            'project': {'key': 'JIRAP'},
            'summary': f"New Harp procedure to approve: {self.procedure_name}",
            'description': f""" New procedure is waiting for review: http://harpia.io/#/procedure/edit/{self.procedure_id}
            The task was automatically created by Harp Actions service. Please contact Support team if you have any 
            questions. FYI {watchers} """,
            'customfield_10200': self.epic,
            'customfield_11019': {"id": self.category},
            'components': [{"id": self.component_id}],
            "labels": ['harp_procedure_review'],
            'issuetype': {'name': 'Task'}
        }

        self.jira_id = self.jira.create_issue(fields=jira_body)
        if self.reporter != 'me_auto':
            self.jira.add_watcher(self.jira_id, self.reporter)
        for watcher in self.watchers:
            self.jira.add_watcher(self.jira_id, watcher)

        self.jira.transition_issue(self.jira_id, self.todo_issue_id)

        logger.info(
            msg=f"JIRA has been created: {self.jira_id}. Procedure: http://harpia.io/#/procedure/edit/{self.procedure_id}"
            )

        return str(self.jira_id)

    def check_jira_status(self):
        print(self.jira_id)
        try:
            jira_obj = self.jira.issue(self.jira_id)
            status = jira_obj.fields.status.name
        except jira_exceptions.JIRAError as jira_ext:
            # TODO Add prometheus metric
            if jira_ext.status_code == 404:
                logger.warning(
                    msg=f"The Jira is not found. ID: {self.jira_id}"
                )
                return True
            logger.error(
                msg=f"Jira exception. ID: {self.jira_id}"
            )
            return False
        except Exception as exc:
            # TODO Add prometheus metric
            logger.warning(
                msg=f"The Jira is not found. ID: {self.jira_id}"
            )
            return False
        else:
            return status == 'Closed'



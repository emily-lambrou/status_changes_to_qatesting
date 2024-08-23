import os

repository_owner = os.environ['GITHUB_REPOSITORY_OWNER']
repository_owner_type = os.environ['INPUT_REPOSITORY_OWNER_TYPE']
repository = os.environ['GITHUB_REPOSITORY']
repository_name = repository.split('/')[1]
server_url = os.environ['GITHUB_SERVER_URL']
is_enterprise = True if os.environ.get('INPUT_ENTERPRISE_GITHUB') == 'True' else False
dry_run = True if os.environ.get('INPUT_DRY_RUN') == 'True' else False

gh_token = os.environ['INPUT_GH_TOKEN']
project_number = int(os.environ['INPUT_PROJECT_NUMBER'])
api_endpoint = os.environ.get('GITHUB_GRAPHQL_URL', 'https://github.intranet.unicaf.org/api/graphql')
status_field_name = os.environ['INPUT_STATUS_FIELD_NAME']
notification_type = os.environ['INPUT_NOTIFICATION_TYPE']

if notification_type not in ['comment', 'email']:
    raise Exception(f'Unsupported notification type {notification_type}')


# Initialize the label ID for "QA Testing" as None
qa_testing_label_id = None

#  update qa_testing_label_id value
def set_qa_testing_label_id(label_id):
    global qa_testing_label_id
    qa_testing_label_id = label_id


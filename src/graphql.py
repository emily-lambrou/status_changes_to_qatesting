from pprint import pprint
import logging
import requests
import config
import utils

# Initialize or retrieve previous_statuses from storage (file, database, etc.)
previous_statuses = {}  # Ensure this is correctly initialized or retrieved

logging.debug(f"Previous statuses at start: {previous_statuses}")

def get_repo_issues(owner, repository, status_field_name, after=None, issues=None):
    query = """
    query GetRepoIssues($owner: String!, $repo: String!, $status: String!, $after: String) {
          repository(owner: $owner, name: $repo) {
            issues(first: 100, after: $after, states: [OPEN]) {
              nodes {
                id
                title
                number
                url
                assignees(first:100) {
                  nodes {
                    name
                    email
                    login
                  }
                }
                projectItems(first: 10) {
                  nodes {
                    project {
                      number
                      title
                    }
                    fieldValueByName(name: $status) {
                    # ProjectV2ItemFieldSingleSelectValue represents a single-select dropdown option that will hold the status values such as "QA Testing"
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        id
                        name
                      }
                    }
                  }
                }
              }
              pageInfo {
                endCursor
                hasNextPage
                hasPreviousPage
              }
              totalCount
            }
          }
        }
    """

    variables = {
        'owner': owner,
        'repo': repository,
        'status': status_field_name,
        'after': after
    }

    response = requests.post(
        config.api_endpoint,
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {config.gh_token}"}
    )

    data = response.json()

    if data.get('errors'):
        print(data.get('errors'))
    
    pprint(data)

    repository_data = data.get('data', {}).get('repository', {})
    issues_data = repository_data.get('issues', {})
    pageinfo = issues_data.get('pageInfo', {})
    nodes = issues_data.get('nodes', [])

    if issues is None:
        issues = []
    issues = issues + nodes

    if pageinfo.get('hasNextPage'):
        return get_repo_issues(
            owner=owner,
            repository=repository,
            after=pageinfo.get('endCursor'),
            issues=issues,
            status_field_name=status_field_name
        )

    return issues


def get_project_issues(owner, owner_type, project_number, status_field_name, filters=None, after=None, issues=None, previous_statuses=None):
    if previous_statuses is None:
        previous_statuses = {}

    query = f"""
    query GetProjectIssues($owner: String!, $projectNumber: Int!, $status: String!, $after: String) {{
        {owner_type}(login: $owner) {{
            projectV2(number: $projectNumber) {{
                id
                title
                number
                items(first: 100, after: $after) {{
                    nodes {{
                        id
                        fieldValueByName(name: $status) {{
                            ... on ProjectV2ItemFieldSingleSelectValue {{
                                id
                                name
                            }}
                        }}
                        content {{
                            ... on Issue {{
                                id
                                title
                                number
                                state
                                url
                                assignees(first: 20) {{
                                    nodes {{
                                        name
                                        email
                                        login
                                    }}
                                }}
                            }}
                        }}
                    }}
                    pageInfo {{
                        endCursor
                        hasNextPage
                        hasPreviousPage
                    }}
                    totalCount
                }}
            }}
        }}
    }}
    """

    variables = {
        'owner': owner,
        'projectNumber': project_number,
        'status': status_field_name,
        'after': after
    }

    response = requests.post(
        config.api_endpoint,
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {config.gh_token}"}
    )

    data = response.json()

    if data.get('errors'):
        print(data.get('errors'))

    owner_data = data.get('data', {}).get(owner_type, {})
    project_data = owner_data.get('projectV2', {})
    items_data = project_data.get('items', {})
    pageinfo = items_data.get('pageInfo', {})
    nodes = items_data.get('nodes', [])

    if issues is None:
        issues = []

    if filters:
        filtered_issues = [] 
        for node in nodes:
            issue_content = node.get('content', {})
            if not issue_content:
                continue

            issue_id = issue_content.get('id')
            if not issue_id:
                continue
    
            current_status = node.get('fieldValueByName', {}).get('name')
            previous_status = previous_statuses.get(issue_id, "Unknown")
    
            # Log the current and previous statuses
            logging.debug(f"Issue ID: {issue_id}, Previous Status: {previous_status}, Current Status: {current_status}")

            if filters.get('open_only') and issue_content.get('state') != 'OPEN':
                logging.debug(f"Filtering out issue ID {issue_id} with state {issue_content.get('state')}")
                continue
    
            if previous_status != 'QA Testing' and current_status == 'QA Testing':
                logging.debug(f"Adding issue ID {issue_id} as status changed to 'QA Testing'")
                filtered_issues.append(node)
    
            previous_statuses[issue_id] = current_status
    
        nodes = filtered_issues

    logging.debug(f"Final previous_statuses: {previous_statuses}")

    issues = issues + nodes

    if pageinfo.get('hasNextPage'):
        return get_project_issues(
            owner=owner,
            owner_type=owner_type,
            project_number=project_number,
            after=pageinfo.get('endCursor'),
            filters=filters,
            issues=issues,
            status_field_name=status_field_name,
            previous_statuses=previous_statuses
        )

    return issues


def add_issue_comment(issueId, comment):
    mutation = """
    mutation AddIssueComment($issueId: ID!, $comment: String!) {
        addComment(input: {subjectId: $issueId, body: $comment}) {
            clientMutationId
        }
    }
    """

    variables = {
        'issueId': issueId,
        'comment': comment
    }
    response = requests.post(
        config.api_endpoint,
        json={"query": mutation, "variables": variables},
        headers={"Authorization": f"Bearer {config.gh_token}"}
    )
    if response.json().get('errors'):
        print(response.json().get('errors'))

    return response.json().get('data')

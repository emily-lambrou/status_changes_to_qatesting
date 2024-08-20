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
        return issues or []

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
            issue_content = node.get('content')
            if issue_content is None:
                logging.warning(f'No content found for node: {node}')
                continue

            issue_id = issue_content.get('id')
            if not issue_id:
                logging.warning(f'No ID found in issue content: {issue_content}')
                continue

            # Ensure 'fieldValueByName' is not None
            field_value = node.get('fieldValueByName')
            if field_value is None:
                logging.warning(f'No fieldValueByName found for issue ID {issue_id}')
                continue

            current_status = field_value.get('name')
            if not current_status:
                logging.warning(f'No status found in fieldValueByName for project item: {node}')
                continue

            previous_status = previous_statuses.get(issue_id, "Unknown")
            # Apply the 'open_only' filter if specified
            if filters.get('open_only') and issue_content.get('state') != 'OPEN':
                logging.debug(f"Filtering out issue ID {issue_id} with state {issue_content.get('state')}")
                continue
        
            # Check if status has changed to "QA Testing"
            if previous_status != 'QA Testing' and current_status == 'QA Testing':
                logging.debug(f"Adding issue ID {issue_id} as status changed to 'QA Testing'")
                filtered_issues.append(node)

            # Update the previous status
            previous_statuses[issue_id] = current_status

        # Update nodes with the filtered list
        nodes = filtered_issues

    # Store or use previous_statuses as needed (e.g., save it for the next run)
    logging.debug(f"Final previous_statuses: {previous_statuses}")

    # Append filtered nodes to issues
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

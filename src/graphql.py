from pprint import pprint

import logging
import requests
import config
import utils

# Initialize or retrieve previous_statuses from storage (file, database, etc.)
previous_statuses = {}  

logging.debug(f"Previous statuses: {previous_statuses}")

logging.basicConfig(level=logging.DEBUG)  # Ensure logging is set up

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
   
    # Add debug print statement
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

    try:
        response = requests.post(
            config.api_endpoint,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {config.gh_token}"}
        )
    
        data = response.json()
    
        if 'errors' in data:
            logging.error(f"GraphQL query errors: {data['errors']}")
            return []
          
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
       
                # Get the current issue status
                current_status = node.get('fieldValueByName', {}).get('name')
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
    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return []


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

    try:
        response = requests.post(
            config.api_endpoint,
            json={"query": mutation, "variables": variables},
            headers={"Authorization": f"Bearer {config.gh_token}"}
        )
        data = response.json()

        if 'errors' in data:
            logging.error(f"GraphQL mutation errors: {data['errors']}")

        return data.get('data')

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return {}

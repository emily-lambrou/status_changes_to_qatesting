import requests
import config
import logging
import utils

logging.basicConfig(level=logging.DEBUG)  # Ensure logging is set up

import logging
import requests
import config

logging.basicConfig(level=logging.DEBUG)

def get_repo_labels(owner, repository):
    query = """
    query($owner: String!, $repo: String!) {
        repository(owner: $owner, name: $repo) {
            labels(first: 100) {
                nodes {
                    id
                    name
                }
            }
        }
    }
    """

    variables = {
        'owner': owner,
        'repo': repository
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

        labels = data.get('data', {}).get('repository', {}).get('labels', {}).get('nodes', [])
        logging.debug(f"Retrieved labels: {labels}")
        return labels

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return []

def get_label_id(owner, repository, label_name):
    labels = get_repo_labels(owner, repository)
    for label in labels:
        if label['name'] == label_name:
            logging.debug(f"Found label '{label_name}' with ID: {label['id']}")
            return label['id']
    logging.warning(f"Label '{label_name}' not found.")
    return None

def add_issue_label(issue_id, label_ids):
    mutation = """
    mutation AddIssueLabel($issueId: ID!, $labelIds: [ID!]!) {
        addLabelsToLabelable(input: {labelableId: $issueId, labelIds: $labelIds}) {
            labelable {
                ... on Issue {
                    id
                    labels(first: 10) {
                        edges {
                            node {
                                name
                            }
                        }
                    }
                }
            }
        }
    }
    """

    variables = {
        'issueId': issue_id,
        'labelIds': label_ids
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
            return None

        logging.debug(f"Mutation result: {data}")
        return data.get('data')

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None


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
                    assignees(first: 100) {
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
        logging.error(f"GraphQL query errors: {data.get('errors')}")
    
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

def get_project_issues(owner, owner_type, project_number, status_field_name, filters=None, after=None, issues=None):
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

                field_value = node.get('fieldValueByName')
                current_status = field_value.get('name') if field_value else None
       
                if filters.get('open_only') and issue_content.get('state') != 'OPEN':
                    logging.debug(f"Filtering out issue ID {issue_id} with state {issue_content.get('state')}")
                    continue
       
                if current_status == 'QA Testing':
                    if not utils.check_comment_exists(issue_id, "This issue is ready for testing. Please proceed accordingly in 15 minutes."):
                        logging.debug(f"Adding issue ID {issue_id} as status is 'QA Testing'")
                        add_issue_comment(issue_id, "This issue is ready for testing. Please proceed accordingly in 15 minutes.")
                        logging.info(f"Comment added to issue {issue_id}")
                        filtered_issues.append(node)
                    else:
                        logging.info(f"Comment already exists for issue {issue_id}")

            nodes = filtered_issues
    
        issues = issues + nodes
    
        if pageinfo.get('hasNextPage'):
            return get_project_issues(
                owner=owner,
                owner_type=owner_type,
                project_number=project_number,
                after=pageinfo.get('endCursor'),
                filters=filters,
                issues=issues,
                status_field_name=status_field_name
            )
    
        return issues
    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return []

def add_issue_comment(issue_id, comment):
    mutation = """
    mutation AddIssueComment($issueId: ID!, $comment: String!) {
        addComment(input: {subjectId: $issueId, body: $comment}) {
            clientMutationId
        }
    }
    """

    variables = {
        'issueId': issue_id,
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

def get_issue_comments(issue_id):
    query = """
    query GetIssueComments($issueId: ID!, $afterCursor: String) {
        node(id: $issueId) {
            ... on Issue {
                comments(first: 100, after: $afterCursor) {
                    nodes {
                        body
                        createdAt
                        author {
                            login
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        }
    }
    """

    variables = {
        'issueId': issue_id,
        'afterCursor': None
    }

    all_comments = []

    try:
        while True:
            response = requests.post(
                config.api_endpoint,
                json={"query": query, "variables": variables},
                headers={"Authorization": f"Bearer {config.gh_token}"}
            )

            data = response.json()

            if 'errors' in data:
                logging.error(f"GraphQL query errors: {data['errors']}")
                break

            comments_data = data.get('data', {}).get('node', {}).get('comments', {})
            comments = comments_data.get('nodes', [])
            all_comments.extend(comments)

            pageinfo = comments_data.get('pageInfo', {})
            if not pageinfo.get('hasNextPage'):
                break

            # Set the cursor for the next page
            variables['afterCursor'] = pageinfo.get('endCursor')

        return all_comments

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return []

import config
from logger import logger
import graphql

def prepare_issue_comment(issue: dict, assignees: dict):
    """
    Prepare the comment from the given arguments and return it
    """

    comment = ''
    if assignees:
        for assignee in assignees:
            comment += f'@{assignee["login"]} '
    else:
        logger.info(f'No assignees found for issue #{issue["number"]}')

    comment += f'This issue is ready for testing. Please proceed accordingly.'
    logger.info(f'Issue {issue["title"]} | {comment}')

    return comment


def check_specific_bot_comment_exists(issue_id):
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
                            isBot  # Check if the comment is from a bot
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
        'afterCursor': None  # Start from the beginning (no cursor)
    }

    try:
        while True:  # Keep fetching until all pages of comments are retrieved
            response = requests.post(
                config.api_endpoint,
                json={"query": query, "variables": variables},
                headers={"Authorization": f"Bearer {config.gh_token}"}
            )

            data = response.json()

            if 'errors' in data:
                logging.error(f"GraphQL query errors: {data['errors']}")
                break

            # Get the comments data
            comments_data = data.get('data', {}).get('node', {}).get('comments', {})
            comments = comments_data.get('nodes', [])

            # Loop through comments and check for the specific bot comment
            for comment in comments:
                if comment['author'].get('isBot') and "This issue is ready for testing. Please proceed accordingly." in comment['body']:
                    return True  # Return True if the specific comment from a bot is found

            # Check if there are more pages of comments to load
            page_info = comments_data.get('pageInfo', {})
            if not page_info.get('hasNextPage'):
                break  # If there are no more pages, exit the loop

            # Update the cursor to fetch the next page
            variables['afterCursor'] = page_info['endCursor']

        return False  # Return False if the comment wasn't found after checking all pages

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return False









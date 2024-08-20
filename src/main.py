import json
import os
from logger import logger
import config
import utils
import graphql

# Define the path to the file that will store previous statuses
previous_statuses_file = 'previous_statuses.json'

def initialize_status_file(file_path):
    """Initialize the status file with an empty dictionary."""
    with open(file_path, 'w') as file:
        json.dump({}, file, indent=4)

def load_previous_statuses(file_path):
    """Load the previous statuses from a file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f'Error loading previous statuses: {e}')
            # Initialize the file with an empty dictionary if there is an error
            initialize_status_file(file_path)
            return {}
    else:
        # If file does not exist, create and initialize it
        initialize_status_file(file_path)
        return {}

def save_previous_statuses(file_path, data):
    """Save the updated statuses to a file."""
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
    except IOError as e:
        logger.error(f'Error saving previous statuses: {e}')

def notify_change_status():
    # Load previous statuses from the file
    previous_statuses = load_previous_statuses(previous_statuses_file)

    # Log the previous statuses for debugging
    if not previous_statuses:
        logger.info('No previous statuses found or file is empty.')
    else:
        logger.info(f'Loaded previous statuses: {json.dumps(previous_statuses, indent=4)}')

    # Retrieve issues from GraphQL API
    if config.is_enterprise:
        issues = graphql.get_project_issues(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            status_field_name=config.status_field_name,
            filters={'open_only': True},
            previous_statuses=previous_statuses
        )
    else:
        issues = graphql.get_repo_issues(
            owner=config.repository_owner,
            repository=config.repository_name,
            status_field_name=config.status_field_name
        )

    # Check if there are issues available
    if not issues:
        logger.info('No issues have been found')
        return

    # Initialize an empty dictionary for the updated statuses
    updated_statuses = {}

    # Loop through issues
    for issue in issues:
        # Skip the issues if it's closed
        if issue.get('state') == 'CLOSED':
            continue
        
        # Print the issue object for debugging
        print("Issue object: ", json.dumps(issue, indent=4))

        # Ensure 'content' is present
        issue_content = issue.get('content', {})
        if not issue_content:
            logger.warning(f'Issue object does not contain "content": {issue}')
            continue

        # Ensure 'id' is present in issue content
        issue_id = issue_content.get('id')
        if not issue_id:
            logger.warning(f'Issue content does not contain "id": {issue_content}')
            continue

        # Retrieve the previous status for this issue
        previous_status = previous_statuses.get(issue_id)

        # Get the project item from issue
        project_items = issue.get('projectItems', {}).get('nodes', [])
        if not project_items:
            logger.warning(f'No project items found for issue {issue_id}')
            continue
        
        # Check the first project item
        project_item = project_items[0]
        if not project_item.get('fieldValueByName'):
            logger.warning(f'Project item does not contain "fieldValueByName": {project_item}')
            continue

        # Get the current status
        status = project_item['fieldValueByName'].get('name')
        if not status:
            logger.warning(f'No status found in fieldValueByName for project item: {project_item}')
            continue

        # Get the list of assignees
        assignees = issue_content.get('assignees', {}).get('nodes', [])

        # Handle the status change logic
        if previous_status != 'QA Testing' and status == 'QA Testing':
            if config.notification_type == 'comment':
                comment = utils.prepare_issue_comment(
                    issue=issue_content,
                    assignees=assignees,
                )

                if not config.dry_run:
                    response = graphql.add_issue_comment(issue_id, comment)
                    if response.get('errors'):
                        logger.error(f'Error adding comment to issue {issue_id}: {response.get("errors")}')
                    else:
                        logger.info(f'Comment added to issue #{issue_content.get("number")} ({issue_id})')

            elif config.notification_type == 'email':
                subject, message, to = utils.prepare_issue_email_message(
                    issue=issue_content,
                    assignees=assignees
                )

                if not config.dry_run:
                    utils.send_email(
                        from_email=config.smtp_from_email,
                        to_email=to,
                        subject=subject,
                        html_body=message
                    )

                    logger.info(f'Email sent to {to} for issue #{issue_content.get("number")}')

        # Update the dictionary with the current status
        updated_statuses[issue_id] = status

    # Save the updated statuses to the file
    save_previous_statuses(previous_statuses_file, updated_statuses)

def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    notify_change_status()

if __name__ == "__main__":
    main()

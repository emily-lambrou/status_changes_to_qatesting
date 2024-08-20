from logger import logger
import json
import os
import requests
import config
import utils
import graphql

# Define the path to the file that will store previous statuses
previous_statuses_file = 'previous_statuses.json'

def load_previous_statuses(file_path):
    """Load the previous statuses from a file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f'Error loading previous statuses: {e}')
            return {}
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

    # Print the loaded previous statuses for debugging
    print("Previous statuses: ", json.dumps(previous_statuses, indent=4))

    if config.is_enterprise:
        # Get the issues
        issues = graphql.get_project_issues(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            status_field_name=config.status_field_name,
            filters={'open_only': True},
            previous_statuses=previous_statuses
        )
    else:
        # Get the issues
        issues = graphql.get_repo_issues(
            owner=config.repository_owner,
            repository=config.repository_name,
            status_field_name=config.status_field_name
        )

    # Check if there are issues available
    if not issues:
        logger.info('No issues have been found')
        return

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
        
        previous_status = previous_statuses.get(issue_id, "Unknown")
        current_status = None

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

        current_status = project_item['fieldValueByName'].get('name')
        if not current_status:
            logger.warning(f'No status found in fieldValueByName for project item: {project_item}')
            continue

        # Handle the status change logic
        if previous_status != 'QA Testing' and current_status == 'QA Testing':
            if config.notification_type == 'comment':
                comment = utils.prepare_issue_comment(
                    issue=issue_content,
                    assignees=issue_content.get('assignees', {}).get('nodes', []),
                )

                if not config.dry_run:
                    graphql.add_issue_comment(issue_id, comment)
                
                logger.info(f'Comment added to issue #{issue_content.get("number")} ({issue_id})')

            elif config.notification_type == 'email':
                subject, message, to = utils.prepare_issue_email_message(
                    issue=issue_content,
                    assignees=issue_content.get('assignees', {}).get('nodes', [])
                )

                if not config.dry_run:
                    utils.send_email(
                        from_email=config.smtp_from_email,
                        to_email=to,
                        subject=subject,
                        html_body=message
                    )

                    logger.info(f'Email sent to {to} for issue #{issue_content.get("number")}')

        # Update previous_statuses with the current status
        previous_statuses[issue_id] = current_status

    # Save the updated statuses to the file
    save_previous_statuses(previous_statuses_file, previous_statuses)

def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    notify_change_status()
       
if __name__ == "__main__":
    main()

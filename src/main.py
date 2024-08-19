from logger import logger
import config
import utils
import graphql
import json
import os

def load_previous_statuses(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f'Error loading previous statuses: {e}')
            return {}
    return {}

def save_previous_statuses(file_path, data):
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
    except IOError as e:
        logger.error(f'Error saving previous statuses: {e}')

previous_statuses_file = 'previous_statuses.json'

def notify_change_status():
    # Load previous statuses from the file
    previous_statuses = load_previous_statuses(previous_statuses_file)

    # Print the loaded previous statuses for debugging
    print("Loaded previous statuses: ", json.dumps(previous_statuses, indent=4))
    
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
        if config.is_enterprise:
            projectItem = issue
            issue = issue['content']
        else:
            projectNodes = issue['projectItems']['nodes']

            if not projectNodes:
                continue

            # Check if the desired project is assigned to the issue
            projectItem = next((entry for entry in projectNodes if entry['project']['number'] == config.project_number), None)

        # The fieldValueByName contains the name/value for the Status Field
        if not projectItem.get('fieldValueByName'):
            continue

        # Get the current status value
        current_status = projectItem['fieldValueByName'].get('name')

        # Get the list of assignees
        assignees = issue.get('assignees', {}).get('nodes', [])

        # Retrieve the previous status
        previous_status = previous_statuses.get(issue['id'])

        # Handle the status change logic
        if previous_status != 'QA Testing' and current_status == 'QA Testing':
            if config.notification_type == 'comment':
                comment = utils.prepare_issue_comment(
                    issue=issue,
                    assignees=assignees,
                )

                if not config.dry_run:
                    graphql.add_issue_comment(issue['id'], comment)
                
                logger.info(f'Comment added to issue #{issue["number"]} ({issue["id"]})')

            elif config.notification_type == 'email':
                subject, message, to = utils.prepare_issue_email_message(
                    issue=issue,
                    assignees=assignees
                )

                if not config.dry_run:
                    utils.send_email(
                        from_email=config.smtp_from_email,
                        to_email=to,
                        subject=subject,
                        html_body=message
                    )

                    logger.info(f'Email sent to {to} for issue #{issue["number"]}')

        # Update the previous_statuses with the current status
        previous_statuses[issue['id']] = current_status

    # Save the updated statuses to the file
    save_previous_statuses(previous_statuses_file, previous_statuses)

def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    notify_change_status()
       
if __name__ == "__main__":
    main()

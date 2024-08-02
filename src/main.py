from logger import logger
import config
import utils
import graphql


def notify_changes_status():
    if config.is_enterprise:
        # Get the issues
        issues = graphql.get_project_issues(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            status_field_name=config.status_field_name,
            filters={'open_only': True}
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
        logger.info('No issues has been found')
        return


    # Loop through issues
    for issue in issues:
        if config.is_enterprise:
            projectItem = issue
            issue = issue['content']
        else:
            projectNodes = issue['projectItems']['nodes']

            # If no project is assigned to the issue
            if not projectNodes:
                continue

            # Check if the desire project is assigned to the issue
            projectItem = next((entry for entry in projectNodes if entry['project']['number'] == config.project_number),
                               None)

        # The fieldValueByName contains the status for the Status Field
        if not projectItem['fieldValueByName']:
            continue

        # Get the status value and convert it to date object
        status = projectItem["fieldValueByName"]["status"]
    
        # Get the list of assignees
        assignees = issue['assignees']['nodes']

        # Handle notification type
        if config.notification_type == 'comment':
            # Prepare the notification content
            comment = utils.prepare_issue_comment(
                issue=issue,
                assignees=assignees
            )

            if not config.dry_run:
                # Add the comment to the issue
                graphql.add_issue_comment(issue['id'], comment)

            logger.info(f'Comment added to issue #{issue["number"]} ({issue["id"]}) with status changes to QA Testing')
        elif config.notification_type == 'email':
            # Prepare the email content
            subject, message, to = utils.prepare_issue_email_message(
                issue=issue,
                assignees=assignees
            )

            if not config.dry_run:
                # Send the email
                utils.send_email(
                    from_email=config.smtp_from_email,
                    to_email=to,
                    subject=subject,
                    html_body=message
                )

            logger.info(f'Email sent to {to} for issue #{issue["number"]} with status changes to QA Testing')


def notify_missing_duedate():
    issues = graphql.get_project_issues(
        owner=config.repository_owner,
        owner_type=config.repository_owner_type,
        project_number=config.project_number,
        status_field_name=config.status_field_name,
        filters={'empty_duedate': True, 'open_only': True}
    )

    # Check if there are issues available
    if not issues:
        logger.info('No issues has been found')
        return

    for projectItem in issues:
        # node_id for status: MDEzOlByb2plY3RDb2x1bW4zNjk=
        # if projectItem['id'] != 'MDEzOlByb2plY3RDb2x1bW4zNjk=':
        #     continue
        issue = projectItem['content']

        # Get the list of assignees
        assignees = issue['assignees']['nodes']

        if config.notification_type == 'comment':
            # Prepare the notification content
            comment = utils.prepare_issue_comment(
                issue=issue,
                assignees=assignees,
            )

            if not config.dry_run:
                # Add the comment to the issue
                graphql.add_issue_comment(issue['id'], comment)

            logger.info(f'Comment added to issue #{issue["number"]} ({issue["id"]})')
        elif config.notification_type == 'email':
            # Prepare the email content
            subject, message, to = utils.prepare_issue_email_message(
                issue=issue,
                assignees=assignees
            )

            if not config.dry_run:
                # Send the email
                utils.send_email(
                    from_email=config.smtp_from_email,
                    to_email=to,
                    subject=subject,
                    html_body=message
                )
            logger.info(f'Email sent to {to} for issue #{issue["number"]}')


def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    if config.notify_for == 'expiring_issues':
        notify_expiring_issues()
    else:
        raise Exception('Unsupported value for argument \'notify_for\'')


if __name__ == "__main__":
    main()

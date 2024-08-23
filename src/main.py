from logger import logger
import json
import config
import graphql
import utils

def notify_change_status():
    if config.is_enterprise:
        issues = graphql.get_project_issues(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            status_field_name=config.status_field_name,
            filters={'open_only': True}
        )
    else:
        issues = graphql.get_repo_issues(
            owner=config.repository_owner,
            repository=config.repository_name,
            status_field_name=config.status_field_name
        )

    if not issues:
        logger.info('No issues have been found')
        return

    for issue in issues:
        if issue.get('state') == 'CLOSED':
            continue
        
        print("Issue object: ", json.dumps(issue, indent=4))

        issue_content = issue.get('content', {})
        if not issue_content:
            logger.warning(f'Issue object does not contain "content": {issue}')
            continue

        issue_id = issue_content.get('id')
        if not issue_id:
            logger.warning(f'Issue content does not contain "id": {issue_content}')
            continue

        project_items = issue.get('projectItems', {}).get('nodes', [])
        if not project_items:
            logger.warning(f'No project items found for issue {issue_id}')
            continue
        
        project_item = project_items[0]
        if not project_item.get('fieldValueByName'):
            logger.warning(f'Project item does not contain "fieldValueByName": {project_item}')
            continue

        current_status = project_item['fieldValueByName'].get('name')
        if not current_status:
            logger.warning(f'No status found in fieldValueByName for project item: {project_item}')
            continue

        if current_status == 'QA Testing':
            comment_text = "This issue is ready for testing. Please proceed accordingly."
            
            if not utils.check_comment_exists(issue_id, comment_text):
                if config.notification_type == 'comment':
                    comment = utils.prepare_issue_comment(
                        issue=issue_content,
                        assignees=issue_content.get('assignees', {}).get('nodes', []),
                    )

                    if not config.dry_run:
                        comment_result = graphql.add_issue_comment(issue_id, comment)
                        if comment_result:
                            logger.info(f'Comment added to issue #{issue_content.get("number")} ({issue_id})')
                        else:
                            logger.error(f'Failed to add comment to issue #{issue_content.get("number")} ({issue_id})')

                        label_id = config.qa_testing_label_id
                        if not label_id:
                            label_id = graphql.get_label_id(
                                owner=config.repository_owner,
                                repository=config.repository_name,
                                label_name="QA Testing"
                            )
                            if label_id:
                                # Store label_id in config if necessary
                                config.qa_testing_label_id = label_id
                            else:
                                logger.error('Label ID for "QA Testing" could not be found.')
                                continue

                        if not config.dry_run:
                            label_result = graphql.add_issue_label(issue_id, [label_id])
                            if label_result:
                                logger.info(f'Label "QA Testing" added to issue #{issue_content.get("number")} ({issue_id})')
                            else:
                                logger.error(f'Failed to add label "QA Testing" to issue #{issue_content.get("number")} ({issue_id})')
            else:
                logger.info(f'Comment already exists for issue #{issue_content.get("number")} ({issue_id})')

def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    notify_change_status()

if __name__ == "__main__":
    main()

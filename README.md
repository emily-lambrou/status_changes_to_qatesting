# Status changes to "QA Testing" Notifications

GitHub doesn't provide a built-in way to send notifications if the status is changing. This
GitHub Action aims to address this by allowing you to manage the changes within a central GitHub project.

## Introduction

This GitHub Action allows you to manage status changes for issues in a central GitHub project. It integrates with a custom
text field (status) that you can add to your GitHub project board. 

There are two ways to send notifications:
1. With comments: Everyone which is subscribed to the issue will receive email notification when comment is placed.
2. With emails: Assignees will receive email directly from the action. 

### Prerequisites

Before you can start using this GitHub Action, you'll need to ensure you have the following:

1. A GitHub repository where you want to enable this action.
2. A GitHub project board with a custom status field added.
3. A Token (Classic) with permissions to repo:*, read:user, user:email, read:project

### Inputs

| Input                                | Description                                                                                      |
|--------------------------------------|--------------------------------------------------------------------------------------------------|
| `gh_token`                           | The GitHub Token                                                                                 |
| `project_number`                     | The project number                                                                               |
| `notify_for`                         | The type of the notification (expiring_issues or missing_duedate) are about to sent. Default is `expiring_issues` |
| `duedate_field_name` _(optional)_    | THe duedate field name. The default is `Due Date`                                                |
| `notification_type` _(optional)_     | The notification type. Available values are `comment` and `email`. Default is `comment`          |
| `enterprise_github` _(optional)_     | `True` if you are using enterprise github and false if not. Default is `False`                   |
| `repository_owner_type` _(optional)_ | The type of the repository owner (oragnization or user). Default is `user`                       |
| `smtp_server` _(optional)_           | The mail server address. `Required` only when `notification_type` is set to `email`              |
| `smtp_port` _(optional)_             | The mail server port. `Required` only when `notification_type` is set to `email`                 |
| `smtp_username` _(optional)_         | The mail server username. `Required` only when `notification_type` is set to `email`             |
| `smtp_password` _(optional)_         | The mail server password. `Required` only when `notification_type` is set to `email`             |
| `smtp_from_email` _(optional)_       | The mail from email address. `Required` only when `notification_type` is set to `email`          |
| `dry_run` _(optional)_               | `True` if you want to enable dry-run mode. Default is `False`                                    |



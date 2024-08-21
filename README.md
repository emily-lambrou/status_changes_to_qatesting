# Status changes to "QA Testing" Notifications

GitHub doesn't provide a built-in way to send notifications if the status is changing. This
GitHub Action aims to address this by allowing you to manage the changes within a central GitHub project.
For this case I only focus to the "QA Testing" status. However, if you are interested for any other status, 
you can modify it.

## Introduction

This GitHub Action allows you to manage status changes for issues in a central GitHub project. It integrates with a custom
text field (status) that you can add to your GitHub project board. 

In this workflow you can use comments to send notifications. You can tag a specific assignee in order to recieve
an email regarding the change of the status to "QA Testing" in order to proceed with the testing. Therefore a comment 
will be added to the issue, tagging a specific assignee. This action will trigger an email notification to that assignee. 
For this workflow, the comment will be directed to the assignee with the username "@tantoniou." However, you can modify this to tag any assignee you choose.

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
| `status_field_name` _(optional)_     | The status field name. The default is `Status`                                                   |
| `notification_type` _(optional)_     | The notification type. Default is `comment`          |
| `enterprise_github` _(optional)_     | `True` if you are using enterprise github and false if not. Default is `False`                   |
| `repository_owner_type` _(optional)_ | The type of the repository owner (oragnization or user). Default is `user`                       |
| `dry_run` _(optional)_               | `True` if you want to enable dry-run mode. Default is `False`                                    |


### Examples

#### Expiring Issues With Comment
To set up QA Testing status change comment notifications, you'll need to create or update a GitHub Actions workflow in your repository. Below is
an example of a workflow YAML file:

```yaml
name: 'Notify Status Change to QA Testing with Comment'

on:
  schedule:
    - cron: '0 1 * * *'
  workflow_dispatch:

jobs:
  notify_status_change::
    runs-on: ubuntu-latest
    steps:
      - name: Check status change and add a comment
        uses: emily-lambrou/status_changes_to_qatesting@latest
        with:
          gh_token: ${{ secrets.GITHUB_TOKEN }}
          project_number: 2
          status_field_name: "Status"
          notification_type: "comment"
```

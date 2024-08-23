# Status changes to "QA Testing"

GitHub doesn't provide a built-in way to send notifications if the status is changing. This
GitHub Action aims to address this by allowing you to manage the changes within a central GitHub project.

In this case I only focused to the "QA Testing" status. However, if you are interested for any other statuses, 
you can modify it.

## Introduction

This GitHub Action allows you to manage status changes for issues in a central GitHub project. It integrates with a custom
text field (status) that you can add to your GitHub project board. 

In this workflow you can use comments to send notifications. You can tag a specific assignee in order to recieve
an email regarding the change of the status to "QA Testing" in order to proceed with the testing. Therefore a comment 
will be added to the issue, tagging a specific assignee. This action will trigger an email notification to that assignee
and also a label "QA Testing (Status)" will be added in the issue. Ensure the label "QA Testing (Status) exists in the repository.
Labels need to be created in the repository before they can be applied to issues. You can also change the text for your specific needs
by also changing the text in the code.


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

#### Status changes to "QA Testing" With Comment
To set up QA Testing status change comment notifications, you'll need to create or update a GitHub Actions workflow in your repository. Below is
an example of a workflow YAML file:

```yaml
name: Testing Status

# Runs every minute
on:
  schedule:
    - cron: '* * * * *'
  workflow_dispatch:

jobs:
  check_status:
    runs-on: self-hosted

    steps:
      # Checkout the code to be used by runner
      - name: Checkout code
        uses: actions/checkout@v3


      # Check for status changes
      - name: Check for status changes
        uses: emily-lambrou/status_changes_to_qatesting@v1.3
        with:
          dry_run: ${{ vars.DRY_RUN }}           
          gh_token: ${{ secrets.GH_TOKEN }}      
          project_number: ${{ vars.PROJECT_NUMBER }} 
          enterprise_github: 'True'
          repository_owner_type: organization
        
```

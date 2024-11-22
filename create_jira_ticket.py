#!/usr/bin/env python3

import os
from jira import JIRA
import argparse
from pprint import pprint


def main(args):
    # JIRA API URL
    if not args.jira_api_url:
        raise ValueError("Must set JIRA_API_URL environment variable")
    jira_api_url = args.jira_api_url

    # JIRA API token
    jira_api_token = args.jira_api_token
    user = args.jira_user
    if not jira_api_token:
        raise ValueError("Must set JIRA_API_TOKEN environment variable")

    jira_client = JIRA(jira_api_url, basic_auth=(user, jira_api_token))

    # Title -> Link mapping for JIRA. Default to title == link generically.
    link_map = {l: l for l in args.link}
    # Leave <TODO> as a reminder for creator to fill in more details if needed
    description = "Description: <TODO>\n\n"
    if args.issue:        
        github_url = args.github_html_url
        github_title = args.github_issue_title
        with open(args.github_issue_body_file, 'r') as file:
            description = file.read().replace('\n', '')
            print(f"Description: {description}")
        link_map["Github Issue"] = github_url

        if not args.title:
            print(f"Setting JIRA title to Github issue title: {github_title}")
            args.title = github_title + f" #{args.issue}"

    # Append all links/references at the bottom of description for easy viewing
    if args.link:
        description += "\nReferences\n"
        for url in args.link:
            description += f"- {url}\n"

    fields = {
        "project": {"key": args.jira_board},
        "summary": args.title,
        "description": description,
        "issuetype": {"name": args.type},
        "components": [{"name": component} for component in args.component],
    }
    print("Creating ticket with fields:")
    pprint(fields)

    if args.dry_run:
        key = "FAKE-KEY"
    else:
        # TODO: Can we detect if a duplicately titled ticket exists and skip?
        # Create JIRA ticket
        ticket = jira_client.create_issue(fields=fields)
        key = ticket.key

    # Print this immediately after creation in case an error happens later
    # so ticket can be found and fixed manually.
    print(f"JIRA Ticket created at URL: {jira_api_url}/browse/{key}")

    # Link the JIRA ticket to the specified links and issues
    for title, url in link_map.items():
        link_object = {"url": url, "title": title}
        print(f"Adding link to {key}: {link_object}")
        if args.dry_run:
            continue

        jira_client.add_simple_link(issue=key, object=link_object)

    print("Done! 🎉")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a JIRA ticket from a GitHub issue"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without actually creating a JIRA ticket for testing",
    )

    github_group = parser.add_argument_group(
        "github",
        "Info to automatically scrape title/description details from a GitHub issue",
    )
    # TODO: Can we just take a fully qualified issue link and figure it out?
    # ex: https://github.com/triton-inference-server/server/issues/7191
    github_group.add_argument(
        "--issue", type=int, help="GitHub issue number to parse and link"
    )
    github_group.add_argument(
        "--repo",
        type=str,
        help="Triton Server Github Repo to associate with the issue number",
        default="server",
    )
    # github_group.add_argument(
    #     "--github-api-token",
    #     type=str,
    #     help="GitHub API token",
    #     default=os.environ.get("GH_API_TOKEN"),
    # )
    github_group.add_argument(
        "--github-html-url",
        type=str,
        help="GitHub HTML URL",
    )
    github_group.add_argument(
        "--github-issue-title",
        type=str,
        help="GitHub issue title",
    )
    github_group.add_argument(
        "--github-issue-body-file",
        type=str,
        help="The file that contains the contents of the issue",
    )

    jira_group = parser.add_argument_group("jira", "Settings to tweak on JIRA ticket")
    jira_group.add_argument(
        "--title",
        type=str,
        help="JIRA ticket title. Will default to GitHub issue title if --issue provided and --title is omitted.",
    )
    jira_group.add_argument(
        "--type", type=str, default="Story", choices=["Bug", "Story"], help="Issue type"
    )
    jira_group.add_argument(
        "--component",
        default=[],
        action="append",
        choices=[
            "Python Backend",
            "Backend",
            "Server",
            "Client",
            "Platforms",
            "Caching",
            "Triton CLI",
            "GitHub",
        ],
        help="Component name, may be specified multiple times",
    )
    jira_group.add_argument(
        "--jira-board",
        type=str,
        choices=["TMA", "DLIS", "TPRD"],
        help="JIRA board name",
        default="DLIS",
    )
    jira_group.add_argument(
        "--jira_api_url",
        type=str,
        help="JIRA API url",
    )
    jira_group.add_argument(
        "--jira-api-token",
        type=str,
        help="JIRA API token",
        default=os.environ.get("JIRA_API_TOKEN"),
    )
    jira_group.add_argument(
        "--jira-user",
        type=str,
        help="JIRA username",
        default=os.environ.get("JIRA_USER", os.environ.get("USER")),
    )

    misc_group = parser.add_argument_group("misc", "Slack, PRs, Misc References")
    misc_group.add_argument(
        "--link",
        default=[],
        action="append",
        help="Generic link to reference in a JIRA ticket, may be specified multiple times (Slack thread, Github PR comment, etc.)",
    )
    args = parser.parse_args()

    if not any([args.issue, args.title]):
        raise ValueError("A --title must be specified if no --issue is provided.")

    if not any([args.issue, args.link]):
        raise ValueError(
            "Must specify some --link values for context if no --issue is provided."
        )

    main(args)

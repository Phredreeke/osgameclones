"""
This script updates games development status

To run, install from pip:
- pygithub
- python-gitlab

Add environment variables:
- GH_TOKEN
  - https://github.com/settings/tokens?type=beta
  - (see https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token#creating-a-token)
- GL_TOKEN
  - https://gitlab.com/-/profile/personal_access_tokens
  - (see https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html#create-a-personal-access-token)
"""
import os
import re
import yaml

from pathlib import Path
from datetime import datetime, timedelta
from github import Github, GithubException
from gitlab import Gitlab

GL_HOST = 'https://gitlab.com'

GH_REGEX = re.compile(r'https://github.com/([^/]+)/([^/]+)')
GL_REGEX = re.compile(GL_HOST + r'/([^/]+/[^/]+)')

GH_DT_FMT = "%a, %d %b %Y %H:%M:%S %Z"


def main():
    gh = Github(os.environ["GH_TOKEN"])
    gl = Gitlab(GL_HOST, private_token=os.environ["GL_TOKEN"])

    for filename in Path('games').iterdir():
        if not filename.is_file() or filename.suffix != '.yaml':
            continue

        games = yaml.safe_load(open(filename, encoding='utf-8'))
        for game in games:
            repo_url = game.get('repo', '')

            if len(repo_url) == 0 or game.get('development', '') == 'complete':
                continue

            if (latest_commit_date := get_latest_commit_date(repo_url, gh, gl)) is None:
                continue

            diff = datetime.now() - latest_commit_date

            status_original = game.get("development", "unknown")
            if diff < timedelta(weeks=1):
                game['development'] = 'very active'
            elif diff < timedelta(weeks=4):
                game['development'] = 'active'
            elif diff < timedelta(days=365):
                game['development'] = 'sporadic'
            else:
                game['development'] = 'halted'
            if status_original != game["development"]:
                print(f"{game['name']} status should be {game['development']} ({status_original=})")

        # yaml.dump(games, open(filename, 'w', encoding='utf-8'), sort_keys=False)
        # print(filename, 'has been updated')


def is_github_repo(repo):
    return repo.startswith('https://github.')


def is_gitlab_repo(repo):
    return repo.startswith(GL_HOST)


def get_latest_commit_date(repo_url, gh, gl):
    if is_github_repo(repo_url):
        return get_latest_commit_date_for_github(gh, repo_url)
    elif is_gitlab_repo(repo_url):
        return get_latest_commit_date_for_gitlab(gl, repo_url)

    print('The', repo_url, 'repository could not be updated')


def get_latest_commit_date_for_github(gh, repo_url):
    match = re.match(GH_REGEX, repo_url)
    if not match:
        return

    owner, repo = match.groups()
    try:
        gh_repo = gh.get_repo(f"{owner}/{repo}")
        commits = gh_repo.get_commits()
    except GithubException as e:
        print(f'Error getting repo info for {owner}/{repo}: {e}')
        return

    return datetime.strptime(commits[0].last_modified, GH_DT_FMT)


def get_latest_commit_date_for_gitlab(gl, repo_url):
    match = re.match(GL_REGEX, repo_url)

    if not match:
        return

    project_namespace = match.groups()[0]
    project = gl.projects.get(project_namespace)

    last_commit = next(project.commits.list(iterator=True))

    return datetime.strptime(
        ''.join(last_commit.committed_date.rsplit(':', 1)),
        '%Y-%m-%dT%H:%M:%S.%f%z'
    ).replace(tzinfo=None)


if __name__ == "__main__":
    main()

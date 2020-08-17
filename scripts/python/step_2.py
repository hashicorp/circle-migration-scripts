### Step 2 -- run this script locally
### This will clone the project repo from GitHub,
### Copy over our migration script and CI config file,
### And push up a new branch to the repo to trigger our CI job
### The CI job will call ci_migration_script.py

from git import Repo, Actor
from os import listdir, path, getenv, makedirs, getcwd, chdir
from requests import get, post, patch
from shutil import rmtree
from shutil import copy
from pathlib import Path as Path
from functools import reduce

# pip install gitpython

org = getenv("MIGRATION_ORG")
project = getenv("CIRCLE_PROJECT_REPONAME")
github_api_endpoint = 'https://api.github.com'

githubHeaders = { "Authorization": 'token {}'.format(getenv("MIGRATION_GITHUB_TOKEN")),
                   "Accept": "application/vnd.github.v3+json" 
                 }

def createDir(dir):
    """Delete dir if it already exists and create a fresh one"""
    try:
        if path.exists(dir):
            rmtree(dir)
        makedirs(dir)
    except Exception as e:
        raise SystemExit(e)

def cloneRepo(gitClonePath):
    """Clone the repo and checkout the default branch"""
    try:
        repo = Repo.clone_from(
            'https://{}:@github.com/{}/{}.git'.format(getenv("MIGRATION_GITHUB_TOKEN"),\
                 org, project), gitClonePath,
            branch='master'
        )
        print("Cloned the repo {}/{} into {}".format(org, project, gitClonePath))
        return repo
    except Exception as e:
        print(e)
        return SystemExit(e)

def updateClone(gitClonePath):
    """
    Copy scripts/python into the git clone dir
    And copy the circle config file into the git clone dir
    Returns a list of dirs to run `git add` on.
    """
    try:
        createdFiles = []
        currDir = getcwd()
        # Copy scripts/python/ci_migration_script.py into the git clone dir under scripts/python/ci_migration_script.py
        scriptPath = path.join(currDir, "ci_migration_script.py")
        scriptDir = reduce(path.join,[gitClonePath, 'scripts', 'python'])
        makedirs(scriptDir)
        copy(scriptPath, scriptDir)
        print("Copied scripts/python/ci_migration_script.py into {}/scripts/python/ci_migration_script.py".format(gitClonePath))
    
        # Copy example-config/.circleci/config.yml into the git clone dir under .circleci/config.yml
        circlePath = reduce(path.join,[str(Path(getcwd()).parents[1]), 'example-config', '.circleci', 'config.yml'])
        circleDir = reduce(path.join,[gitClonePath, '.circleci'])
        createDir(circleDir)
        copy(circlePath, circleDir)
        print("Copied example-config/.circleci/config.yml into {}/.circleci/config.yml".format(gitClonePath))
        return [circleDir, scriptDir]
    except Exception as e:
        return SystemExit(e)

def commitAndPush(gitClonePath, repo, targetBranch, paths):
    """
    Add, commit, and push changes to a new branch called $targetBranch
    """
    try:
        repo.index.add(paths)
        print("Running `git add .`")
        author = Actor("Migration Bot", "team-rel-eng@hashicorp.com")
        committer = Actor("Migration Bot", "team-rel-eng@hashicorp.com")
        repo.index.commit("Add migration helper script")
        print("Running `git commit`")
        origin = repo.remote()
        repo.create_head(targetBranch)
        origin.push(targetBranch)
        print("Successfully pushed up branch {} to {}/{}".format(targetBranch, org, project))
    except Exception as e:
        return SystemExit(e)

if __name__ == "__main__":
    """ 
    Clone project repo from GitHub.
    Copy over our CircleCI config file and python script, ci_migration_script.py.
    Push up our changes to a new branch to trigger the CI job. 
    This will retrieve the CI secrets for the project, write them to a 
    JSON file, and then upload that file to S3. 
    """ 
    targetBranch = 'get-secrets'
    gitClonePath = reduce(path.join,[getcwd(), 'git-clone', project])
    createDir(gitClonePath)
    repo = cloneRepo(gitClonePath)
    if repo and path.isdir(gitClonePath):
        paths = updateClone(gitClonePath)
        commitAndPush(gitClonePath, repo, targetBranch, paths)

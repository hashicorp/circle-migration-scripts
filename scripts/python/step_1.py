### Step 1 -- run this script locally
### Create required env vars in the Circle-CI On-Prem project, and trigger a CI job.
### WARNING: If env vars with the same names are already set for the project, 
### This script will OVERWRITE them! 

from json import dumps, loads
from git import Repo
from os import listdir, path, getenv, makedirs, getcwd, chdir
from requests import get, post, patch, exceptions
from shutil import rmtree, copy
from pathlib import Path as Path
from functools import reduce

org = getenv("MIGRATION_ORG")
project = getenv("CIRCLE_PROJECT_REPONAME")
tempBranch = 'get-secrets'
gitClonePath = reduce(path.join,[getcwd(), 'git-clone', project])

serverHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Circle-Token': getenv("MIGRATION_CIRCLE_SERVER_TOKEN")
}

envVarList = [ "MIGRATION_CIRCLE_SERVER_TOKEN", "MIGRATION_CIRCLE_CLOUD_TOKEN", "MIGRATION_AWS_ACCESS_KEY_ID",
               "MIGRATION_AWS_SECRET_ACCESS_KEY", "MIGRATION_BUCKET", "MIGRATION_PREFIX", "MIGRATION_ORG",
               "MIGRATION_GITHUB_TOKEN", "MIGRATION_CIRCLE_SERVER_URL_V1", "MIGRATION_CIRCLE_CLOUD_URL_V1",
               "MIGRATION_CIRCLE_CLOUD_URL_V2" ]

def createEnvVar(key):
    """ 
    In the given CircleCI On-Prem project, set a new project-level environment variable
    to help with the migration. These env vars are temporary and will not be migrated to SaaS. 
    """
    val = getenv(key)
    if val is None:
        raise SystemExit('{} is a required env var and must be set'.format(key))

    data = {
        'name': key,
        'value': val
    }
    url = '{}/{}/{}/envvar'.format(getenv("MIGRATION_CIRCLE_SERVER_URL_V1"), org, project)

    try: 
        res = post(url, headers=serverHeaders, data=dumps(data), timeout=3)
        res.raise_for_status()
        print('Successfully set env var {} in project {}'.format(res.json(), project))
    except (exceptions.HTTPError, exceptions.ConnectionError, exceptions.Timeout, exceptions.RequestException) as err:
        raise SystemExit(err)

def setEnvVars():
    """ 
    Iterate over the keys in `envVarList` to set temporary project level environment variables
    for the On-Prem project. These are needed for the migration, but will not be added to SaaS. 
    """
    for key in envVarList:
        createEnvVar(key)

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
        currDir = getcwd()
        # Copy scripts/python/ci_migration_script.py into the git clone dir under scripts/python/ci_migration_script.py
        scriptPath = reduce(path.join,[currDir, 'scripts', 'python', 'ci_migration_script.py'])
        scriptDir = reduce(path.join,[gitClonePath, 'scripts', 'python'])
        makedirs(scriptDir)
        copy(scriptPath, scriptDir)
        print("Copied scripts/python/ci_migration_script.py into {}/scripts/python/ci_migration_script.py".format(gitClonePath))

        # Copy example-config/.circleci/config.yml into the git clone dir under .circleci/config.yml
        configPath = reduce(path.join,[currDir, 'example-config', '.circleci', 'config.yml'])
        configDir = reduce(path.join,[gitClonePath, '.circleci'])
        createDir(configDir)
        copy(configPath, configDir)
        print("Copied example-config/.circleci/config.yml into {}/.circleci/config.yml".format(gitClonePath))
        return [configDir, scriptDir]
    except Exception as e:
        return SystemExit(e)

def commitAndPush(gitClonePath, repo, paths):
    """
    Add, commit, and push changes to a new branch called $tempBranch
    """
    try:
        repo.index.add(paths)
        print("Running `git add .`")
        # This requires being authenticated with GitHub locally as an org admin,
        # rather than adding a service account to all repos for migration
        repo.index.commit("Add migration helper script")
        print("Running `git commit`")
        origin = repo.remote()
        repo.create_head(tempBranch)
        origin.push(tempBranch)
        print("Successfully pushed up branch {} to {}/{}".format(tempBranch, org, project))
    except Exception as e:
        return SystemExit(e)

if __name__ == "__main__":
    """
    1. Set the environment variables from `envVarList` as project level environment variables in 
    the given CircleCI On-Prem project. 
    2. Clone project repo from GitHub. Copy over our CircleCI config file and python script, 
    ci_migration_script.py. Push up our changes to a new branch to trigger the script to run in CI.
    This will retrieve the CI secrets for the project, write them to a JSON file, and then upload that file to S3. 
    """
    setEnvVars()
    createDir(gitClonePath)
    repo = cloneRepo(gitClonePath)
    if repo and path.isdir(gitClonePath):
        paths = updateClone(gitClonePath)
        commitAndPush(gitClonePath, repo, paths)
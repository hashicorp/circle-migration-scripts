### Step 3 -- run this script locally
### Download the JSON file from S3 containing the project's secrets,
### and POST these as project-level environment variables in CircleCI SaaS 

### The project must already be 'Followed' and 'Building' in CircleCI SaaS

### WARNING: If env vars with the same names already exist in the SaaS project,
### This script will OVERWRITE them! 

from requests import get, post, put, exceptions
from os import getenv, path, getcwd, remove
from json import dumps, load, loads
from boto3 import s3, client
from botocore.exceptions import ClientError
from jq import compile
from github import Github
from functools import reduce
from shutil import rmtree

org = getenv("MIGRATION_ORG")
project = getenv("CIRCLE_PROJECT_REPONAME")
tempBranch = 'get-secrets'
gitClonePath = reduce(path.join,[getcwd(), 'git-clone', project])

cloudV2URL = "https://circleci.com/api/v2/project/gh/{}".format(org)

cloudHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Circle-Token': getenv("MIGRATION_CIRCLE_CLOUD_TOKEN")
}

onPremHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Circle-Token': getenv("MIGRATION_CIRCLE_SERVER_TOKEN")
}

def deleteLocalFiles():
    """Delete local files created by this script and step_1.py"""
    try:
        gitcloneDir = reduce(path.join,[getcwd(), 'git-clone'])
        jsonFilePath = reduce(path.join,[getcwd(), '{}.json'.format(project)])
        if path.exists(jsonFilePath):
            remove(jsonFilePath)
        if path.exists(gitcloneDir):
            rmtree(gitcloneDir)
        print('Deleted local files/directories created by this script: {}, {}'.format(jsonFilePath, gitClonePath))
    except Exception as e:
        # Print the error, but don't exit. We can move on from this! 
        print('Failed to cleanup temporary local files/directories created by this script: {}'.format(e))

def deleteBranch(branch):
    """Delete the temporary branch we created in step_1.py, get-secrets"""
    try:
        g = Github(getenv("MIGRATION_GITHUB_TOKEN"))
        repo = g.get_repo('{}/{}'.format(org, project))
        if repo:
            repo.get_git_ref('heads/{}'.format(branch)).delete()
            print('Deleted branch {} in project {}/{}'.format(branch, org, project))
    except Exception as e:
        # Print the error, but don't exit. We can move on from this! 
        print('Failed to delete branch branch {} in project {}/{}: {}'.format(branch, org, project, e))

def getJSON(project):
    """
    Download the JSON file containing the project's secret key:val pairs
    from the S3 bucket.
    """
    try:
        s3client = client('s3', aws_access_key_id=getenv("MIGRATION_AWS_ACCESS_KEY_ID"),aws_secret_access_key=getenv("MIGRATION_AWS_SECRET_ACCESS_KEY"))
        bucket = getenv("MIGRATION_BUCKET")
        filepath = '{}/{}.json'.format(getenv("MIGRATION_PREFIX"), project)
        filename = "{}.json".format(project)
        s3client.download_file(bucket, filepath, '{}.json'.format(project))
        print("Successfully downloaded {} to {} from S3 bucket {}".format(filepath, filename, bucket))
    except ClientError as err:
        raise SystemExit(err)
    return filename

def postToCircle(project, key, val):
    """
    For the given project, set each key:val pair as
    project level environment variables in Circle SaaS.
    """
    data = {
        'name': key,
        'value': val
    }
    url = '{}/{}/envvar'.format(cloudV2URL, project)

    try: 
        res = post(url, headers=cloudHeaders, data=dumps(data), timeout=3)
        res.raise_for_status()
        print('Successfully set env var {} in project {}'.format(res.json(), project))
    except (exceptions.HTTPError, exceptions.ConnectionError, exceptions.Timeout, exceptions.RequestException) as err:
        raise SystemExit(err)

def uploadSecrets(project, filename):
    """
    Read secrets from the JSON file in S3 and upload them to the 
    CircleCI SaaS project as projet-level environment variables.
    """
    with open(filename) as f:
        secrets = load(f)
        for key, val in secrets.items():
            postToCircle(project, key, val)

def getAndUploadSettings(project):
    """
    Use CircleCI API and jq to pull down a project's Settings
    from OnPrem and upload them to the active SaaS project.
    """
    settings = compile('."feature_flags" | del(."builds-service") | del(."fleet")').input(getSettings(project)).text()
    print('Successfully got settings for project {}:\n{}'.format(project, settings))
    uploadSettings(settings)

def getSettings(project):
    url = "{}/{}/{}/settings".format(getenv("MIGRATION_CIRCLE_SERVER_URL_V1"), org, project)
    data = {}
    print("GET url: {}\nheaders: {}".format(url, onPremHeaders))

    try:
        res = get(url, headers=onPremHeaders, data=data, timeout=3)
        res.raise_for_status()
    except (exceptions.HTTPError, exceptions.ConnectionError, exceptions.Timeout, exceptions.RequestException) as err:
        raise SystemExit(err)
    return res.json()

def uploadSettings(settings):
    url = "{}/{}/{}/settings".format(getenv("MIGRATION_CIRCLE_CLOUD_URL_V1"), org, project)
    data = dumps({"feature_flags": loads(settings)})
    print("PUT url: {}\nheaders: {}\ndata: {}".format(url, cloudHeaders, data))

    try:
        res = put(url, headers=cloudHeaders, data=data, timeout=3)
        res.raise_for_status()
        print('Successfully put settings for project {}'.format(project))
    except (exceptions.HTTPError, exceptions.ConnectionError, exceptions.Timeout, exceptions.RequestException) as err:
        raise SystemExit(err)

if __name__ == "__main__":
    """
    For a given project, download the JSON file containing the project level 
    environment variable key:val pairs, that were retrieved from On-Prem. 
    Set these environment variables for the project in SaaS.
    """
    filename = getJSON(project)
    uploadSecrets(project, filename)
    getAndUploadSettings(project)
    deleteBranch(tempBranch)
    deleteLocalFiles()

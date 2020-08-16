### Step 2 -- this will be run in CircleCI.
### step_2_pre.py will trigger it automatically. 
### Write all env vars to a JSON file, and 
### Upload the file to an s3 bucket

from requests import get
from os import getenv
from json import dump
from boto3 import client
from botocore.exceptions import ClientError

org = getenv("MIGRATION_ORG")
serverBaseURL = "https://circleci.{}.engineering".format(org)
project = getenv("CIRCLE_PROJECT_REPONAME")

serverHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Circle-Token': getenv("MIGRATION_SERVER_TOKEN")
}

filterlist = [ "MIGRATION_SERVER_TOKEN", "MIGRATION_CLOUD_TOKEN", "MIGRATION_AWS_ACCESS_KEY_ID",
               "MIGRATION_AWS_SECRET_ACCESS_KEY", "MIGRATION_BUCKET", "MIGRATION_PREFIX", "MIGRATION_ORG",
               "MIGRATION_GITHUB_TOKEN" ]

def listKeys(project):
    """ 
    For the given project, return a list of all project level environment variable keys
    Keys only.. no values!
    """ 
    keys = set()
    url = '{}/api/v1.1/project/github/{}/{}/envvar'.format(serverBaseURL, org, project)
    res = get(url, headers=serverHeaders, timeout=3)
    envvars = res.json()
    for envvar in envvars:
        keys.add(envvar['name'])
    return keys

def getVals(project, keys):
    """ 
    For the given project, given the list of project level environment variable keys, 
    return a dict of key:val pairs. Filter out any environment variables we added
    for the migration. 
    """ 
    secrets = {}
    for key in keys:
        # We don't want to write our 'migration' secrets to the file
        # Since they don't have anything to do with the project
        if key not in filterlist:
            val = getenv(key)
            if val is None:
                print("WARNING: Value for key {} in project {} is None".format(key, project))
                val = "None"
            secrets[key] = val
    return secrets

def writeToFile(project, secrets):
    """ 
    Write the dict of secrets to a file called $project.json
    and return the filename.
    """ 
    filename = '{}.json'.format(project)
    with open(filename,'w') as f:
        dump(secrets, f)
    return filename

def uploadFile(filename):
    """ 
    Upload the JSON file containing a dict of secrets to an S3 bucket.
    The file will be uploaded into a folder that is set by the MIGRATION_PREFIX env var,
    e.g. 'test' or 'prod'.
    """
    try:
        s3client = client('s3', aws_access_key_id=getenv("MIGRATION_AWS_ACCESS_KEY_ID"),aws_secret_access_key=getenv("MIGRATION_AWS_SECRET_ACCESS_KEY"))
        bucket = getenv("MIGRATION_BUCKET")
        filePath = '{}/{}'.format(getenv("MIGRATION_PREFIX"), filename)
        s3client.upload_file(filename, bucket, filePath)
        print("Successfully uploaded {} to {} in S3 bucket {}".format(filename, filePath, bucket))
    except ClientError as err:
        raise SystemExit(err)

if __name__ == "__main__":
    """ 
    Write all On-Prem project level environment variables for a given project 
    into a JSON file, and upload that file to S3
    """ 
    keys = listKeys(project)
    secrets = getVals(project, keys)
    filename = writeToFile(project, secrets)
    uploadFile(filename)

### Step 3 -- run this script locally
### Download the JSON file from S3 containing the project's secrets,
### and POST these as project-level environment variables in CircleCI SaaS 

### The project must already be 'Followed' and 'Building' in CircleCI SaaS

### WARNING: If env vars with the same names already exist in the SaaS project,
### This script will OVERWRITE them! 

from requests import get, post, put, exceptions
from os import getenv
from json import dumps, load, loads
from boto3 import s3, client
from botocore.exceptions import ClientError
import jq

org = getenv("MIGRATION_ORG")
cloudBaseURL = "https://circleci.com/api/v2/project/gh/{}".format(org)
cloudV1URL = "https://circleci.com/api/v1.1/project/github/{}".format(org)
onPremBaseURL = "https://circleci.hashicorp.engineering/api/v1.1/project/gh/{}".format(org)
project = getenv("CIRCLE_PROJECT_REPONAME")

cloudHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Circle-Token': getenv("MIGRATION_CLOUD_TOKEN")
}

onPremHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Circle-Token': getenv("MIGRATION_SERVER_TOKEN")
}

def getCSV(project):
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
    url = '{}/{}/envvar'.format(cloudBaseURL, project)

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
    settings = jq.compile('."feature_flags" | del(."builds-service") | del(."fleet")').input(getSettings(project)).text()
    print('Successfully got settings for project {}:\n{}'.format(project, settings))
    uploadSettings(settings)

def getSettings(project):
    url = "{}/{}/settings".format(onPremBaseURL, project)
    data = {}
    print("GET url: {}\nheaders: {}".format(url, onPremHeaders))

    try:
        res = get(url, headers=onPremHeaders, data=data, timeout=3)
        res.raise_for_status()
    except (exceptions.HTTPError, exceptions.ConnectionError, exceptions.Timeout, exceptions.RequestException) as err:
        raise SystemExit(err)
    return res.json()

def uploadSettings(settings):
    url = "{}/{}/settings".format(cloudV1URL, project)
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
    filename = getCSV(project)
    uploadSecrets(project, filename)
    getAndUploadSettings(project)

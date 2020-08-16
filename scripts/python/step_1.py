### Step 1 -- run this script locally
### Create required env vars in the Circle-CI On-Prem project
### These contain AWS keys and CircleCI API keys
### WARNING: If env vars with the same names are already set for the project, 
### This script will OVERWRITE them! 

from requests import post, exceptions
from os import getenv
from json import dumps, loads

org = getenv("MIGRATION_ORG")
serverBaseURL = "https://circleci.{}.engineering".format(org)
project = getenv("CIRCLE_PROJECT_REPONAME")

serverHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Circle-Token': getenv("MIGRATION_SERVER_TOKEN")
}

envVarList = [ "MIGRATION_SERVER_TOKEN", "MIGRATION_CLOUD_TOKEN", "MIGRATION_AWS_ACCESS_KEY_ID",
               "MIGRATION_AWS_SECRET_ACCESS_KEY", "MIGRATION_BUCKET", "MIGRATION_PREFIX", "MIGRATION_ORG" ]

def createEnvVar(project, key):
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
    url = '{}/api/v1.1/project/github/{}/{}/envvar'.format(serverBaseURL, org, project)

    try: 
        res = post(url, headers=serverHeaders, data=dumps(data), timeout=3)
        res.raise_for_status()
        print('Successfully set env var {} in project {}'.format(res.json(), project))
    except exceptions.HTTPError as err:
        raise SystemExit(err)
    except exceptions.ConnectionError as err:
        raise SystemExit(err)
    except exceptions.Timeout as err:
        raise SystemExit(err)
    except exceptions.RequestException as err:
        raise SystemExit(err)

def setEnvVars(project):
    """ 
    Iterate over the keys in `envVarList` to set temporary project level environment variables
    for the On-Prem project. These are needed for the migration, but will not be added to SaaS. 
    """
    for key in envVarList:
        createEnvVar(project, key)

if __name__ == "__main__":
    """
    Set the environment variables from `envVarList` as project level environment variables in 
    the given CircleCI On-Prem project.
    """
    setEnvVars(project)

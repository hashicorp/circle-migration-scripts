# Circle Migration Scripts

This repo contains some scripts to help with the Circle On-Prem to SaaS migration. Follow the steps below to get started. 

### Project level environment variable migration

Clone the repo:
`git clone git@github.com:hashicorp/circle-migration-scripts.git`

Rename .env-test:
`mv .env-test .env`

Add real secrets to `.env`

Source the secrets on your local machine to set the env vars:
`source .env`

1. Start with the script called `step_1.py` in `scripts/python`. <br />
This script should be run LOCALLY. It's purpose is to create the required project level environment variables needed for the migration in the given Circle-CI On-Prem project. The environment variables set contain AWS keys and CircleCI API keys, among other things. These secrets will not be moved to SaaS.

**NOTE** If environment variables with the same are already set for the project, this script will OVERWRITE them. (Each environment variable in the `.env` file is prefixed with `MIGRATION_` to help with this, but can be randomized further if needed.)

2. After running `step_1.py` locally, move onto `step_2.py` in `scripts/python`. <br />
This script should be run LOCALLY. It's purpose is to trigger a CircleCI job for the given project. It starts by cloning the project repo locally, copying over our `example-config/.circleci/config.yml` file, and copying over our `scripts/python/ci_migration_script.py` file. It then does a `git add .`, commit, and finally pushes up our changes to a new branch called `get-secrets`. This will kick off a CI job in the given CircleCI On-Prem project. 

The CI job simply calls `ci_migration_script.py`, whose purpose is to get all project level environment variables from the CircleCI On-Prem project, write the key:val pairs to a JSON file, and upload the file to an S3 bucket.

3. Follow the project in CircleCI SaaS to start building it. Feel free to cancel the build it kicks off.

4. After running `step_2.py`, and then following the project in SaaS, move onto `step_3.py`in `scripts/python`. <br />
This script should be run LOCALLY. It's purpose is to download the JSON file from S3 containing the project's secrets, and POST these as project-level environment variables in CircleCI SaaS. 

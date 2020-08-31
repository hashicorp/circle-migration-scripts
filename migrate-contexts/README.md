# Migrating Contexts from CircleCI On-Prem to CircleCI SaaS

## Extract Contexts from On-Prem

### Get List of Contexts
1. Get onto the [`services`](https://circleci.com/docs/2.0/overview/#services-machine) host
```
ssh ubuntu@services.circleci.myorg.com
```
2. Run the following to output a csv file of `contextname,context_uuid`
```
sudo docker exec postgres psql -U circle -d contexts_service_production -c "\copy (select name,id from contexts) TO STDOUT WITH CSV" > contexts.csv
```

### Get Contexts from REPL

Prereq: Complete the steps to [get a list of contexts](#get-list-of-contexts)

1. Connect to the `contexts-service` container via Docker. **Note:** This may only be accessible through the `services` host
```
sudo docker exec -ti contexts-service bash
```
3. Connect to the REPL
```
lein repl :connect 2718
```
4. Generate a JSON file with the input of the CSV context list above:
```
(let [contexts      {"context-foo" "uuid-of-context"
                     "context-bar" "uuid-of-context"
                     .......
                     }
      reduce-fn (fn [coll [context uuid]]
                  (let [id        (java.util.UUID/fromString uuid)
                        response  (contexts-service.db/get-context id)
                        resources (:contexts-service-client.context.response/resources response)
                        parse-fn  (fn [res]
                                    (let [var (:contexts-service-client.context/variable res)
                                          val (:contexts-service-client.context/value res)]
                                      {var val}))
                        parsed    (map parse-fn resources)
                        data (into {} parsed)]
                    (conj coll {context data})))
      data (reduce reduce-fn {} contexts)
      writer (clojure.java.io/writer "/tmp/foo")]
  (cheshire.core/generate-stream data writer))
```
5. SCP it back out to the host you need it on
```
scp -o 'ProxyJump ubuntu@bastion.circleci.org.com' ubuntu@services.circleci.myorg.com:/home/ubuntu/contexts.json contexts.json
```
## Uploading Contexts to CircleCI SaaS

1. Install the [circleci-cli](https://github.com/CircleCI-Public/circleci-cli) and login to your account. This will be used to authenticate in the program.
2. Run the go program with the JSON file you exported above:
```
$ go build main.go -o circleci-context-uploader

Usage of ./circleci-context-uploader:
  -context string
        (Optional) Name of context to migrate
  -file string
        (Required) JSON file of CircleCI Contexts
  -org string
        (Required) Name of VCS Organization (ex: hashicorp)
  -vcs string
        (Optional) VCS type (default "github")
```

Example usage:

(Recommended) Upload a specific context:
```
./circleci-context-uploader -file=contexts.json -org=hashicorp -context=some-context-name
```
Upload all contexts:
```
./circleci-context-uploader -file=contexts.json -org=hashicorp
```
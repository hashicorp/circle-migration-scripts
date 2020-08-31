package main

import (
	"encoding/json"
	"flag"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"strings"
)

const (
	app        = "circleci"
	subCommand = "context"
)

// uploadContext uses the circleci CLI upload context kv pairs
func uploadContext(result map[string]map[string]string, vcs, org, contextName string) error {
	// create CircleCI Context
	cmd := exec.Command(app, subCommand, "create", vcs, org, contextName)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	// attempt to create the context
	err := cmd.Run()

	if err == nil {
		log.Printf("Context %q created\n", contextName)
	}
	if err != nil {
		if ee, ok := err.(*exec.ExitError); ok && ee.ExitCode() == 255 {
			// 255 is the error the CLI returns if the context already exists
			log.Printf("Context %q exists already\n", contextName)
		} else {
			return err
		}
	}

	// loop through each KV pair and add to context
	for key, value := range result[contextName] {
		log.Printf("Uploading key: %q, value: %q\n", key, value)
		cmd = exec.Command(app, subCommand, "store-secret", vcs, org, contextName, key)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Stdin = strings.NewReader(value)
		err := cmd.Run()
		// the CLI does not update, only adds a new entry
		if err != nil {
			return err
		}
	}
	return nil
}

func main() {
	var inputFile, org, contextName, vcs string
	flag.StringVar(&inputFile, "file", "", "(Required) JSON file of CircleCI Contexts")
	flag.StringVar(&org, "org", "", "(Required) Name of VCS Organization (ex: hashicorp)")
	flag.StringVar(&contextName, "context", "", "(Optional) Name of context to migrate")
	flag.StringVar(&vcs, "vcs", "github", "(Optional) VCS type")
	flag.Parse()

	if inputFile == "" {
		log.Fatalln("Error: -file needs to be set")
	}

	if org == "" {
		log.Fatalln("Error: -org needs to be set")
	}

	// read json file
	jsonFile, err := ioutil.ReadFile(inputFile)
	var result map[string]map[string]string
	if err != nil {
		log.Fatalf("Error reading inputFile: %v", err)
	}
	err = json.Unmarshal([]byte(jsonFile), &result)
	if err != nil {
		log.Fatalf("Error unmarshalling inputFile: %v", err)
	}

	// if --context isn't set we loop through all contexts in the json file, otherwise
	// we only upload a specific context
	if contextName == "" {
		for name := range result {
			err := uploadContext(result, vcs, org, name)
			if err != nil {
				log.Fatalf("Error executing uploadContext on the %q context: %v\n", name, err)
			}
		}
		os.Exit(0)
	}
	err = uploadContext(result, vcs, org, contextName)
	if err != nil {
		log.Fatalf("Error executing uploadContext on the %q context: %v\n", contextName, err)
	}
}

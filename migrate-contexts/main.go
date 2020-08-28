package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"strings"
)

// uploadContext uses the circleci CLI upload context kv pairs
func uploadContext(result map[string]map[string]string, vcs, org, contextName string) error {
	// create CircleCI Context
	app := "circleci"
	subCommand := "context"

	cmd := exec.Command(app, subCommand, "create", vcs, org, contextName)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	// attempt to create the context
	err := cmd.Run()
	if err != nil {
		if ee, ok := err.(*exec.ExitError); ok {
			// 255 is the error the CLI returns if the context already exists
			if ee.ExitCode() == 255 {
				log.Printf("Context '%s' exists already\n", contextName)
			} else {
				return err
			}
		}
	} else {
		log.Printf("Context '%s' created\n", contextName)
	}

	// loop through each KV pair and add to context
	for key, value := range result[contextName] {
		fmt.Printf("Uploading...\nkey: %s\nvalue: %s\n", key, value)
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
		fmt.Println("Error: -file needs to be set")
		os.Exit(1)
	}

	if org == "" {
		fmt.Println("Error: -org needs to be set")
		os.Exit(1)
	}

	// read json file
	jsonFile, err := ioutil.ReadFile(inputFile)
	var result map[string]map[string]string
	if err != nil {
		fmt.Printf("Error reading inputFile: %s", err)
		os.Exit(1)
	}
	err = json.Unmarshal([]byte(jsonFile), &result)
	if err != nil {
		fmt.Printf("Error unmarshalling inputFile: %s", err)
		os.Exit(1)
	}

	// if --context isn't set we loop through all contexts in the json file, otherwise
	// we only upload a specific context
	if contextName == "" {
		for name := range result {
			err := uploadContext(result, vcs, org, name)
			if err != nil {
				fmt.Printf("Error executing uploadContext on the '%s' context: %v\n", name, err)
				os.Exit(1)
			}
		}
	} else {
		err := uploadContext(result, vcs, org, contextName)
		if err != nil {
			fmt.Printf("Error executing uploadContext on the '%s' context: %v\n", contextName, err)
			os.Exit(1)
		}
	}
}

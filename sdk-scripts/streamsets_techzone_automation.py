#!/usr/bin/python3

"""
FILE: streamsets_techzone_automation.py

DESCRIPTION: 
Create the base items in control hub to easiy get started with streamSets.

ARGS:
    - TBD

USAGE: $ python3 streamsets_techzone_automation.py

USAGE EXAMPLE: python3 streamsets_techzone_automation.py

PREREQUISITES:

- Python 3.9+

- StreamSets Platform SDK for Python v6.0+
  See: https://docs.streamsets.com/platform-sdk/latest/welcome/installation.html

- StreamSets Platform API Credentials for a user with Organization Administrator role

- Before running the script, export the environment variables CRED_ID and CRED_TOKEN
  with the StreamSets Platform API Credentials, like this:

    $ export CRED_ID="40af8..."
    $ export CRED_TOKEN="eyJ0..."

"""
import os
from streamsets.sdk import ControlHub
from kubernetes import client, config, utils
import sys
import yaml

############################# global variables

kubeconfig_path = '~/.kube/kubeconfig_techzone_k3s.conf'

##### environment sensible values
env_name = 'Techzone StreamSets Demos'
env_version = '1.2.1'
env_tags = ['k3s-techzone','demo']
env_kub_namespace = 'streamsetsdemos'
env_kub_agent_jvm_opt = ''
env_kub_labels = {'environment': 'techzone'}

##### deployment sensible values
deployment_name = 'Techzone StreamSets Multipurpose Demo 1'
deployment_engine_version = '6.0.0'
deployment_engine_type = 'DC'
deployment_tags = ['k3s-techzone-sdc-6.0.0','kafka','postgres','minio',"s3"]
deployment_external_resource_location = 'http://minio.minio.svc.cluster.local/streamsets-deployment-archives/externalResources-demos.zip'
deployment_stage_libs = [
	"aws:6.0.0",
	"apache-kafka_3_7:6.0.0",
	"basic:6.0.0",
	"dataformats:6.0.0",
	"dev:6.0.0",
	"groovy_4_0:6.0.0",
	"jdbc:6.0.0",
	"jython_2_7:6.0.0"
]
deployment_kub_labels = {'environment': 'techzone'}

############################# functions

def print_usage_and_exit():
    print('Prerequisite: StreamSets Control Hub API Credentials set via environment variables: CRED_ID and CRED_TOKEN')
    print('Usage: $ python3 streamsets_techzone_automation.py <optional:deploy_agent_yaml(true|false)> <optional:kube_config_path>')
    print('Usage Example: python3 streamsets_techzone_automation.py true')
    sys.exit(1)


# Method to add a user to an Organization
def deploy_k8s_agent(install_yaml, install_namespace):
    print("Deploying Kubernetes YAML")
    
    # Load Kubernetes configuration
    config.load_kube_config(config_file=kubeconfig_path)

    # Create a Kubernetes API client
    api_client = client.ApiClient()

    # shall we delete the namespace and recreate? too destructive...
    # k8s_coreapi = client.CoreV1Api()
    # k8s_coreapi.delete_namespace(name=install_namespace)

    install_yaml_objects = yaml.safe_load_all(install_yaml)

    # Create the Kubernetes objects from the YAML string
    utils.create_from_yaml(api_client, yaml_objects=install_yaml_objects, namespace=install_namespace, verbose=True)

    print("Agent Deployment created!")


############################# end functions

# Get Control Hub Credentials from the environment
cred_id = os.getenv('CRED_ID')
cred_token = os.getenv('CRED_TOKEN')

if not (cred_id and cred_token):
    print('Error: You must add your Control Hub Credentials to the environment')
    print_usage_and_exit()

# Check the number of command line args
if len(sys.argv) != 1:
    print('Error: Wrong number of arguments')
    print_usage_and_exit()

# Connect to Control Hub
sch = None
try:
    sch = ControlHub(
        credential_id=cred_id,
        token=cred_token)
except Exception as e:
    print('Error connecting to Control Hub; check your CRED_ID and CRED_TOKEN environment variables')
    print(str(e))
    sys.exit(1)

# Get the Organization's name
org_name = sch.organizations[0].name
print("Connected to org = {}".format(org_name))

################################ Environment section: create new or get

print("Create new, or get existing, environment for Techzone")
environment = None
try:
    ## check if env is already there
    environment = sch.environments.get(environment_name=env_name)
    print('Environment \'{}\' already exists in the Org \'{}\''.format(env_name, org_name))
    print('No action will be taken')

# If we get here, the object does not exist in the Org
except ValueError:
    try:
        environment_builder = sch.get_environment_builder(environment_type='KUBERNETES')
        environment = environment_builder.build(environment_name=env_name,
                                                environment_tags=env_tags,
                                                allow_nightly_builds=False)
        environment.agent_version = env_version
        environment.kubernetes_namespace = env_kub_namespace
        environment.kubernetes_labels = env_kub_labels

        sch.add_environment(environment)
        sch.activate_environment(environment, timeout_sec=300)
    except Exception as e:
        print('Error creating/adding the environment in Control Hub')
        print(str(e))
        sys.exit(1)

print("INFO: environment state = {} / status = {} / status details = {}".format(environment.state, environment.agent_status, environment.agent_status_detail))

if environment.state != 'ACTIVE':
    raise ValueError("Environment should be activated at this point")

try:
    if environment.agent_status != 'ONLINE':
        print("Environment agent is not online...installing it!")
        install_yaml = sch.get_kubernetes_environment_yaml(environment)
        deploy_k8s_agent(install_yaml,env_kub_namespace)
except Exception as e:
    print('Error creating the kubernetes artifatcs automatically!')
    print("Fallback: Try doing it manually with this Kubernetes Agent install script command:")
    install_script = sch.get_kubernetes_apply_agent_yaml_command(environment)
    print(install_script)
    print(str(e))

################################ deployment section - create new or get

print("Create new, or get existing, deployment for Techzone")
deployment = None
try:
    ## check if env is already there
    deployment = sch.deployments.get(deployment_name=deployment_name)
    print('Deployment \'{}\' already exists in the Org \'{}\''.format(deployment_name, org_name))
    print('No action will be taken')

# If we get here, the object does not exist in the Org
except ValueError:
    try:
        deployment_builder = sch.get_deployment_builder(deployment_type='KUBERNETES')
        deployment = deployment_builder.build(deployment_name=deployment_name,
                                            environment=environment,
                                            external_resource_location=deployment_external_resource_location,
                                            engine_type=deployment_engine_type,
                                            engine_version=deployment_engine_version,
                                            deployment_tags=deployment_tags,
                                            max_cpu_load=80.0, 
                                            max_memory_used=100.0
                                            )
        sch.add_deployment(deployment)

        # Set Kubernetes configurations for the deployment
        deployment.kubernetes_labels = {'environment': 'streamsets'}
        deployment.desired_instances = 1
        deployment.cpu_request = '1.0'
        deployment.memory_request = '2Gi'
        deployment.memory_limit = '4Gi'

        deployment.engine_configuration.stage_libs = deployment_stage_libs

        # Update the deployment's configuration/definition on Control Hub
        sch.update_deployment(deployment)

        # Optional - equivalent to clicking on 'Launch Deployment'
        sch.start_deployment(deployment)
    except Exception as e:
        print('Error creating/adding the environment in Control Hub')
        print(str(e))
        sys.exit(1)

print('Done')
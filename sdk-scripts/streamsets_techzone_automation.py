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
import hashlib
import time
import argparse
import getpass
import socket

############################# global variables

##### environment values
env_name = 'TZ-{} Demos'
env_version = '1.2.1'
env_tags = ['k3s-techzone','demo']
env_kub_namespace = 'streamsetsdemos'
env_kub_agent_jvm_opt = ''
env_kub_labels = {'environment': 'techzone'}

##### deployment values
deployment_name = 'TZ-{} Multipurpose Demo 1 '
deployment_engine_version = '6.0.0'
deployment_engine_type = 'DC'
deployment_tags = ['k3s-techzone-sdc-6.0.0','kafka','postgres','minio',"s3"]
deployment_external_resource_location = 'http://minio.minio.svc.cluster.local/streamsets-deployment-archives/externalResources-demos.zip'

deployment_stage_libs_min = [
	"aws:6.0.0",
	"apache-kafka_3_7:6.0.0",
	"basic:6.0.0",
	"dataformats:6.0.0",
	"dev:6.0.0",
	"groovy_4_0:6.0.0",
	"jdbc:6.0.0",
	"jython_2_7:6.0.0"
]

deployment_stage_libs_extensive = [
	"kinesis:6.0.0",
	"aws:6.0.0",
	"apache-kafka_3_7:6.0.0",
	"aws-secrets-manager-credentialstore:6.0.0",
	"azure-keyvault-credentialstore:6.0.0",
	"azure:6.0.0",
	"basic:6.0.0",
	"crypto:6.0.0",
	"cyberark-credentialstore:6.0.0",
	"dataformats:6.0.0",
	"sdc-databricks:6.0.0",
	"dev:6.0.0",
	"elasticsearch_8:6.0.0",
	"bigtable:6.0.0",
	"google-cloud:6.0.0",
	"google-secret-manager-credentialstore:6.0.0",
	"groovy_4_0:6.0.0",
	"jks-credentialstore:6.0.0",
	"jdbc:6.0.0",
	"jms:6.0.0",
	"jython_2_7:6.0.0",
	"webclient-impl-okhttp:6.0.0",
	"orchestrator:6.0.0",
	"redis:6.0.0",
	"salesforce:6.0.0",
	"singlestore:6.0.0",
	"sdc-snowflake:6.0.0",
	"vault-credentialstore:6.0.0"
]

## pick the extensive one for more coverage for demos
deployment_stage_libs = deployment_stage_libs_extensive

deployment_kub_labels = {'environment': 'techzone'}

############################# functions

def kube_deploy_yaml(kubeconfig_path, namespace_name, install_yaml):
    """Patching Kubernetes deployments's dnspolicy"""

    print("Deploying Kubernetes YAML into namespace {}, with kube config {}".format(namespace_name, kubeconfig_path))
    
    # Load Kubernetes configuration
    config.load_kube_config(config_file=kubeconfig_path)

    # Create a Kubernetes API client
    api_client = client.ApiClient()

    # shall we delete the namespace and recreate? too destructive...
    # k8s_coreapi = client.CoreV1Api()
    # k8s_coreapi.delete_namespace(name=install_namespace)

    install_yaml_objects = yaml.safe_load_all(install_yaml)

    # Create the Kubernetes objects from the YAML string
    utils.create_from_yaml(api_client, yaml_objects=install_yaml_objects, namespace=namespace_name, verbose=True)

    print("Agent Deployment created!")


def kube_patch_deployment_dnspolicy(kubeconfig_path, namespace_name, deployments):
    """Patching Kubernetes deployments's dnspolicy"""

    # Load Kubernetes configuration
    config.load_kube_config(config_file=kubeconfig_path)

    # Create a Kubernetes API client
    api_instance = client.AppsV1Api()

    # Create a patch object
    patch = {
        "spec": {
            "template": {
                "spec": {
                    "dnsPolicy": "ClusterFirst" 
                }
            }
        }
    }

    # Patch all the pod
    for dep in deployments:
        dep_name = dep.metadata.name
        print(dep_name)
        try:
            api_instance.patch_namespaced_deployment(dep_name, namespace_name, patch)
            print("Deployment DNS policy patched successfully.")
        except client.rest.ApiException as e:
            print(f"Error patching pod: {e}")

def kube_get_pods_by_label(kubeconfig_path, namespace_name, label_selector):
    """Gets a pod by label in the specified namespace."""

    # Load Kubernetes configuration
    config.load_kube_config(config_file=kubeconfig_path)

    # Create a Kubernetes API client
    api_instance = client.CoreV1Api()

    # List pods in the specified namespace, filtered by label
    pods = api_instance.list_namespaced_pod(namespace=namespace_name, label_selector=label_selector)

    if pods.items:
        return pods.items
    else:
        return []

def kube_get_deployments_by_label(kubeconfig_path, namespace_name, label_selector):
    """Gets a pod by label in the specified namespace."""

    # Load Kubernetes configuration
    config.load_kube_config(config_file=kubeconfig_path)

    # Create a Kubernetes API client
    api_instance = client.AppsV1Api()

    # List deployments in the specified namespace, filtered by label
    deployments = api_instance.list_namespaced_deployment(namespace=namespace_name, label_selector=label_selector)

    if deployments.items:
        return deployments.items
    else:
        return []
    
def wait_for_state(check_function, desired_state, desired_state_not=False, timeout=10, interval=1):
    """Waits for a condition to become true.

    Args:
        check_function: A function that returns the current state.
        desired_state: The state we are waiting for.
        timeout: Maximum time to wait (in seconds).
        interval: Time between checks (in seconds).

    Returns:
        True if the desired state was reached, False if timeout occurred.
    """

    start_time = time.time()
    while True:
        print('Waiting...')
        current_state = check_function()

        if desired_state_not:
            if current_state != desired_state:
                return True
        else:
            if current_state == desired_state:
                return True

        if time.time() - start_time > timeout:
            print('Reached timeout...')
            return False

        time.sleep(interval)

class PwdAction(argparse.Action):
     def __call__(self, parser, namespace, values, option_string=None):
         mypass = getpass.getpass()
         setattr(namespace, self.dest, mypass)

def get_environment_status(env_name):
    env_check = sch.environments.get(environment_name=env_name)
    return env_check.agent_status

def get_deployment_status(dep_name):
    dep_check = sch.deployments.get(deployment_name=dep_name)
    return dep_check.state

############################# end functions

# Add named arguments
parser = argparse.ArgumentParser(description="StreamSets Techzone Automation script")
parser.add_argument("-u", "--cred_id", help="StreamSets Control Hub API ID (Optional: Also set via OS ENV var 'SCH_CRED_ID)'", default=os.environ.get('SCH_CRED_ID'))
parser.add_argument('-p', "--cred_token", action=PwdAction, nargs=0, dest='cred_token', help="StreamSets Control Hub API Token (Optional: Also set via OS ENV var 'SCH_CRED_TOKEN)'", default=os.environ.get('SCH_CRED_TOKEN'))
parser.add_argument("-kn", "--kube_nodeploy", action='store_true', help="Deploy the agent YAML or not")
parser.add_argument("-kc", "--kube_config", help="Kube Config path", default=os.environ.get('KUBECONFIG'))
parser.add_argument("-s", "--suffix", help="Suffix to add to the created objects", default=os.environ.get('SCH_OBJ_SUFFIX'))

# Parse the arguments
args = parser.parse_args()

if not (args.cred_id and args.cred_token):
    print('Parameter required: StreamSets Control Hub API Credentials! Specify either with environment variables, or script arguments as defined by usage.')
    exit(parser.print_usage())

cred_id = args.cred_id
cred_token = args.cred_token
kube_nodeploy = args.kube_nodeploy
kube_config_path = args.kube_config

obj_suffix = None
if args.suffix:
    obj_suffix = args.suffix

# get a constant unique identifier hash based on the cred_id token
unique_identifier_full = str(int(hashlib.sha256(cred_id.encode('utf-8')).hexdigest(), 16))
unique_identifier_size = len(unique_identifier_full)
if unique_identifier_size < 10:
    unique_identifier = unique_identifier_full
else:
    unique_identifier = unique_identifier_full[0:5] + unique_identifier_full[unique_identifier_size-5:unique_identifier_size]

if obj_suffix:
    unique_identifier += '-' + obj_suffix

print("Unique identifyer {}".format(unique_identifier))

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
print("Connected to org = {} with unique identifyer {}".format(org_name, unique_identifier))

################################ Environment section: create new or get

environment = None
env_name_final = env_name.format(unique_identifier);
print("Create new, or get existing, environment with name = {}".format(env_name_final))

try:
    ## check if env is already there
    environment = sch.environments.get(environment_name=env_name_final)
    print('Environment \'{}\' already exists in the Org \'{}\''.format(env_name_final, org_name))
    print('No action will be taken')

# If we get here, the object does not exist in the Org
except ValueError:
    try:
        environment_builder = sch.get_environment_builder(environment_type='KUBERNETES')
        environment = environment_builder.build(environment_name=env_name_final,
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

if environment.state == 'DEACTIVATED':
    print('Environment in DEACTIVATED state - RE-ACTIVATING!')
    sch.activate_environment(environment, timeout_sec=300)

if environment.state != 'ACTIVE':
    raise ValueError("Environment should be activated at this point")

if not kube_nodeploy:
    try:
        if get_environment_status(env_name_final) != 'ONLINE':
            print("Environment agent is not online...installing it!")
            install_yaml = sch.get_kubernetes_environment_yaml(environment)
            kube_deploy_yaml(kube_config_path, env_kub_namespace, install_yaml)

    except Exception as e:
        print('Error creating the kubernetes artifatcs automatically!')
        print("Fallback: Try doing it manually with this Kubernetes Agent install script command:")
        install_script = sch.get_kubernetes_apply_agent_yaml_command(environment)
        print(install_script)
        print(str(e))

    print("Waiting a bit for Environment ONLINE before next step")
    if wait_for_state(lambda: get_environment_status(env_name_final), desired_state='ONLINE', timeout=60, interval=5):
        print("Environment is ONLINE!!")

################################ deployment section - create new or get

deployment = None
deployment_name_final = deployment_name.format(unique_identifier);
print("Create new, or get existing, deployment with name = {}".format(deployment_name_final))

try:
    ## check if deployment is already there
    deployment = sch.deployments.get(deployment_name=deployment_name_final)
    print('Deployment \'{}\' already exists in the Org \'{}\''.format(deployment_name_final, org_name))
    print('No action will be taken')

# If we get here, the object does not exist in the Org
except ValueError:
    try:
        deployment_builder = sch.get_deployment_builder(deployment_type='KUBERNETES')
        deployment = deployment_builder.build(deployment_name=deployment_name_final,
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
    except Exception as e:
        print('Error creating/adding the environment in Control Hub')
        print(str(e))
        sys.exit(1)

# Equivalent to clicking on 'Launch Deployment'
dep_state = get_deployment_status(deployment_name_final)
print('Deployment state = {}'.format(dep_state))

if dep_state == 'ACTIVATING':
    if wait_for_state(lambda: get_deployment_status(deployment_name_final), desired_state='ACTIVATING', desired_state_not=True, timeout=60, interval=5):
        print("Environment is NOT ACTIVATING anymore!!")

if dep_state == 'DEACTIVATING':
    if wait_for_state(lambda: get_deployment_status(deployment_name_final), desired_state='DEACTIVATING', desired_state_not=True, timeout=60, interval=5):
        print("Environment is NOT DEACTIVATING anymore!!")

if dep_state != 'ACTIVE':
    try:
        print('Deployment not active...re-starting the deployment in case it was in error state...')
        sch.stop_deployment(deployment)
        sch.start_deployment(deployment)
    except Exception as e:
        print(str(e))

if dep_state != 'ACTIVE':
    if wait_for_state(lambda: get_deployment_status(deployment_name_final), desired_state='ACTIVE', timeout=60, interval=5):
        print("Deployment is ACTIVE!!")
    else:
        raise ValueError("Deployment should be activated at this point")

## finally, patch the pods
print("Patch the dnspolicy of all the deployments in the namespace {} due to manifest issues".format(env_kub_namespace))
label_selector = "environment=techzone"
deployments = kube_get_deployments_by_label(kube_config_path, env_kub_namespace, label_selector)
kube_patch_deployment_dnspolicy(kube_config_path, env_kub_namespace, deployments)

print('Done')
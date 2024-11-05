k8-externalresources-mgt-with-aws
=======================================

This is a small sample concept, where you centralize your external resources in an object storage (like AWS S3), and have all the StreamSets data collectors pull from that object store repo automatically to keep in sync.

In this sample/demo, we will use AWS S3 as the repo source. 
You can find the same demo where we use Minio instead of AWS S3. find it [here](../k8-externalresources-mgt-with-minio/)

## Prerequisites

You have a K8 install to test this with (ie. Rancher Desktop for example)
You have a streamSets control hub tenant
You have access to AWS S3 with Access_Key and Access_Secret available

Let's do the work in the Streamsets namespace for simplicity (the namespace that has the streamSets Kubernetes agent)...
ie. namespace "streamsetsdemos"

### Add StreamSets assets in AWS S3

Create the following 3 directories (names matter... we will use these same names in the K8 assets) in a bucket of choice
Each of these S3 directory will get pulled from into a specific directory on the StreamSets data collector. 

- streamsets-libs-extras --> for extra libs to be added to specific stages (for example, new JDBC drivers for the stage "streamsets-datacollector-jdbc-lib"...)
- user-libs --> custom stage (for example, a custom salesforce stage "streamsets-datacollector-salesforce-lib" with different Salesforce client lib versions...)
- resources --> custom resources (properties files, etc.)

## Kubernetes assets
 
### Deploy core supporting assets

Core Supporting assets 1: Create secret for AWS access:

```sh
kubectl create secret generic streamsets-libspull-credentials-aws \
    --namespace streamsetsdemos \
    --from-literal=access_key_id="<SOMEVALUE>" \
    --from-literal=secret_access_key="<SOMEVALUE>"
```

Core Supporting assets 2: PVC (that will get used by the deployment engines)

```sh
kubectl --namespace streamsetsdemos apply -f ./manifests/pvc-pull-libraries.yaml
```

Core Supporting assets 3: Config map for the shell sync command script

```sh
kubectl --namespace streamsetsdemos apply -f ./manifests/cm-sync-aws.yaml
```

### Deploy JOB supporting assets

The jobs will allow you to keep things in sync automatically or on demand...

1 K8s CRON JOB to offer options and auto-pull assets ongoingly on a schedule  

```sh
kubectl --namespace streamsetsdemos apply -f ./manifests/cronjob-pull-libraries.yaml
```

And 1 K8s JOB for easy ad-hoc running if/when needed (deploy when needed)

```sh
kubectl --namespace streamsetsdemos apply -f ./manifests/job-pull-libraries.yaml
```

You can re-run the ad-hoc job at will by deleting and recreating...

```sh
kubectl --namespace streamsetsdemos delete -f ./manifests/job-pull-libraries.yaml
kubectl --namespace streamsetsdemos apply -f ./manifests/job-pull-libraries.yaml
```

## Deploy the deployment in streamsets

The deployment file contains the following customization, in addition to the usual StreamSets items:
 - The PVC gets used by the data collector pod to create a Persistent Volume (PV),
 - PV gets mounted READ-ONLY to the right places on the data collector (specific Sx directories) using volumeMounts section
 - An init container to automatically pull from AWS S3 all the required assets onto the same Persistent Volume (PV) BEFORE the data collector container starts

And outside of that, the cronjob will refresh the data on that Persistent Volume (PV) regularly to keep thing fresh...

The file "./manifests/deployment-with-pvc-template.yaml" should be added to the StreamSets deployment
IMPORTANT: make sure to replace the placeholders "UUID" and "ORGID" in that file with what StreamSets expects
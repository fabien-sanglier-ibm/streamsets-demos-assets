k8-externalresources-mgt-with-minio
=======================================

This is a small sample concept, where you centralize your external resources in an object storage (like Minio), and have all the StreamSets data collectors pull from that object store repo automatically to keep in sync.

In this sample/demo, we will use Minio deployed right on our K8 cluster... BUT the very same concept could be easily adapted and achieved with AWS S3 or other object storage platforms.

## Prerequisites

You have a K8 install to test this with (ie. Rancher Desktop for example)
You have a streamSets control hub tenant

Let's do the work in the Streamsets namespace for simplicity (the namespace that has the streamSets Kubernetes agent)...
ie. namespace "streamsetsdemos"

If you already have Minio or AWS S3, no need for the next section for you...

## Object Storage - Minio

### Install Minio

You should havbe the Minio operator already installed...

Install new tenant in the Sx namespace 
(using ./minio/minio-tenant-sx.yaml which is very standard value file as explained in the Minio Doc website)

helm install \
--namespace streamsetsdemos \
--create-namespace \
--values ./minio/minio-tenant-sx.yaml \
streamsetsminio minio-operator/tenant

### Forward the Tenant’s MinIO ports

This is a simple demo... not setting Minio with ingress etc...
Will just use port forwards to access the minio services.

Minio API: forward on port 55280
Minio Console: forward on port 55281

Access URL: https://localhost:55281

Access with Minio CLI (mc) - Create an alias for the minio CLI:

```zsh
mc alias set myminio https://localhost:55280 ACCESSKEY ACCESSSECRET --insecure
```

### Create MinIO core assets

Create User for StreamSets = streamsets-svc
+ create access key / secret key

Create bucket:
mc mb --insecure myminio/streamsets-datacollector-libs-collection1

Note: ensures "streamsets-svc" user has read/write access to that bucket

### Add StreamSets assets in Minio

Create the following 3 directories in this bucket (names matter... we will use these names in the K8 assets)
Each of these directory will get mapped to a specific directory on the StreamSets data collector. 

- streamsets-libs-extras --> for extra libs to be added to specific stages (for example, new JDBC drivers for the stage "streamsets-datacollector-jdbc-lib"...)
- user-libs --> custom stage (for example, a custom salesforce stage "streamsets-datacollector-salesforce-lib" with different Salesforce client lib versions...)
- resources --> custom resources (properties files, etc.)

## Kubernetes assets

### create secret for minio access (tokens for minio "streamsets-svc")

```sh
kubectl create secret generic streamsets-libspull-credentials \
    --namespace streamsetsdemos \
    --from-literal=access_key_id="<SOMEVALUE>" \
    --from-literal=secret_access_key="<SOMEVALUE>"
```

## Deploy supporting assets

Supporting assets are: 1 PVC + 2 JOBs (1 cron job for regular syncing, 1 simple job for easy ad-hoc running if/when needed)

```sh
kubectl --namespace streamsetsdemos apply -f ./manifests/pvc-pull-libraries.yaml
kubectl --namespace streamsetsdemos apply -f ./manifests/job-pull-libraries.yaml
kubectl --namespace streamsetsdemos apply -f ./manifests/cronjob-pull-libraries.yaml
```

You can re-run the ad-hoc job at will...

```sh
kubectl --namespace streamsetsdemos delete -f ./manifests/job-pull-libraries.yaml
kubectl --namespace streamsetsdemos apply -f ./manifests/job-pull-libraries.yaml
```

## Deploy the deployment in streamsets

The deployment file contains the following customization, in addition to the usual StreamSets items:
 - The PVC gets used by the data collector pod to create a Persistent Volume (PV),
 - PV gets mounted READ-ONLY to the right places on the data collector (specific Sx directories) using volumeMounts section
 - An init container to automatically pull from minio all the required assets onto the same Persistent Volume (PV) BEFORE the data collector container starts

And outside of that, the cronjob will refresh the data on that Persistent Volume (PV) regularly to keep thing fresh...

The file "./manifests/deployment-with-pvc.yaml" should be added to the StreamSets deployment (make sure to replace the UUID and ORGID in that file with what StreamSets expects)
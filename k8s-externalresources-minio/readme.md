k8s-externalresources-mgt-with-minio
=======================================

This is a small sample concept, where you centralize your external resources in an object storage (like Minio), and have all the StreamSets data collectors pull from that object store repo automatically to keep in sync.

In this sample/demo, we will use Minio deployed right on our K8 cluster.
BUT the very same concept could be easily adapted and achieved with AWS S3 or other object storage platforms.
You can find the same demo where we use AWS instead of Minio. find it [here](../k8s-externalresources-aws/)

## Prerequisites

You have a K8 install to test this with (ie. Rancher Desktop for example)
You have a streamSets control hub tenant

Let's do the work in the Streamsets namespace for simplicity (the namespace that has the streamSets Kubernetes agent)...
ie. namespace "streamsetsdemos"

If you already have Minio, no need for the next section for you...

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

Create bucket named "streamsets-externalresources":

```sh
mc mb --insecure myminio/streamsets-externalresources
```

Note: ensures "streamsets-svc" user has read/write access to that bucket

## Add StreamSets assets in Minio

Create the following 3 directories (names matter... we will use these same names in the K8 assets) in a bucket of choice
Each of these directory will get pulled from into a specific directory on the StreamSets data collector. 

- streamsets-libs-extras --> for extra libs to be added to specific stages (for example, new JDBC drivers for the stage "streamsets-datacollector-jdbc-lib"...)
- user-libs --> custom stage (for example, a custom salesforce stage "streamsets-datacollector-salesforce-lib" with different Salesforce client lib versions...)
- resources --> custom resources (properties files, etc.)

## Kubernetes assets
 
### Deploy core supporting assets

Core Supporting assets 1: Create secret for Minio access:

```sh
kubectl create secret generic streamsets-pull-external-resources-credentials \
    --namespace streamsetsdemos \
    --from-literal=access_key_id="<SOMEVALUE>" \
    --from-literal=secret_access_key="<SOMEVALUE>"
```

Core Supporting assets 2: Config map for the shell scripts used by the init container + scheduler...

```sh
kubectl --namespace streamsetsdemos apply -f ./manifests/cm-sync.yaml
```

## Deploy the deployment in streamsets

The deployment file contains the following customization, in addition to the usual StreamSets items:
 - The single EmptyDir volume gets used by all the containers in the pod
 - The volume gets mounted READ-ONLY to the right places on the data collector (specific Sx directories) using volumeMounts section
 - An init container to automatically pull from Minio Bucket all the required assets onto the volume BEFORE the data collector container starts
 - A simple side-car container to automatically pull the Minio Bucketassets at regular interval to keep the files in sync continuously.

The file "./manifests/deployment-template.yaml" should be added to the StreamSets deployment

IMPORTANT: 
- make sure to replace the placeholders "UUID" and "ORGID" in that file with what StreamSets expects
- Make sure to replace the AWS_S3_BUCKET_NAME if you named your bucket differently
- Make sure to replace the AWS_S3_ENDPOINT to go to Minio in the deployment... for example: https://minio.minio.svc.cluster.local:443
- Make sure to replace the AWS_S3_BUCKET_PREFIX if somehow, the streamsets resources are not at the root of the bucket
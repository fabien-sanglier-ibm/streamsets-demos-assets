k8-prometheus-jmx-exporter
=======================================

Sample to add a JMX-exporter to your SDC in Kubernetes

## Kubernetes assets
 
### Deploy core supporting assets

Config map for the exporter config:

```sh
kubectl create configmap streamsets-jmxexporter-configs \
    --namespace streamsetsdemos \
    --from-file=config.yml=./jmx_exporter_configs/config-simple-all.yaml
```

If you need to recreate the config map, you'll need to first delete it...do it as so:

```sh
kubectl delete configmap streamsets-jmxexporter-configs --namespace streamsetsdemos
```

### Deploy the deployment in streamsets

The deployment file contains the following customization, in addition to the usual StreamSets items:
 - A simple side-car container for the jmx exporter

The file "./manifests/deployment-jmxexporter-template.yaml" should be added to the StreamSets deployment
IMPORTANT: make sure to replace the placeholders "UUID" and "ORGID" in that file with what StreamSets expects


## Enable JMX exporter via JVM configs


In deployment > advanced configurations > JAVA configuration > field "Java Options", add:

```sh
-javaagent:/jmxexporter/jmx_prometheus_javaagent.jar=12345:/jmxexporter_configs/config.yml
```

and restart the engine...

Verify by running the following request:

```sh
curl http://localhost:12345/metrics
```

## Prometheus

Don't forget to annotate your resources so Prometheus will scrape your pod's /metrics endpoint:

annotations:
  "prometheus.io/scrape": "true"
  "prometheus.io/port": "12345"

## Troubleshooting: Enable jmxremote

You can expose the JMX objects in order to browse and build your JMX-exporter config for example:

```
-Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.port=9999 -Dcom.sun.management.jmxremote.local.only=true -Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false
```
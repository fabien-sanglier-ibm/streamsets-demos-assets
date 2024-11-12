k8-prometheus-jmx-exporter
=======================================

Sample to add a JMX-exporter to your SDC in Kubernetes

## Kubernetes assets

### Deploy core supporting assets

NOTE: The JMX exporter config (./jmx_exporter_configs/config-sdc.yaml) is very broad and will export all metrics with the following patterns:
 - metrics:name=jvm.*
 - metrics:name=sdc.pipeline.*

See relevant product doc at: https://docs.streamsets.com/portal/datacollector/latest/help/datacollector/UserGuide/Configuration/JMXMetrics-EnableExternalTools.html

Config map for the exporter config:

```sh
kubectl create configmap streamsets-jmxexporter-configs \
    --namespace streamsetsdemos \
    --from-file=config.yml=./jmx_exporter_configs/config-sdc.yaml
```

If you need to recreate the config map, you'll need to first delete it...do it as so:

```sh
kubectl delete configmap streamsets-jmxexporter-configs --namespace streamsetsdemos
```

### Deploy the deployment in streamsets

The deployment file contains the following customization, in addition to the usual StreamSets items:
- initContainers to copy the jmx-exporter java agent into the collector
- volumes and volume mounts to help achieve that
- add new containerPort entry with name "jmxexporter"

The file "./manifests/deployment-jmxexporter-template.yaml" should be added to the StreamSets deployment
IMPORTANT: make sure to replace the placeholders "UUID" and "ORGID" in that file with what StreamSets expects

## Enable JMX exporter via JVM configs

Now all the Kubernetes assets are added and available, we need to enable the exporter agent in the StreamSets engine...

In deployment > advanced configurations > JAVA configuration > field "Java Options", add:

```sh
-javaagent:/jmxexporter/jmx_prometheus_javaagent.jar=12345:/jmxexporter_configs/config.yml
```

And make sure to restart the engine!!

Verify by running the following request from the StreamSets collector container...

```sh
curl http://localhost:12345/metrics
```

This should return a long list of metrics in the expected format.

## Prometheus

Pod monitor for Prometheus to discover the StreamSets pods (this will not run if you don't have the prometheus stack installed, since it relies on the Prometheus CRD - monitoring.coreos.com)

```sh
kubectl --namespace streamsetsdemos apply -f ./manifests/pod-monitor.yaml
```

NOTE: Our pod monitor has the label "prometheus: scrape" to facilitate being selected by the Prometheus engine.

You should make sure the Prometheus deployment is set to select all the pod monitors with this labels.

## Troubleshooting: Enable jmxremote

NOTE: This is not needed by the setup... just for extra browsing of the metrics if you want to update the jmx-exporter configs for example...

You can expose the JMX objects in order to browse and build your JMX-exporter config for example:

```sh
-Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.port=10099 -Dcom.sun.management.jmxremote.rmi.port=10099 -Djava.rmi.server.hostname=localhost -Dcom.sun.management.jmxremote.local.only=false -Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false
```

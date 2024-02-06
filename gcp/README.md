## Spot-Checker GCP

1. Launch your controller Virtual Machine(Ubuntu OS, size is depends on number of workloads)
2. Clone this repository, and run setting

```
git clone https://github.com/ddps-lab/spot-checker.git
cd gcp
bash settings.sh
gcloud init
```

1. upload your service account key to VM
    1. If you do not have a service account key, check the link
    2. https://cloud.google.com/iam/docs/keys-create-delete#iam-service-account-keys-create-console
2. Modify  service account key path and spot running time, then run!

```
vi run_workloads_parallels.sh
./run_workload_parallel.sh
```
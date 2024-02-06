## Spot-Checker Azure

1. Launch your controller Virtual Machine(Ubuntu OS, size is depends on number of workloads)
2. Clone this repository, and run setting

```
git clone https://github.com/ddps-lab/spot-checker.git
cd azure
bash settings.sh
```

3. restart shell

```
exec -l $SHELL
```

4. az login

```
az login
```

5. Go to the link and enter the code

```
To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code ********* to authenticate.
```

6. When you enter the code, you get the following response

```
[
  {
    "cloudName": "AzureCloud",
    "homeTenantId": "********-****-****-****-************",
    "id": "********-****-****-****-************",
    "isDefault": true,
    "managedByTenants": [],
    "name": "spotchecker",
    "state": "Enabled",
    "tenantId": "********-****-****-****-************",
    "user": {
      "name": "example@spotchecker.onmicrosoft.com",
      "type": "user"
    }
  }
```

7. Modify AZURE_SUBSCRIPTION_ID to “id” of response  and spot running time, then run!

```
vi run_workloads_parallels.sh
./run_workload_parallel.sh
```
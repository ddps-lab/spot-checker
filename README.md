# Spot-Chcker

---

Spot-checker is collect stability data of Spot VMs across various public cloud vendors. Users can check the stability of Spot VMs on Amazon Web Services, Google Cloud, and Microsoft Azure. Researchers and developers can utilize spot-checker to gather data on the stability of Spot VMs, and analyze this data to select more stable and reliable Spot VMs.

### The spot-chcker work flow is:

1. User sample the workload set and save as file
2. Setting controller server using VM (The number of CPUs are same as the number of workloads)
3. Send workload file to controller server
4. Controller run spot chekcer experiment with workload file
5. Controller run parallel spot checker servers for 24 Hours
6. Controller save the log file of spot checkers to object storage
7. You can analyze the spot checker log as ground truth of spot status at that time

<img width="661" alt="spot-checker-overview" src="https://github.com/ddps-lab/spot-checker/assets/106056971/41bd167b-5a80-4488-8299-b4993eeb54ac">


### **How to start?**
- Check README file in each vendor's folder.

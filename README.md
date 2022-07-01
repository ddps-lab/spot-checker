# spot-checker
Check and save the health status log of spot instances concurrently in EC2

---
### Spot Checker Flow
1. User sample the workload set and save as file
2. Setting controller server using AWS EC2 (The number of CPUs are same as the number of workloads)
3. Send workload file to controller server
4. Controller run spot chekcer experiment with workload file
5. Controller run parallel spot checker servers for 24 Hours
6. Controller save the log file of spot checkers to AWS S3
7. You can analyze the spot checker log as ground truth of spot status at that time

<img width="600" alt="Screen Shot 2022-07-01 at 11 48 47 AM" src="https://user-images.githubusercontent.com/20024627/176817071-4baa0c53-d015-4673-93ec-dc66069a3759.png">

### 사용 방법
1. `generate_test_data.py`를 사용하여 `test_data` 폴더에 `Region.csv` 형식으로 측정할 Instance Type, Availability Zone을 기록합니다.
  - test_data를 생성하기 위해 `dataset/$region` 폴더에 `sps_{low,medium,high}.csv` 파일이 위치해야 합니다.
2. `regions.txt.sample`을 참고하여 자신이 측정하고자 하는 region들을 입력한 `region.txt`를 생성합니다.
  - `region.txt`에 있는 Region에 대해서 test_data 내 데이터를 읽어들여 측정 준비를 합니다.
3. `variables.py.sample`을 참고하여 `variables.py`를 생성해 사용자 변수 값을 설정합니다.
4. `get_all_vcpu_info_by_instance_types.py`, `get_all_vcpu_quota.py`를 실행시켜 인스턴스 타입별 vCPU개수와, 리전별 SpotInstance Quota를 가져옵니다.
5. `create_log_group.py`를 통해 CloudWatch Log Group을 생성합니다.
6. `create_tester.py`를 통해 측정 환경을 생성 및 시작합니다.
  - 생성시부터 비용이 청구되니 주의합니다.

### 삭제방법 
- `delete_tester.py`를 통해 측정 환경을 삭제합니다.
- `delete_log_group.py`를 실행하는 경우, 측정된 데이터가 모두 삭제될 수 있으니 유의 바랍니다.

---
### EC2 사용 방법
1. variables.py 작성 시, `use_ec2 = "true"`와 같이 설정합니다.
2. `create_tester.py`를 통해 테스트 환경을 생성합니다.
- EC2를 사용할 경우, `create_tester.py`를 통해 tester infra를 생성한 직후 즉시 테스트가 시작되지 않으며, 각 Region의 EC2 Instance에 접속해 추가 작업을 수행해야 합니다.
3. 테스트할 Region의 EC2 Console로 접속 후, 생성된 EC2 Instance에 SSH로 접속합니다.
4. tester.go, tester.sh, 해당 Region에서 테스트 할 `generate_test_data.py`를 통해 생성된 csv 파일을 복사합니다.
5. tester.sh의 내용 중, CSV의 File Name을 지정하는 `filename` 변수와, 생성 주기를 지정하는 `spawnrate` 변수를 설정합니다.
6. `chmod +x tester.sh` 후, `./tester.sh`를 통해 Script를 실행합니다. 만약, Shell Session이 끊어질 수 있는 상황이라면 `nohup ./tester.sh &` 명령을 사용합니다.
7. 실험을 종료하고 싶은 경우, `Ctrl + C`를 통해 Interrupt 하거나 `pkill tester.sh`를 통해 nohup으로 실행된 테스트 스크립트를 종료합니다.
### 사용 방법
1. `generate_test_data.py`를 사용하여 `test_data` 폴더에 `Region.csv` 형식으로 측정할 Instance Type, Availability Zone을 기록합니다.
  - test_data를 생성하기 위해 `dataset/$region` 폴더에 `sps_{low,medium,high}.csv` 파일이 위치해야 합니다.
2. `regions.txt.sample`을 참고하여 자신이 측정하고자 하는 region들을 입력한 `region.txt`를 생성합니다.
  - `region.txt`에 있는 Region에 대해서 test_data 내 데이터를 읽어들여 측정 준비를 합니다.
3. `variables.py.sample`을 참고하여 `variables.py`를 생성해 사용자 변수 값을 설정합니다.
4. `create_log_group.py`를 통해 CloudWatch Log Group을 생성합니다.
5. `create_tester.py`를 통해 측정 환경을 생성 및 시작합니다.
  - 생성시부터 비용이 청구되니 주의합니다.

### 삭제방법
- `delete_tester.py`를 통해 측정 환경을 삭제합니다.
- `delete_log_group.py`를 실행하는 경우, 측정된 데이터가 모두 삭제될 수 있으니 유의 바랍니다.
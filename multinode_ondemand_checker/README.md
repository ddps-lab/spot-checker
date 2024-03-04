## 사용 방법

1. variables.py.sample을 참고하여 variables.py를 생성해 사용자 변수 값을 설정합니다.
2. `python3 create_log_group.py`를 실행하여 로그 그룹을 생성합니다.
3. `python3 create_tester.py`를 실행하여 람다함수, 로그스트림 등을 생성합니다.
4. `python3 spot-health-checker.py`를 실행하여 스팟 인스턴스를 요청 실험을 시작합니다.

## 로그 저장

1. `export_log.py`를 실행하여 로그를 다운로드 받습니다.

    `log/sps1` 과 같은 경로를 미리 지정 해야합니다.

2. `json_to_csv.py`를 실행하여 json 형식의 로그를 csv 형식으로 변경합니다.

## 실험 종료 후

**삭제 전 실험 로그를 저장하였는지 확인 후 진행**

1. `python3 delete_tester.py`를 실행하여 람다함수, 로그스트림을 삭제합니다.
2. `python3 delete_log_group.py`를 실행하여 로그 그룹을 삭제합니다.

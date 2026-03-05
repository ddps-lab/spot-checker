## 사용 방법

1. variables.py.sample을 참고하여 variables.py를 생성해 사용자 변수 값을 설정합니다.
2. `python3 create_log_group.py`를 실행하여 로그 그룹을 생성합니다.
3. `python3 create_tester.py`를 실행하여 람다함수, 로그스트림 등을 생성합니다.
4. `python3 spot-health-checker.py` 또는 `python3 spot-health-checker-iter.py`를 실행하여 스팟 인스턴스 요청 실험을 시작합니다.
   - `spot-health-checker.py`: 단일 요청
   - `spot-health-checker-iter.py`: CSV 기반 다중 조합 요청 (권장)

## 로그 저장 및 결과 처리

### CloudWatch Logs → CSV 변환 (권장)
1. `python3 export_result.py`를 실행하여 CloudWatch Logs를 직접 CSV로 변환합니다.
   - CloudWatch Logs에서 모든 로그 스트림 조회
   - JSON 형식 이벤트 추출 및 S3 임시 저장
   - 지역별/이벤트 타입별로 정렬하여 `result_data/` 폴더에 저장
   - 모든 리전 통합 CSV 파일 생성: `change_result.csv`, `rebalance_result.csv`, `interruption_result.csv`, `count_result.csv`

2. (선택) `python3 export_result_each.py`를 실행하여 인스턴스별 성능 분석
   - 각 인스턴스 타입별 최대/최소 응답 시간 분석
   - 지역별 성능 비교 데이터 생성

### 기존 로그 파일 변환 (선택)
- `json_to_csv.py`를 실행하여 기존 JSON 형식 로그를 CSV로 변환합니다.
- `log/sps1` 과 같은 경로를 미리 지정해야 합니다.

## FIS (AWS Fault Injection Simulator) 실험
AWS Fault Injection Simulator를 사용하여 Spot 인스턴스의 실제 동작을 시뮬레이션합니다.

### FIS Template 생성
`python3 fis_tester.py --action setup`을 실행하여 FIS Template을 생성합니다.

생성되는 Template:
- **ec2-stop**: EC2 인스턴스 즉시 중단
- **spot-rebalance**: Spot 용량 부족 예상 신호 (PT5M)
- **spot-interruption**: Spot 2분 경고 후 중단 (PT2M)
- **instance-reboot**: 인스턴스 재부팅

### FIS 실험 실행
```bash
# Spot 재조정 실험
python3 fis_tester.py --action run --experiment-type spot-rebalance

# Spot 중단 실험
python3 fis_tester.py --action run --experiment-type spot-interruption

# EC2 중단 실험
python3 fis_tester.py --action run --experiment-type ec2-stop

# 인스턴스 재부팅 실험
python3 fis_tester.py --action run --experiment-type instance-reboot
```

실험 흐름:
1. FIS가 Template 검색
2. 태그 필터로 대상 인스턴스 선택 (`Environment={PREFIX}-spot-test`)
3. 신호 전송 → 인스턴스 상태 변화
4. Lambda 함수가 EventBridge로 변화 감지
5. CloudWatch Logs에 이벤트 기록

---

## 실험 종료 후

**삭제 전 실험 로그를 저장하였는지 확인 후 진행**

1. `python3 delete_tester.py`를 실행하여 람다함수, 로그스트림을 삭제합니다.
2. `python3 delete_log_group.py`를 실행하여 로그 그룹을 삭제합니다.

# Azure Spot VM Multinode Checker



- AWS Lambda에서 Azure Spot VM을 관리
- Evict 시 자동 재시작 (Deallocate 정책)
- 1분마다 VM 상태를 CloudWatch Logs에 기록
- 실험 종료 시간 도달 시 **자동 VM 및 NIC 삭제**
- 여러 Region/Zone 동시 실험 지원
- **ProvisioningState 로그만 저장** (불필요한 로그 제거)
- **공통 timestamp** 사용 (년월일시분) - GROUP BY 분석 용이
- **ARM64/x64 자동 감지** - VM 사이즈에 맞는 이미지 자동 선택

## 사전 준비

### 1. Azure Service Principal 생성

```bash
az login
az ad sp create-for-rbac --name "spot-multinode-checker" --role Contributor
```

출력된 값들을 `variables.py`에 설정:
- `appId` → `azure_client_id`
- `password` → `azure_client_secret`
- `tenant` → `azure_tenant_id`

### 2. Azure Subscription ID 확인

```bash
az account show --query id -o tsv
```

## 사용 방법

### 1. 설정 파일 생성

```bash
cp variables.py.sample variables.py
# variables.py 편집하여 인증 정보 및 VM 스펙 설정
```

### 2. AWS Lambda Layer 빌드

```bash
cd IaC
bash build_azure_layer.sh
cd ..
```

### 3. AWS 인프라 배포

```bash
# CloudWatch Log Group 생성
python3 create_log_group.py

# Lambda 함수 및 S3 버킷 배포
python3 create_tester.py
```

**배포되는 리소스:**
- Lambda 함수 (monitor-vm-status)
- EventBridge 스케줄 (1분마다)
- Lambda Layer (Azure SDK)
- S3 버킷 (로그 export용)
- IAM Role 및 정책

### 4. Azure Spot VM 생성

```bash
# 로컬에서 실행
python3 spot-health-checker.py
```

### 5. 실험 진행

Lambda가 자동으로 1분마다 VM 상태를 체크합니다.
- VM이 Evict되면 Deallocate 상태로 전환
- Capacity가 돌아오면 자동으로 재시작
- 실험 종료 시간이 지나면 **VM과 연결된 NIC를 자동으로 삭제**
- ProvisioningState가 있는 VM만 로그에 기록 (불필요한 로그 제거)
- 한 Lambda 실행의 모든 로그는 **공통 timestamp** 사용 (년월일시분)

### 6. 로그 추출

```bash
# CloudWatch Logs를 S3로 export 후 CSV로 변환
python3 export_result.py
```

**입력 예시:**
```
Enter the log start time (YYYY-MM-DD HH:MM): 2025-11-05 10:00
Enter the log end time (YYYY-MM-DD HH:MM): 2025-11-06 10:00
```

**출력:**
- `result_data/2025-11-05-AbCd/vm_status.csv`

**장점:**
- S3 export로 대량 로그 빠른 처리
- 자동 CSV 변환 및 병합
- TimestampUnix 기준 자동 정렬

### 7. 정리

```bash
# Lambda 함수 삭제
python3 delete_tester.py

# CloudWatch Log Group 삭제
python3 delete_log_group.py

# S3 버킷은 Terraform destroy 시 자동 삭제됨
```

## VM 스펙 형식

`variables.py`의 `vm_specs`는 **리스트 형식**을 따릅니다:

```
Tier,InstanceType,Location,Zone,Count
```

### 예시

**1. Display Name 사용 (권장)**
```python
vm_specs = [
    "Standard,E2_v4,US West 3,2,10",      # US West 3 Zone 2에 10개
    "Standard,D2s_v3,Korea Central,1,5",  # Korea Central Zone 1에 5개
    "Standard,D4s_v3,Japan East,3,1",     # Japan East Zone 3에 1개
]
```

**2. API Name 사용**
```python
vm_specs = [
    "Standard,E2_v4,westus3,2,10",
    "Standard,D2s_v3,koreacentral,1,5",
]
```

### 필드 설명

- **Tier**: Standard, Basic 등
- **InstanceType**: E2_v4, D2s_v3 등 (언더스코어 사용)
- **Location**: Azure location 이름
  - Display Name: "US West 3", "Korea Central" (공백 포함, 자동 변환)
  - API Name: "westus3", "koreacentral" (공백 없음, 소문자)
- **Zone**: Availability Zone (1, 2, 3)
- **Count**: 해당 스펙으로 생성할 VM 개수 (정수)

### 하위 호환성

Count를 생략하면 자동으로 1개로 간주:
```python
vm_specs = [
    "Standard,D2s_v3,Korea Central,1",  # Count 없음 -> 1개
]
```

### 주요 Location 매핑표

| Display Name | API Name |
|--------------|----------|
| US West 3 | westus3 |
| US East | eastus |
| Korea Central | koreacentral |
| Japan East | japaneast |
| West Europe | westeurope |
| Southeast Asia | southeastasia |

전체 리전 목록: [Azure Regions](https://azure.microsoft.com/en-us/explore/global-infrastructure/geographies/)

### 대량 생성 예시

```python
vm_specs = [
    "Standard,D2s_v3,Korea Central,1,50",  # x64 VM 50개
    "Standard,D2s_v3,US West 3,1,30",      # x64 VM 30개
    "Standard,E2_v4,Japan East,2,20",      # x64 VM 20개
]
```
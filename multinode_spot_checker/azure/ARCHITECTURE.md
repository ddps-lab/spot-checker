# Azure Spot VM Multinode Checker - 아키텍처 및 파일 구조

## 📁 전체 디렉토리 구조

```
multinode_spot_checker/azure/
├── variables.py.sample          # 설정 샘플 파일
├── README.md                    # 사용자 가이드
├── ARCHITECTURE.md              # 본 문서 (아키텍처 설명)
├── .gitignore                   # Git 무시 파일
│
├── spot-health-checker.py       # [로컬 실행] Azure Spot VM 생성
├── azure_auth.py                # [헬퍼] Azure 인증 모듈
│
├── create_log_group.py          # [배포] CloudWatch Log Group 생성
├── delete_log_group.py          # [정리] CloudWatch Log Group 삭제
├── create_tester.py             # [배포] Lambda 함수 배포 (Terraform)
├── delete_tester.py             # [정리] Lambda 함수 삭제 (Terraform)
│
├── export_result.py             # [결과] CloudWatch Logs 추출
├── json_to_csv.py               # [결과] JSON → CSV 변환
│
├── auto.sh                      # [자동화] 전체 배포 및 VM 생성
├── autodel.sh                   # [자동화] 전체 정리
│
└── IaC/                         # Terraform Infrastructure as Code
    ├── provider.tf              # AWS Provider 설정
    ├── var.tf                   # 변수 정의
    ├── main.tf                  # 메인 모듈 호출
    ├── role.tf                  # Lambda IAM Role
    ├── azure_layer.tf           # Azure SDK Lambda Layer
    │
    ├── build_azure_layer.sh     # [빌드] Azure SDK Layer 빌드
    ├── requirements_azure_layer.txt  # Azure SDK 패키지 목록
    │
    ├── monitor-vm-status.py     # [Lambda 코드] VM 상태 모니터링
    └── monitor-vm-status/       # [Lambda 모듈] Terraform 설정
        ├── var.tf               # 모듈 변수
        ├── data.tf              # 데이터 소스 (ZIP 생성)
        └── lambda.tf            # Lambda 함수 및 EventBridge
```

---

## 🔧 주요 파일 역할

### **1. 설정 파일**

#### `variables.py.sample`
- **역할**: 실험 설정 템플릿
- **내용**:
  - AWS 인증 정보 (Lambda 배포용)
  - Azure 인증 정보 (Service Principal)
  - VM 스펙 (CSV 형식)
  - 실험 시간 설정
- **사용**: `cp variables.py.sample variables.py` 후 수정

---

### **2. 로컬 실행 스크립트**

#### `spot-health-checker.py`
- **역할**: Azure Spot VM 생성 (로컬에서 실행)
- **주요 기능**:
  1. `variables.py`의 `vm_specs` 파싱
  2. Location별로 Resource Group, VNet, Subnet 자동 생성
  3. Spot VM 생성 (Deallocate 정책)
  4. Tag에 `experiment_end_time` 기록
- **실행**: `python3 spot-health-checker.py`

#### `azure_auth.py`
- **역할**: Azure SDK 인증 헬퍼
- **기능**:
  - `ClientSecretCredential` 생성
  - Compute/Network/Resource 클라이언트 반환
  - `get_azure_clients()` 편의 함수 제공

---

### **3. AWS 인프라 배포 스크립트**

#### `create_log_group.py`
- **역할**: CloudWatch Log Group 및 Log Stream 생성
- **API**: `boto3.client('logs')`
- **실행**: `python3 create_log_group.py`

#### `create_tester.py`
- **역할**: Terraform으로 Lambda 함수 배포
- **과정**:
  1. Terraform workspace 생성
  2. `terraform init`
  3. `terraform apply` (Azure 인증 정보 전달)
- **실행**: `python3 create_tester.py`

#### `delete_log_group.py` / `delete_tester.py`
- **역할**: 생성한 리소스 정리
- **실행**: 각각 독립 실행 가능

---

### **4. 결과 추출 스크립트**

#### `export_result.py`
- **역할**: CloudWatch Logs에서 로그 추출
- **출력**: `result_data/YYYY-MM-DD-HHMM/vm_status.json`
- **API**: `logs_client.get_log_events()`

#### `json_to_csv.py`
- **역할**: JSON 로그를 CSV로 변환
- **입력**: `result_data/**/*.json`
- **출력**: 같은 경로에 `.csv` 파일 생성

---

### **5. Terraform IaC (Infrastructure as Code)**

#### `provider.tf`
```hcl
# AWS Provider 설정
provider "aws" {
  region  = var.region
  profile = var.awscli_profile
}
```

#### `var.tf`
- **역할**: Terraform 변수 정의
- **주요 변수**:
  - `region`, `prefix`, `awscli_profile`
  - `log_group_name`, `log_stream_name`
  - `azure_subscription_id`, `azure_tenant_id`, etc.

#### `role.tf`
- **역할**: Lambda 실행 IAM Role
- **권한**:
  - CloudWatch Logs 쓰기
  - Lambda 기본 실행 권한

#### `azure_layer.tf`
- **역할**: Azure SDK Lambda Layer 정의
- **패키지**: `azure_sdk_layer.zip`
- **내용**: azure-identity, azure-mgmt-compute, etc.

#### `main.tf`
- **역할**: 메인 모듈 호출
- **모듈**: `monitor-vm-status`

---

### **6. Lambda 함수**

#### `monitor-vm-status.py`
- **역할**: Azure VM 상태 모니터링 (1분마다 실행)
- **주요 로직**:
  ```python
  1. PREFIX로 시작하는 모든 Resource Group 찾기
  2. 각 VM의 PowerState 조회 (running/deallocated/stopped)
  3. CloudWatch Logs에 상태 기록
  4. experiment_end_time Tag 확인
  5. 만료된 VM 삭제 (begin_delete)
  ```
- **환경변수**:
  - `LOG_GROUP_NAME`, `LOG_STREAM_NAME`
  - `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, etc.
- **트리거**: EventBridge Schedule (rate(1 minute))

#### `monitor-vm-status/` (Terraform 모듈)
- **`data.tf`**: Lambda 코드 ZIP 생성
- **`lambda.tf`**: Lambda 함수, EventBridge Rule, Permission 정의
- **`var.tf`**: 모듈 입력 변수

---

### **7. Lambda Layer 빌드**

#### `build_azure_layer.sh`
```bash
# Azure SDK를 Lambda Layer 형식으로 패키징
mkdir -p python/lib/python3.11/site-packages
pip install -r requirements_azure_layer.txt -t python/lib/python3.11/site-packages
zip -r azure_sdk_layer.zip python
```

#### `requirements_azure_layer.txt`
```
azure-identity==1.15.0
azure-mgmt-compute==30.5.0
azure-mgmt-network==25.2.0
azure-mgmt-resource==23.0.1
python-dateutil==2.8.2
```

---

## 실행 방법

### **1. 초기 설정**
```bash
# 1. Azure Service Principal 생성
az ad sp create-for-rbac --name "spot-multinode-checker" --role Contributor

# 2. variables.py 설정
cp variables.py.sample variables.py
# (Azure 인증 정보 입력)

# 3. Azure SDK Layer 빌드
cd IaC
bash build_azure_layer.sh
cd ..
```

### **2. 인프라 배포**
```bash
# AWS Lambda 배포
python3 create_log_group.py  # CloudWatch Logs
python3 create_tester.py      # Lambda + EventBridge
```

### **3. 실험 시작**
```bash
# Azure Spot VM 생성 (로컬)
python3 spot-health-checker.py
```

### **4. 모니터링**
- Lambda가 자동으로 1분마다 실행
- CloudWatch Logs에 VM 상태 기록
- 만료된 VM 자동 삭제

### **5. 결과 추출**
```bash
python3 export_result.py  # JSON 추출
python3 json_to_csv.py    # CSV 변환
```

### **6. 정리**
```bash
python3 delete_tester.py    # Lambda 삭제
python3 delete_log_group.py # Logs 삭제
```

## 로그 형식

### **CloudWatch Logs JSON**
```json
{
  "Timestamp": "2025-11-05 15:30:00",
  "TimestampUnix": 1730821800.0,
  "ResourceGroup": "azure-multinode-westus3-rg",
  "VMName": "azure-multinode-vm-001",
  "VMSize": "Standard_E2_v4",
  "Location": "westus3",
  "Zone": "2",
  "Priority": "Spot",
  "PowerState": "running",
  "ProvisioningState": "succeeded"
}
```

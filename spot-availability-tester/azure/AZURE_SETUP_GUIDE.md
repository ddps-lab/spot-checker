# Azure Spot Availability Tester - 설정 가이드

### 1단계: Azure Service Principal 생성

Azure CLI를 사용하여 Service Principal을 생성합니다 (AWS의 access_key/secret_key와 동일한 역할):

```bash
# Azure CLI 설치 확인
az --version

# Azure 로그인
az login

# 현재 구독 ID 확인
az account show --query id -o tsv

# Service Principal 생성
az ad sp create-for-rbac \
  --name "spot-availability-tester" \
  --role "Contributor" \
  --scopes "/subscriptions/YOUR_SUBSCRIPTION_ID"
```

**출력 예시:**
```json
{
  "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "displayName": "spot-availability-tester",
  "password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### 2단계: variables.py 설정

위에서 받은 값들을 `variables.py`에 입력:

```bash
cp variables.py.sample variables.py
vi variables.py
```

```python
# AWS 설정 (CloudWatch 로그용 - 기존 유지)
awscli_profile = "your-profile"
prefix = "your-prefix"
log_stream_name = "your-log-stream"
use_ec2 = "false"
spawn_rate = 1
describe_rate = 0.1

# Azure 인증 (Service Principal)
azure_subscription_id = "YOUR_SUBSCRIPTION_ID"  # az account show --query id
azure_tenant_id = "tenant"                       # 위 출력의 tenant 값
azure_client_id = "appId"                        # 위 출력의 appId 값
azure_client_secret = "password"                 # 위 출력의 password 값
```

### 3단계: Python 의존성 설치

```bash
pip install azure-identity azure-mgmt-compute azure-mgmt-network azure-mgmt-resource
```

### 4단계: 인증 테스트

```bash
python azure_auth.py
```

**인증 성공 시 출력:**
```
✅ Azure 인증 성공!
   Subscription ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   Tenant ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   Client ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

✅ Compute Client 생성 성공!
```

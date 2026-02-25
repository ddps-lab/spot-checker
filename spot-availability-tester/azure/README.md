### 사용 방법
1. **Azure 인증 설정**
   - `variables.py.sample`을 참고하여 `variables.py`를 생성하고 Azure Service Principal 정보를 입력합니다.
   - `AZURE_SETUP_GUIDE.md`를 참고하여 Azure 인증 정보를 얻을 수 있습니다.

2. **테스트 대상 CSV 준비**
   - 4개 컬럼 형식: `InstanceTier,InstanceType,Region,AZ`
   - 예시: `Standard,E64-16ds_v4,US West 3,1`

3. **AWS 리전 설정**
   - `regions.txt.sample`을 참고하여 `regions.txt`를 생성합니다.
   - AWS 인프라를 배포할 리전을 지정합니다 (테스트 실행 위치).

4. **Azure 테스트 리전 설정**
   - `variables.py`에서 `azure_test_regions`, `azure_nic_pool_size`를 설정합니다.

5. **의존성 설치** ⭐ (최초 1회 필수)
   ```bash
   # Python Azure SDK (NIC 생성용)
   pip install azure-identity azure-mgmt-network
   
   # Lambda Layer 빌드
   cd IaC
   ./build_azure_layer.sh
   ```

6. **CloudWatch Log Group 생성**
   ```bash
   python create_log_group.py
   ```

7. **테스트 인프라 생성**
   ```bash
   python create_tester.py
   ```
   - Terraform: AWS Lambda, EC2, Azure RG/VNet/Subnet 생성
   - Python asyncio: Azure NIC 풀 고속 생성 (100개 기준 ~3-5분)

### 삭제방법 
- `delete_tester.py`를 통해 측정 환경을 삭제합니다.
- `delete_log_group.py`를 실행하는 경우, 측정된 데이터가 모두 삭제될 수 있으니 유의 바랍니다.

---
### EC2 사용 방법 (use_ec2 = "true")
1. **variables.py 설정**
   - `use_ec2 = "true"`로 설정합니다.

2. **인프라 생성**
   - `create_tester.py`를 통해 테스트 환경을 생성합니다.
   - EC2 모드에서는 인프라 생성 직후 즉시 테스트가 시작되지 않습니다.

3. **EC2 접속**
   - AWS Console에서 생성된 EC2 인스턴스에 SSH로 접속합니다.

4. **파일 복사**
   - `tester.go`: Lambda 호출 클라이언트
   - `tester.sh`: 테스트 오케스트레이션 스크립트
   - `azure.csv`: Azure VM 테스트 데이터 (4컬럼 형식)

5. **tester.sh 설정**
   - `filename`: 테스트할 CSV 파일명 (예: `azure.csv`)
   - `spawnrate`: 테스트 실행 주기 (분)
   - `function_url`: Lambda Function URL (환경변수로 자동 설정됨)

6. **테스트 실행**
   ```bash
   chmod +x tester.sh
   ./tester.sh
   ```
   - 백그라운드 실행: `nohup ./tester.sh &`

7. **테스트 종료**
   - 포그라운드: `Ctrl + C`
   - 백그라운드: `pkill -f tester.sh`

---
### 주요 구성 요소
- **AWS Lambda**: Azure VM 생성/삭제 테스트 실행
- **AWS EC2**: tester.go/tester.sh 실행 (Lambda 호출)
- **Azure NIC Pool**: Python asyncio로 고속 생성 (Terraform 대비 7-15배 빠름)
- **CloudWatch Logs**: 테스트 결과 저장
"""
Azure Authentication Helper
AWS의 access_key/secret_key처럼 간단하게 Azure에 인증하는 모듈
"""

from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
import variables


class AzureAuth:
    """
    Azure 인증을 간단하게 처리하는 클래스
    
    Usage:
        auth = AzureAuth()
        compute_client = auth.get_compute_client()
        network_client = auth.get_network_client()
    """
    
    def __init__(self):
        # variables.py에서 인증 정보 로드
        self.subscription_id = variables.azure_subscription_id
        self.tenant_id = variables.azure_tenant_id
        self.client_id = variables.azure_client_id
        self.client_secret = variables.azure_client_secret
        
        # 인증 정보 검증
        if not all([self.subscription_id, self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError(
                "Azure 인증 정보가 variables.py에 설정되지 않았습니다.\n"
                "다음 명령어로 Service Principal을 생성하세요:\n"
                "az ad sp create-for-rbac --name 'spot-tester' --role Contributor "
                f"--scopes '/subscriptions/{self.subscription_id or 'YOUR_SUBSCRIPTION_ID'}'"
            )
        
        # Credential 객체 생성 (AWS의 access_key/secret_key와 동일한 역할)
        self.credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
    
    def get_compute_client(self, region=None):
        """
        Compute Management Client 반환
        VM 생성/삭제/조회 등에 사용
        
        Args:
            region: 사용하지 않음 (Azure는 subscription 레벨에서 모든 리전 접근 가능)
        """
        return ComputeManagementClient(self.credential, self.subscription_id)
    
    def get_network_client(self, region=None):
        """
        Network Management Client 반환
        VNet, Subnet, NSG 등에 사용
        """
        return NetworkManagementClient(self.credential, self.subscription_id)
    
    def get_resource_client(self, region=None):
        """
        Resource Management Client 반환
        Resource Group 관리에 사용
        """
        return ResourceManagementClient(self.credential, self.subscription_id)
    
    @property
    def subscription(self):
        """구독 ID 반환"""
        return self.subscription_id


def get_azure_clients():
    """
    간편하게 모든 클라이언트를 한 번에 가져오기
    
    Returns:
        tuple: (compute_client, network_client, resource_client, subscription_id)
    
    Usage:
        compute, network, resource, sub_id = get_azure_clients()
    """
    auth = AzureAuth()
    return (
        auth.get_compute_client(),
        auth.get_network_client(),
        auth.get_resource_client(),
        auth.subscription
    )


# 환경변수로도 사용 가능하도록 (Lambda에서 유용)
def get_credential_from_env():
    """
    환경변수에서 직접 인증 정보를 가져오는 방법
    Lambda 환경변수 설정 시 유용
    
    Environment Variables:
        AZURE_SUBSCRIPTION_ID
        AZURE_TENANT_ID
        AZURE_CLIENT_ID
        AZURE_CLIENT_SECRET
    """
    import os
    
    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    tenant_id = os.getenv('AZURE_TENANT_ID')
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    
    if not all([subscription_id, tenant_id, client_id, client_secret]):
        raise ValueError("환경변수에 Azure 인증 정보가 설정되지 않았습니다.")
    
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )
    
    return credential, subscription_id


if __name__ == "__main__":
    # 테스트: 인증이 올바르게 설정되었는지 확인
    try:
        auth = AzureAuth()
        print("✅ Azure 인증 성공!")
        print(f"   Subscription ID: {auth.subscription}")
        print(f"   Tenant ID: {auth.tenant_id}")
        print(f"   Client ID: {auth.client_id}")
        
        # 실제 API 호출 테스트
        compute_client = auth.get_compute_client()
        print("\n✅ Compute Client 생성 성공!")
        
        # 사용 가능한 VM 사이즈 목록 가져오기 (간단한 API 테스트)
        # locations = compute_client.resource_skus.list()
        # print("✅ Azure API 호출 성공!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


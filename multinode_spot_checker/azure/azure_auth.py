"""
Azure Authentication Helper

로컬 스크립트에서 Azure SDK를 쉽게 사용하기 위한 헬퍼 모듈
AWS의 boto3.Session과 유사한 역할
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
                "az ad sp create-for-rbac --name 'spot-multinode-checker' --role Contributor"
            )
        
        # Credential 객체 생성
        self.credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
    
    def get_compute_client(self):
        """Compute Management Client 반환 (VM 관리)"""
        return ComputeManagementClient(self.credential, self.subscription_id)
    
    def get_network_client(self):
        """Network Management Client 반환 (VNet, NIC 관리)"""
        return NetworkManagementClient(self.credential, self.subscription_id)
    
    def get_resource_client(self):
        """Resource Management Client 반환 (Resource Group 관리)"""
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


if __name__ == "__main__":
    # 테스트: 인증이 올바르게 설정되었는지 확인
    try:
        auth = AzureAuth()
        print("✅ Azure 인증 성공!")
        print(f"   Subscription ID: {auth.subscription}")
        print(f"   Tenant ID: {auth.tenant_id}")
        print(f"   Client ID: {auth.client_id}")
        
        compute_client = auth.get_compute_client()
        print("\n✅ Compute Client 생성 성공!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


from typing import Optional

import httpx


class PulsarAdminClient:
    def __init__(self, admin_url: str, auth_token: Optional[str] = None):
        """
        初始化 Pulsar Admin 客户端。

        :param admin_url: Pulsar Admin REST API 的基础 URL，例如 "http://localhost:8080"
        :param auth_token: 可选的身份验证令牌，如果启用了身份验证
        """
        self.admin_url = admin_url.rstrip('/')
        self.auth_token = auth_token
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if auth_token:
            self.headers['Authorization'] = f'Bearer {auth_token}'

    async def get(self, path: str) -> dict:
        """
        发送 GET 请求。

        :param path: API 路径，例如 "/admin/v2/brokers/health"
        :return: 响应的 JSON 数据
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{self.admin_url}{path}', headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, json: Optional[dict] = None):
        """
        发送 POST 请求。

        :param path: API 路径
        :param json: 可选的 JSON 数据
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(f'{self.admin_url}{path}', headers=self.headers, json=json)
            response.raise_for_status()

    async def put(self, path: str, json: Optional[dict] = None):
        """
        发送 PUT 请求。

        :param path: API 路径
        :param json: 可选的 JSON 数据
        """
        async with httpx.AsyncClient() as client:
            response = await client.put(f'{self.admin_url}{path}', headers=self.headers, json=json)
            response.raise_for_status()

    async def delete(self, path: str):
        """
        发送 DELETE 请求。

        :param path: API 路径
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(f'{self.admin_url}{path}', headers=self.headers)
            response.raise_for_status()

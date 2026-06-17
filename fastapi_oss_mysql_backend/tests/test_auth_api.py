"""认证接口测试。"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user) -> None:
    """登录成功。"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin1234"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user) -> None:
    """密码错误。"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpass"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] != 0


@pytest.mark.asyncio
async def test_login_user_not_exist(client: AsyncClient) -> None:
    """用户不存在。"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "Whatever1234"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, admin_user) -> None:
    """刷新 Token。"""
    # 1. 先登录
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin1234"},
    )
    refresh_token = login_resp.json()["data"]["refresh_token"]

    # 2. 刷新
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient, admin_user) -> None:
    """获取当前用户信息。"""
    resp = await client.get("/api/v1/users/me", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == "admin"
    assert data["is_superuser"] is True


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient) -> None:
    """未授权访问。"""
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401

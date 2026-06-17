"""用户管理接口测试。"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient, admin_user) -> None:
    """创建用户成功。"""
    resp = await client.post(
        "/api/v1/users",
        headers=auth_headers(admin_user),
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewUser123",
            "full_name": "新用户",
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_create_user_permission_denied(client: AsyncClient, test_user) -> None:
    """非超级管理员无法创建用户。"""
    resp = await client.post(
        "/api/v1/users",
        headers=auth_headers(test_user),
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewUser123",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_user_duplicate(client: AsyncClient, admin_user) -> None:
    """用户名重复。"""
    await client.post(
        "/api/v1/users",
        headers=auth_headers(admin_user),
        json={
            "username": "dupuser",
            "email": "dup1@example.com",
            "password": "DupUser123",
        },
    )
    resp = await client.post(
        "/api/v1/users",
        headers=auth_headers(admin_user),
        json={
            "username": "dupuser",
            "email": "dup2@example.com",
            "password": "DupUser123",
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_user_weak_password(client: AsyncClient, admin_user) -> None:
    """弱密码。"""
    resp = await client.post(
        "/api/v1/users",
        headers=auth_headers(admin_user),
        json={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "123",  # 太短
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, admin_user, test_user) -> None:
    """分页查询用户。"""
    resp = await client.get(
        "/api/v1/users?page=1&page_size=10",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_get_user_detail(client: AsyncClient, admin_user, test_user) -> None:
    """获取用户详情。"""
    resp = await client.get(
        f"/api/v1/users/{test_user.id}",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, admin_user, test_user) -> None:
    """更新用户。"""
    resp = await client.put(
        f"/api/v1/users/{test_user.id}",
        headers=auth_headers(admin_user),
        json={"full_name": "更新的名字"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["full_name"] == "更新的名字"


@pytest.mark.asyncio
async def test_delete_self_forbidden(client: AsyncClient, admin_user) -> None:
    """不能删除自己。"""
    resp = await client.delete(
        f"/api/v1/users/{admin_user.id}",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, admin_user, test_user) -> None:
    """删除用户。"""
    resp = await client.delete(
        f"/api/v1/users/{test_user.id}",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200

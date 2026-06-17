"""文件上传接口测试。"""
from __future__ import annotations

import io

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_upload_file_success(client: AsyncClient, test_user) -> None:
    """上传文件成功。"""
    # 构造文件
    file_content = b"Hello, OSS! " * 100
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

    resp = await client.post(
        "/api/v1/files/upload",
        headers=auth_headers(test_user),
        files=files,
        data={"prefix": "tests", "business_type": "demo"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["original_filename"] == "test.txt"
    assert data["file_size"] == len(file_content)
    assert "oss_key" in data


@pytest.mark.asyncio
async def test_upload_file_unauthorized(client: AsyncClient) -> None:
    """未授权上传。"""
    file_content = b"test"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_empty_file(client: AsyncClient, test_user) -> None:
    """上传空文件失败。"""
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}

    resp = await client.post(
        "/api/v1/files/upload",
        headers=auth_headers(test_user),
        files=files,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_file_info(client: AsyncClient, test_user) -> None:
    """获取文件详情。"""
    # 上传
    file_content = b"test content"
    files = {"file": ("info.txt", io.BytesIO(file_content), "text/plain")}
    upload_resp = await client.post(
        "/api/v1/files/upload",
        headers=auth_headers(test_user),
        files=files,
    )
    file_id = upload_resp.json()["data"]["id"]

    # 查询
    resp = await client.get(
        f"/api/v1/files/{file_id}",
        headers=auth_headers(test_user),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == file_id


@pytest.mark.asyncio
async def test_list_my_files(client: AsyncClient, test_user) -> None:
    """查询我的文件。"""
    # 上传几个
    for i in range(3):
        files = {"file": (f"file{i}.txt", io.BytesIO(b"x"), "text/plain")}
        await client.post(
            "/api/v1/files/upload",
            headers=auth_headers(test_user),
            files=files,
        )

    # 查询
    resp = await client.get(
        "/api/v1/files?page=1&page_size=10",
        headers=auth_headers(test_user),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_delete_file(client: AsyncClient, test_user) -> None:
    """删除文件。"""
    files = {"file": ("del.txt", io.BytesIO(b"x"), "text/plain")}
    upload_resp = await client.post(
        "/api/v1/files/upload",
        headers=auth_headers(test_user),
        files=files,
    )
    file_id = upload_resp.json()["data"]["id"]

    resp = await client.delete(
        f"/api/v1/files/{file_id}",
        headers=auth_headers(test_user),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient) -> None:
    """存活探针。"""
    resp = await client.get("/api/v1/health/live")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "alive"

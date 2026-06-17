"""用户业务逻辑。"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BusinessException, ErrorCode
from src.core.security import hash_password
from src.crud.user import user_crud
from src.db.models.user import User
from src.schemas.user_schema import UserCreateRequest, UserUpdateRequest


class UserService:
    """用户服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user(self, data: UserCreateRequest) -> User:
        """创建用户。"""
        # 检查用户名/邮箱是否已存在
        if await user_crud.get_by_username(self.db, data.username):
            raise BusinessException(
                code=ErrorCode.USER_EXISTS, message=f"用户名 {data.username} 已存在"
            )
        if await user_crud.get_by_email(self.db, data.email):
            raise BusinessException(
                code=ErrorCode.USER_EXISTS, message=f"邮箱 {data.email} 已被使用"
            )

        user = await user_crud.create(
            self.db,
            username=data.username,
            email=data.email,
            full_name=data.full_name,
            phone=data.phone,
            hashed_password=hash_password(data.password),
            is_active=True,
        )
        await self.db.commit()
        return user

    async def get_user(self, user_id: int) -> User:
        """获取用户。"""
        user = await user_crud.get(self.db, user_id)
        if user is None:
            raise BusinessException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        return user

    async def list_users(
        self,
        *,
        keyword: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        """分页查询用户。"""
        return await user_crud.list_users(
            self.db,
            keyword=keyword,
            is_active=is_active,
            offset=offset,
            limit=limit,
        )

    async def update_user(self, user_id: int, data: UserUpdateRequest) -> User:
        """更新用户。"""
        user = await self.get_user(user_id)

        # 检查邮箱是否被其他人占用
        if data.email and data.email != user.email:
            existing = await user_crud.get_by_email(self.db, data.email)
            if existing and existing.id != user_id:
                raise BusinessException(
                    code=ErrorCode.USER_EXISTS, message=f"邮箱 {data.email} 已被使用"
                )

        update_data = data.model_dump(exclude_unset=True)
        user = await user_crud.update(self.db, user_id, **update_data)
        await self.db.commit()
        return user  # type: ignore[return-value]

    async def delete_user(self, user_id: int) -> None:
        """删除用户（物理删除）。"""
        if not await user_crud.delete(self.db, user_id):
            raise BusinessException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        await self.db.commit()

    async def change_password(
        self, user_id: int, *, old_password: str, new_password: str
    ) -> None:
        """修改密码。"""
        from src.core.security import verify_password

        user = await self.get_user(user_id)
        if not verify_password(old_password, user.hashed_password):
            raise BusinessException(
                code=ErrorCode.PASSWORD_ERROR, message="原密码错误"
            )
        user.hashed_password = hash_password(new_password)
        await self.db.commit()

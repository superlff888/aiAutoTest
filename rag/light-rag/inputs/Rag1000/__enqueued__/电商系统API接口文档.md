# 电商系统API接口文档

## 文档说明
- **版本**: v1.0
- **最后更新**: 2022-08-15
- **接口BaseURL**: `https://api.mstest.com`

### 1、认证方式
所有需要认证的接口需要在请求头中添加：
```
Authorization: Bearer {jwt_token}
```

### 2、异常返回

#### 1. 异常响应标准结构

所有异常响应均采用以下JSON格式：

```python
{
  "success": false,
  "code": "COMMON_0001",
  "message": "请求参数校验失败",
}
```

#### 2. HTTP状态码使用规范

| 状态码                    | 使用场景                         |
| :------------------------ | :------------------------------- |
| 400 Bad Request           | 客户端请求错误（参数校验失败等） |
| 401 Unauthorized          | 未认证或Token无效                |
| 403 Forbidden             | 无权限访问资源                   |
| 404 Not Found             | 资源不存在                       |
| 409 Conflict              | 资源冲突（如重复创建）           |
| 422 Unprocessable Entity  | 业务逻辑验证失败                 |
| 429 Too Many Requests     | 请求过于频繁                     |
| 500 Internal Server Error | 服务器内部错误                   |
| 503 Service Unavailable   | 服务暂时不可用                   |

#### 3. 错误代码全集

| 模块         | 错误代码（code） | HTTP状态码 | 描述（message）    |
| :----------- | :--------------- | :--------- | :----------------- |
| **通用错误** |                  |            |                    |
|              | COMMON_0001      | 400        | 请求参数校验失败   |
|              | COMMON_0002      | 401        | 未提供认证信息     |
|              | COMMON_0003      | 401        | Token已过期        |
|              | COMMON_0004      | 401        | Token无效          |
|              | COMMON_0005      | 403        | 权限不足           |
|              | COMMON_0006      | 404        | 资源不存在         |
|              | COMMON_0007      | 409        | 资源已存在         |
|              | COMMON_0008      | 422        | 业务规则校验失败   |
|              | COMMON_0009      | 429        | 请求过于频繁       |
|              | COMMON_9999      | 500        | 系统内部错误       |
| **用户模块** |                  |            |                    |
|              | USER_0001        | 400        | 用户名已存在       |
|              | USER_0002        | 400        | 邮箱已注册         |
|              | USER_0003        | 400        | 手机号已绑定       |
|              | USER_0004        | 401        | 用户名或密码错误   |
|              | USER_0005        | 403        | 账户已被封禁       |
|              | USER_0006        | 403        | 验证码错误         |
|              | USER_0007        | 403        | 验证码已过期       |
|              | USER_0008        | 429        | 验证码发送过于频繁 |
| **商品模块** |                  |            |                    |
|              | PRODUCT_0001     | 404        | 商品不存在         |
|              | PRODUCT_0002     | 422        | 商品已下架         |
|              | PRODUCT_0003     | 422        | 库存不足           |
|              | PRODUCT_0004     | 403        | 商品禁止购买       |
| **订单模块** |                  |            |                    |
|              | ORDER_0001       | 404        | 订单不存在         |
|              | ORDER_0002       | 422        | 订单状态异常       |
|              | ORDER_0003       | 403        | 订单不属于当前用户 |
|              | ORDER_0004       | 422        | 支付金额不匹配     |
|              | ORDER_0005       | 409        | 重复支付           |
| **支付模块** |                  |            |                    |
|              | PAYMENT_0001     | 400        | 支付方式不支持     |
|              | PAYMENT_0002     | 402        | 支付失败           |
|              | PAYMENT_0003     | 409        | 重复支付请求       |
|              | PAYMENT_0004     | 422        | 支付已超时         |



## 1. 用户模块

### 1.1 用户注册
```
POST /api/users/register
```

**请求参数**:
| 参数名          | 类型   | 必填 | 描述               | 示例              |
| --------------- | ------ | ---- | ------------------ | ----------------- |
| username        | string | 是   | 4-20位字母数字     | "user123"         |
| email           | string | 是   | 有效邮箱格式       | "user@mstest.com" |
| password        | string | 是   | 至少6位            | "password123"     |
| confirmPassword | string | 是   | 必须与password一致 | "password123"     |

**响应示例**:

```json
{
  "userId": 1,
  "username": "user123",
  "email": "user@mstest.com",
  "avatar": "https://mstest.com/default-avatar.jpg",
  "status": "NORMAL",
  "createdAt": "2023-10-15T08:30:00Z"
}
```

### 1.2 用户登录
```
POST /api/users/login
```

**请求参数**:
| 参数名   | 类型   | 必填 | 描述         | 示例                           |
| -------- | ------ | ---- | ------------ | ------------------------------ |
| account  | string | 是   | 用户名或邮箱 | "user123" 或 "user@mstest.com" |
| password | string | 是   | 登录密码     | "password123"                  |

**响应示例**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "userInfo": {
    "userId": 1,
    "username": "user123",
    "email": "user@mstest.com",
    "phone": "13800138000",
    "avatar": "https://mstest.com/avatar.jpg"
  }
}
```

### 1.3 获取用户信息
```
GET /api/users/{userId}
```

**响应示例**:
```json
{
  "userId": 1,
  "username": "user123",
  "nickname": "用户昵称",
  "email": "user@mstest.com",
  "phone": "13800138000",
  "avatar": "https://mstest.com/avatar.jpg",
  "gender": "MALE",
  "status": "NORMAL",
  "createdAt": "2023-10-15T08:30:00Z"
}
```

### 1.4 修改用户信息
```
PUT /api/users/{userId}
```

**请求参数**:
| 参数名   | 类型   | 必填 | 描述                     | 示例                                |
| -------- | ------ | ---- | ------------------------ | ----------------------------------- |
| nickname | string | 否   | ≤20字符                  | "新昵称"                            |
| avatar   | string | 否   | 图片URL                  | "https://mstest.com/new-avatar.jpg" |
| phone    | string | 否   | 手机号                   | 13800138000                         |
| gender   | string | 否   | "MALE"/"FEMALE"/"SECRET" | "MALE"                              |

**响应示例**:

```json
{
  "message": "更新成功"
}
```

### 1.5 收货地址管理

#### 获取地址列表
```
GET /api/users/{userId}/addresses
```

**响应示例**:
```json
[
  {
    "addressId": 1,
    "receiver": "张三",
    "phone": "13800138000",
    "region": "北京市朝阳区",
    "detail": "建国路88号",
    "isDefault": true
  }
]
```

#### 添加地址
```
POST /api/users/{userId}/addresses
```

**请求参数**:
| 参数名    | 类型    | 必填 | 描述         | 示例           |
| --------- | ------- | ---- | ------------ | -------------- |
| receiver  | string  | 是   | 收货人姓名   | "张三"         |
| phone     | string  | 是   | 联系电话     | "13800138000"  |
| region    | string  | 是   | 省市区       | "北京市朝阳区" |
| detail    | string  | 是   | 详细地址     | "建国路88号"   |
| isDefault | boolean | 否   | 是否默认地址 | true           |

**响应示例**:
```json
{
  "addressId": 1
}
```

#### 修改地址
```
PUT /api/users/{userId}/addresses/{addressId}
```

**请求参数**: 同添加地址

**响应示例**:
```json
{
  "message": "更新成功"
}
```

#### 删除地址
```
DELETE /api/users/{userId}/addresses/{addressId}
```

**响应示例**:
```json
{
  "message": "删除成功"
}
```

## 2. 商品模块

### 2.1 首页商品展示
```
GET /api/products/home
```

**响应示例**:
```json
{
  "banners": [
    {
      "imageUrl": "https://mstest.com/banner1.jpg",
      "linkUrl": "/product/1"
    }
  ],
  "categories": [
    {
      "categoryId": 1,
      "name": "电子产品",
      "icon": "https://mstest.com/category-icon.png"
    }
  ],
  "recommendProducts": [
    {
      "productId": 1,
      "name": "智能手机",
      "price": 2999,
      "imageUrl": "https://mstest.com/product1.jpg",
      "sales": 100
    }
  ]
}
```

### 2.2 商品列表
```
GET /api/products
```

**查询参数**:
| 参数名     | 类型   | 必填 | 描述       | 示例        |
| ---------- | ------ | ---- | ---------- | ----------- |
| categoryId | number | 否   | 分类ID     | 1           |
| keyword    | string | 否   | 搜索关键词 | "手机"      |
| minPrice   | number | 否   | 最低价格   | 1000        |
| maxPrice   | number | 否   | 最高价格   | 5000        |
| sort       | string | 否   | 排序方式   | "price_asc" |
| page       | number | 否   | 页码       | 1           |
| pageSize   | number | 否   | 每页数量   | 20          |

**响应示例**:
```json
{
  "total": 50,
  "products": [
    {
      "productId": 1,
      "name": "智能手机",
      "price": 2999,
      "imageUrl": "https://mstest.com/product1.jpg",
      "sales": 100,
      "rating": 4.5,
      "isCollected": true
    }
  ]
}
```

### 2.3 商品详情
```
GET /api/products/{productId}
```

**响应示例**:
```json
{
  "productId": 1,
  "name": "智能手机",
  "price": 2999,
  "stock": 50,
  "images": [
    "https://mstest.com/product1-1.jpg",
    "https://mstest.com/product1-2.jpg"
  ],
  "description": "高性能智能手机...",
  "specifications": [
    {
      "name": "屏幕尺寸",
      "value": "6.5英寸"
    }
  ],
  "isCollected": true,
  "rating": 4.5,
  "reviewCount": 100
}
```

### 2.4 商品收藏

#### 收藏商品
```
POST /api/products/{productId}/collect
```

**响应示例**:
```json
{
  "message": "收藏成功"
}
```

#### 取消收藏
```
DELETE /api/products/{productId}/collect
```

**响应示例**:
```json
{
  "message": "取消收藏成功"
}
```

#### 获取收藏列表
```
GET /api/users/{userId}/collections
```

**响应示例**:
```json
[
  {
    "productId": 1,
    "name": "智能手机",
    "price": 2999,
    "imageUrl": "https://mstest.com/product1.jpg",
    "collectedAt": "2023-10-15T09:00:00Z"
  }
]
```

## 3. 购物车模块

### 3.1 加入购物车
```
POST /api/cart
```

**请求参数**:
| 参数名    | 类型   | 必填 | 描述        | 示例 |
| --------- | ------ | ---- | ----------- | ---- |
| productId | number | 是   | 商品ID      | 1    |
| quantity  | number | 否   | 数量，默认1 | 2    |

**响应示例**:
```json
{
  "cartItemId": 1
}
```

### 3.2 获取购物车列表
```
GET /api/cart
```

**响应示例**:
```json
[
  {
    "cartItemId": 1,
    "productId": 1,
    "name": "智能手机",
    "imageUrl": "https://mstest.com/product1.jpg",
    "price": 2999,
    "quantity": 2,
    "selected": true,
    "stock": 50,
    "status": "NORMAL"
  }
]
```

### 3.3 修改购物车商品
```
PUT /api/cart/{cartItemId}
```

**请求参数**:
| 参数名   | 类型    | 必填 | 描述     | 示例  |
| -------- | ------- | ---- | -------- | ----- |
| quantity | number  | 否   | 新数量   | 3     |
| selected | boolean | 否   | 是否选中 | false |

**响应示例**:
```json
{
  "message": "更新成功"
}
```

### 3.4 删除购物车商品
```
DELETE /api/cart/{cartItemId}
```

**响应示例**:
```json
{
  "message": "删除成功"
}
```

### 3.5 批量删除购物车商品
```
DELETE /api/cart/batch
```

**请求参数**:
| 参数名      | 类型  | 必填 | 描述           | 示例   |
| ----------- | ----- | ---- | -------------- | ------ |
| cartItemIds | array | 是   | 购物车项ID数组 | [1, 2] |

**响应示例**:
```json
{
  "message": "批量删除成功"
}
```

## 4. 订单模块

### 4.1 提交订单
```
POST /api/orders
```

**请求参数**:
| 参数名      | 类型   | 必填 | 描述           | 示例         |
| ----------- | ------ | ---- | -------------- | ------------ |
| cartItemIds | array  | 是   | 购物车项ID数组 | [1, 2]       |
| addressId   | number | 是   | 收货地址ID     | 1            |
| remark      | string | 否   | 订单备注       | "请尽快发货" |

**响应示例**:
```json
{
  "orderId": "202310150001",
  "totalAmount": 5998,
  "paymentAmount": 5998,
  "createdAt": "2023-10-15T10:00:00Z"
}
```

### 4.2 获取订单列表
```
GET /api/orders
```

**查询参数**:
| 参数名   | 类型   | 必填 | 描述     | 示例     |
| -------- | ------ | ---- | -------- | -------- |
| status   | string | 否   | 订单状态 | "UNPAID" |
| page     | number | 否   | 页码     | 1        |
| pageSize | number | 否   | 每页数量 | 10       |

**响应示例**:
```json
{
  "total": 5,
  "orders": [
    {
      "orderId": "202310150001",
      "totalAmount": 5998,
      "status": "UNPAID",
      "createdAt": "2023-10-15T10:00:00Z",
      "itemCount": 2,
      "firstProductImage": "https://mstest.com/product1.jpg"
    }
  ]
}
```

### 4.3 获取订单详情
```
GET /api/orders/{orderId}
```

**响应示例**:
```json
{
  "orderId": "202310150001",
  "status": "UNPAID",
  "totalAmount": 5998,
  "paymentAmount": 5998,
  "createdAt": "2023-10-15T10:00:00Z",
  "paidAt": null,
  "shippedAt": null,
  "completedAt": null,
  "address": {
    "receiver": "张三",
    "phone": "13800138000",
    "fullAddress": "北京市朝阳区建国路88号"
  },
  "items": [
    {
      "productId": 1,
      "name": "智能手机",
      "imageUrl": "https://mstest.com/product1.jpg",
      "price": 2999,
      "quantity": 2
    }
  ],
  "canReview": false
}
```

### 4.4 支付订单
```
POST /api/orders/{orderId}/pay
```

**请求参数**:
| 参数名        | 类型   | 必填 | 描述     | 示例     |
| ------------- | ------ | ---- | -------- | -------- |
| paymentMethod | string | 是   | 支付方式 | "ALIPAY" |

**响应示例**:
```json
{
  "paymentData": {
    "payUrl": "https://alipay.com?order=123456"
  }
}
```

### 4.5 取消订单
```
PUT /api/orders/{orderId}/cancel
```

**响应示例**:

```json
{
  "message": "订单已取消"
}
```

### 4.6 确认收货
```
PUT /api/orders/{orderId}/complete
```

**响应示例**:
```json
{
  "message": "确认收货成功"
}
```

## 5. 评论模块

### 5.1 提交评论
```
POST /api/reviews
```

**请求参数**:
| 参数名    | 类型   | 必填 | 描述             | 示例                               |
| --------- | ------ | ---- | ---------------- | ---------------------------------- |
| orderId   | string | 是   | 订单ID           | "202310150001"                     |
| productId | number | 是   | 商品ID           | 1                                  |
| rating    | number | 是   | 评分1-5          | 5                                  |
| content   | string | 是   | 评论内容10-500字 | "商品质量很好"                     |
| images    | array  | 否   | 图片URL数组      | ["https://mstest.com/review1.jpg"] |

**响应示例**:
```json
{
  "reviewId": 1
}
```

### 5.2 获取商品评论
```
GET /api/products/{productId}/reviews
```

**查询参数**:
| 参数名   | 类型   | 必填 | 描述     | 示例          |
| -------- | ------ | ---- | -------- | ------------- |
| filter   | string | 否   | 筛选条件 | "WITH_IMAGES" |
| page     | number | 否   | 页码     | 1             |
| pageSize | number | 否   | 每页数量 | 10            |

**响应示例**:
```json
{
  "averageRating": 4.5,
  "total": 100,
  "reviews": [
    {
      "reviewId": 1,
      "userId": 1,
      "username": "用户123****",
      "rating": 5,
      "content": "商品质量很好",
      "images": ["https://mstest.com/review1.jpg"],
      "createdAt": "2023-10-15T11:00:00Z"
    }
  ]
}
```



## 6. 后台管理：商品管理

### 1.1 获取商品列表
```
GET /products
```

**查询参数**:
| 参数名     | 类型   | 必填 | 描述                       | 示例      |
| ---------- | ------ | ---- | -------------------------- | --------- |
| keyword    | string | 否   | 商品名称搜索               | "手机"    |
| categoryId | number | 否   | 分类ID筛选                 | 1         |
| status     | string | 否   | 状态筛选(ON_SALE/OFF_SALE) | "ON_SALE" |
| minPrice   | number | 否   | 最低价格                   | 1000      |
| maxPrice   | number | 否   | 最高价格                   | 5000      |
| page       | number | 否   | 页码(默认1)                | 1         |
| pageSize   | number | 否   | 每页数量(默认20)           | 20        |

**响应示例**:

```json
{
  "total": 125,
  "products": [
    {
      "productId": 101,
      "name": "智能手机X",
      "price": 3999.00,
      "costPrice": 2999.00,
      "stock": 150,
      "sales": 320,
      "categoryPath": "电子产品/手机",
      "status": "ON_SALE",
      "createdAt": "2023-09-01T10:00:00Z",
      "updatedAt": "2023-10-05T15:30:00Z"
    }
  ]
}
```

### 1.2 创建商品
```
POST /products
```

**请求参数**:
| 参数名      | 类型   | 必填 | 描述              | 示例                                   |
| ----------- | ------ | ---- | ----------------- | -------------------------------------- |
| name        | string | 是   | 商品名称          | "智能手机X Pro"                        |
| categoryId  | number | 是   | 分类ID            | 101                                    |
| price       | number | 是   | 销售价            | 4999.00                                |
| costPrice   | number | 否   | 成本价            | 3999.00                                |
| stock       | number | 是   | 库存              | 200                                    |
| mainImage   | string | 是   | 主图URL           | "https://cdn.com/p101.jpg"             |
| images      | array  | 否   | 详情图URL数组     | ["https://cdn.com/p101-1.jpg"]         |
| description | string | 是   | 商品描述          | "高端智能手机..."                      |
| specs       | array  | 否   | 规格参数          | [{"name":"颜色","values":["黑","白"]}] |
| status      | string | 否   | 状态(默认ON_SALE) | "ON_SALE"                              |

**响应示例**:
```json
{
  "productId": 102,
  "message": "商品创建成功"
}
```

### 1.3 更新商品信息
```
PUT /products/{productId}
```

**请求参数**: 同创建商品(所有字段可选)

**响应示例**:
```json
{
  "message": "商品信息更新成功"
}
```

### 1.4 商品上下架
```
PATCH /products/{productId}/status
```

**请求参数**:
| 参数名 | 类型   | 必填 | 描述             | 示例       |
| ------ | ------ | ---- | ---------------- | ---------- |
| status | string | 是   | ON_SALE/OFF_SALE | "OFF_SALE" |
| reason | string | 否   | 下架原因         | "库存不足" |

**响应示例**:
```json
{
  "message": "商品已下架"
}
```

### 1.5 删除商品(逻辑删除)
```
DELETE /products/{productId}
```

**响应示例**:
```json
{
  "message": "商品已删除"
}
```

## 7. 后台管理：商品分类管理

### 2.1 获取分类树
```
GET /categories/tree
```

**响应示例**:
```json
[
  {
    "categoryId": 1,
    "name": "电子产品",
    "icon": "https://cdn.com/icon1.png",
    "sort": 10,
    "status": "ENABLED",
    "children": [
      {
        "categoryId": 101,
        "name": "手机",
        "parentId": 1,
        "icon": "https://cdn.com/icon101.png",
        "sort": 5,
        "status": "ENABLED"
      }
    ]
  }
]
```

### 2.2 创建分类
```
POST /categories
```

**请求参数**:
| 参数名   | 类型   | 必填 | 描述              | 示例                          |
| -------- | ------ | ---- | ----------------- | ----------------------------- |
| name     | string | 是   | 分类名称          | "智能家居"                    |
| parentId | number | 否   | 父分类ID(0为一级) | 1                             |
| icon     | string | 否   | 图标URL           | "https://cdn.com/icon201.png" |
| sort     | number | 否   | 排序值            | 15                            |
| status   | string | 否   | 状态(默认ENABLED) | "ENABLED"                     |

**响应示例**:
```json
{
  "categoryId": 201,
  "message": "分类创建成功"
}
```

### 2.3 更新分类
```
PUT /categories/{categoryId}
```

**请求参数**: 同创建分类(所有字段可选)

**响应示例**:
```json
{
  "message": "分类更新成功"
}
```

### 2.4 启用/禁用分类
```
PATCH /categories/{categoryId}/status
```

**请求参数**:
| 参数名 | 类型   | 必填 | 描述             | 示例       |
| ------ | ------ | ---- | ---------------- | ---------- |
| status | string | 是   | ENABLED/DISABLED | "DISABLED" |

**响应示例**:
```json
{
  "message": "分类已禁用"
}
```

## 8. 后台管理：订单管理

### 3.1 订单列表
```
GET /orders
```

**查询参数**:
| 参数名    | 类型   | 必填 | 描述                 | 示例          |
| --------- | ------ | ---- | -------------------- | ------------- |
| orderNo   | string | 否   | 订单号模糊查询       | "20231015"    |
| status    | string | 否   | 订单状态             | "PAID"        |
| userId    | number | 否   | 用户ID               | 1001          |
| phone     | string | 否   | 收货人手机号         | "13800138000" |
| startTime | string | 否   | 开始时间(yyyy-MM-dd) | "2023-10-01"  |
| endTime   | string | 否   | 结束时间(yyyy-MM-dd) | "2023-10-15"  |
| page      | number | 否   | 页码                 | 1             |
| pageSize  | number | 否   | 每页数量             | 20            |

**响应示例**:
```json
{
  "total": 85,
  "orders": [
    {
      "orderId": "20231015123456",
      "userId": 1001,
      "username": "user123",
      "totalAmount": 5998.00,
      "paymentAmount": 5998.00,
      "status": "PAID",
      "paymentMethod": "ALIPAY",
      "createdAt": "2023-10-15T10:30:00Z",
      "shippingInfo": {
        "receiver": "张三",
        "phone": "13800138000",
        "address": "北京市朝阳区..."
      }
    }
  ]
}
```

### 3.2 订单详情
```
GET /orders/{orderId}
```

**响应示例**:
```json
{
  "orderId": "20231015123456",
  "userId": 1001,
  "userInfo": {
    "username": "user123",
    "phone": "13800138001"
  },
  "status": "PAID",
  "paymentInfo": {
    "method": "ALIPAY",
    "amount": 5998.00,
    "transactionId": "ALI123456789",
    "paidAt": "2023-10-15T10:35:00Z"
  },
  "shippingInfo": {
    "receiver": "张三",
    "phone": "13800138000",
    "address": "北京市朝阳区...",
    "company": "顺丰",
    "trackingNo": "SF123456789"
  },
  "items": [
    {
      "productId": 101,
      "name": "智能手机X",
      "image": "https://cdn.com/p101.jpg",
      "price": 2999.00,
      "quantity": 2,
      "total": 5998.00
    }
  ],
  "createdAt": "2023-10-15T10:30:00Z",
  "updatedAt": "2023-10-15T10:35:00Z"
}
```

### 3.3 订单发货
```
POST /orders/{orderId}/ship
```

**请求参数**:
| 参数名          | 类型   | 必填 | 描述     | 示例                   |
| --------------- | ------ | ---- | -------- | ---------------------- |
| shippingCompany | string | 是   | 物流公司 | "顺丰快递"             |
| trackingNumber  | string | 是   | 物流单号 | "SF123456789"          |
| shippingTime    | string | 否   | 发货时间 | "2023-10-15T14:00:00Z" |

**响应示例**:
```json
{
  "message": "发货操作成功",
  "shippingInfo": {
    "company": "顺丰快递",
    "trackingNumber": "SF123456789",
    "shippingTime": "2023-10-15T14:00:00Z"
  }
}
```

### 3.4 订单备注
```
POST /orders/{orderId}/remarks
```

**请求参数**:
| 参数名     | 类型    | 必填 | 描述         | 示例               |
| ---------- | ------- | ---- | ------------ | ------------------ |
| content    | string  | 是   | 备注内容     | "客户要求周末配送" |
| isInternal | boolean | 否   | 是否内部备注 | true               |

**响应示例**:
```json
{
  "message": "备注添加成功"
}
```

## 9. 后台管理：用户管理

### 4.1 用户列表
```
GET /users
```

**查询参数**:
| 参数名    | 类型   | 必填 | 描述              | 示例          |
| --------- | ------ | ---- | ----------------- | ------------- |
| keyword   | string | 否   | 用户名/手机号搜索 | "13800138000" |
| status    | string | 否   | 状态筛选          | "NORMAL"      |
| startTime | string | 否   | 注册开始时间      | "2023-10-01"  |
| endTime   | string | 否   | 注册结束时间      | "2023-10-15"  |
| page      | number | 否   | 页码              | 1             |
| pageSize  | number | 否   | 每页数量          | 20            |

**响应示例**:
```json
{
  "total": 150,
  "users": [
    {
      "userId": 1001,
      "username": "user123",
      "nickname": "测试用户",
      "phone": "138****8000",
      "email": "u***@mstest.com",
      "status": "NORMAL",
      "registerTime": "2023-09-01T08:00:00Z",
      "lastLoginTime": "2023-10-15T09:30:00Z"
    }
  ]
}
```

### 4.2 用户详情
```
GET /users/{userId}
```

**响应示例**:
```json
{
  "userId": 1001,
  "username": "user123",
  "nickname": "测试用户",
  "phone": "13800138000",
  "email": "user@mstest.com",
  "avatar": "https://cdn.com/avatar1001.jpg",
  "status": "NORMAL",
  "registerInfo": {
    "ip": "192.168.1.1",
    "time": "2023-09-01T08:00:00Z",
    "device": "iPhone"
  },
  "statistics": {
    "orderCount": 5,
    "totalSpent": 19995.00,
    "lastOrderTime": "2023-10-10T14:30:00Z"
  }
}
```

### 4.3 封禁/解封用户
```
PATCH /users/{userId}/status
```

**请求参数**:
| 参数名 | 类型   | 必填 | 描述          | 示例           |
| ------ | ------ | ---- | ------------- | -------------- |
| status | string | 是   | NORMAL/BANNED | "BANNED"       |
| reason | string | 否   | 封禁原因      | "多次恶意退货" |

**响应示例**:
```json
{
  "message": "用户已封禁"
}
```

## 10. 后台管理：运营配置

### 5.1 轮播图管理

#### 获取轮播图列表
```
GET /banners
```

**响应示例**:
```json
[
  {
    "bannerId": 1,
    "title": "双十一大促",
    "imageUrl": "https://cdn.com/banner1.jpg",
    "linkUrl": "/promo/1111",
    "sort": 1,
    "status": "ONLINE",
    "startTime": "2023-10-25T00:00:00Z",
    "endTime": "2023-11-12T23:59:59Z"
  }
]
```

#### 创建轮播图
```
POST /banners
```

**请求参数**:
| 参数名    | 类型   | 必填 | 描述     | 示例                          |
| --------- | ------ | ---- | -------- | ----------------------------- |
| title     | string | 是   | 标题     | "双十一大促"                  |
| imageUrl  | string | 是   | 图片URL  | "https://cdn.com/banner2.jpg" |
| linkUrl   | string | 是   | 跳转链接 | "/promo/1111"                 |
| sort      | number | 否   | 排序值   | 2                             |
| status    | string | 否   | 状态     | "ONLINE"                      |
| startTime | string | 否   | 开始时间 | "2023-10-25T00:00:00Z"        |
| endTime   | string | 否   | 结束时间 | "2023-11-12T23:59:59Z"        |

**响应示例**:
```json
{
  "bannerId": 2,
  "message": "轮播图创建成功"
}
```

### 5.2 推荐位管理

#### 获取推荐位配置
```
GET /recommends
```

**查询参数**:
| 参数名   | 类型   | 必填 | 描述       | 示例       |
| -------- | ------ | ---- | ---------- | ---------- |
| position | string | 否   | 推荐位标识 | "HOME_HOT" |

**响应示例**:
```json
{
  "HOME_HOT": {
    "name": "首页热销推荐",
    "maxItems": 10,
    "items": [
      {
        "productId": 101,
        "name": "智能手机X",
        "image": "https://cdn.com/p101.jpg",
        "sort": 1
      }
    ]
  }
}
```

#### 更新推荐位
```
PUT /recommends/{position}
```

**请求参数**:
| 参数名 | 类型  | 必填 | 描述         | 示例                         |
| ------ | ----- | ---- | ------------ | ---------------------------- |
| items  | array | 是   | 推荐商品数组 | [{"productId":101,"sort":1}] |

**响应示例**:
```json
{
  "message": "推荐位更新成功"
}
```

## 11. 后台管理：数据统计

### 6.1 销售概况
```
GET /stats/sales-overview
```

**查询参数**:
| 参数名 | 类型   | 必填 | 描述                     | 示例         |
| ------ | ------ | ---- | ------------------------ | ------------ |
| period | string | 否   | 统计周期(day/week/month) | "week"       |
| date   | string | 否   | 指定日期(yyyy-MM-dd)     | "2023-10-15" |

**响应示例**:
```json
{
  "totalSales": 158976.50,
  "orderCount": 256,
  "userCount": 189,
  "avgOrderAmount": 621.00,
  "trend": [
    {
      "date": "2023-10-09",
      "sales": 12000.00,
      "orders": 25
    }
  ]
}
```

### 6.2 商品销售排行
```
GET /stats/product-ranking
```

**查询参数**:
| 参数名     | 类型   | 必填 | 描述                   | 示例     |
| ---------- | ------ | ---- | ---------------------- | -------- |
| limit      | number | 否   | 返回数量(默认10)       | 5        |
| sortBy     | string | 否   | 排序方式(sales/amount) | "amount" |
| categoryId | number | 否   | 按分类筛选             | 101      |

**响应示例**:

```json
[
  {
    "productId": 101,
    "name": "智能手机X",
    "image": "https://cdn.com/p101.jpg",
    "sales": 156,
    "amount": 467844.00
  }
]
```

1
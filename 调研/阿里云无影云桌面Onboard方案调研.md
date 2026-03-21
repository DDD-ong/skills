# 阿里云无影云桌面用户Onboard方案调研

## 一、概述

本方案针对在新加坡区域（ap-southeast-1）部署阿里云无影云桌面（Elastic Desktop Service, ECD）的用户onboard流程进行调研，实现以下核心能力：
1. 为用户创建独立的云影桌面
2. 配置已准备好的镜像
3. 通过镜像自动安装云桌面内容

---

## 二、新加坡区域支持确认

阿里云无影云桌面**支持新加坡区域**，区域ID为：`ap-southeast-1`

- 新加坡可用区：ap-southeast-1a, ap-southeast-1b, ap-southeast-1c
- 支持便捷账号和AD账号两种办公网络类型

---

## 三、核心API列表及功能说明

### 3.1 办公网络管理

#### 1. CreateSimpleOfficeSite - 创建便捷账号办公网络
**功能**：创建基于便捷账号的办公网络（工作区），是创建云桌面的前提条件

**调用链路**：用户onboard流程的第一步

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID，固定为 `ap-southeast-1` |
| OfficeSiteName | String | 否 | 办公网络名称，2-255个字符 |
| CidrBlock | String | 否 | VPC网段，如 172.16.0.0/12 |
| EnableInternetAccess | Boolean | 否 | 是否开启公网访问 |
| EnableAdminAccess | Boolean | 否 | 是否允许管理员访问 |
| DesktopAccessType | String | 否 | 桌面访问类型：INTERNET/VPC/ANY |
| VSwitchId | String | 否 | 交换机ID |

**响应参数**：
| 参数名 | 类型 | 说明 |
|--------|------|------|
| OfficeSiteId | String | 创建的办公网络ID，后续创建桌面需要用到 |
| RequestId | String | 请求ID |

---

### 3.2 镜像管理

#### 2. DescribeImages - 查询镜像列表
**功能**：查询可用的系统镜像和自定义镜像列表

**调用链路**：在创建云桌面或模板前，查询可用的镜像

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| ImageType | String | 否 | 镜像类型：SYSTEM(系统镜像)/CUSTOM(自定义镜像) |
| ImageId | Array | 否 | 镜像ID列表，用于查询特定镜像 |
| ImageStatus | String | 否 | 镜像状态：Available/Creating/CreateFailed |
| GpuCategory | Boolean | 否 | 是否为GPU类型镜像 |
| ProtocolType | String | 否 | 协议类型：ASP/HDX |
| OsType | String | 否 | 操作系统类型：Windows/Linux |
| MaxResults | Integer | 否 | 最大返回条数，默认50 |
| NextToken | String | 否 | 分页令牌 |

**响应参数**：
| 参数名 | 类型 | 说明 |
|--------|------|------|
| Images | Array | 镜像列表 |
| Images[].ImageId | String | 镜像ID，如 m-4zfb6zj728hhr**** |
| Images[].Name | String | 镜像名称 |
| Images[].ImageType | String | 镜像类型 |
| Images[].OsType | String | 操作系统类型 |
| Images[].Platform | String | 平台：Windows/Ubuntu/CentOS等 |
| Images[].Status | String | 镜像状态 |
| Images[].Size | Integer | 镜像大小(GB) |
| Images[].DataDiskSize | Integer | 数据盘大小(GB) |
| Images[].Description | String | 镜像描述 |
| Images[].GpuCategory | Boolean | 是否GPU镜像 |
| NextToken | String | 下一页令牌 |
| RequestId | String | 请求ID |

---

#### 3. CreateImage - 创建自定义镜像
**功能**：通过已部署好的云电脑创建自定义镜像，用于保存预装软件的桌面环境

**调用链路**：先创建一台基础云桌面并安装所需软件，然后基于此创建自定义镜像

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| DesktopId | String | 是 | 源云电脑ID |
| ImageName | String | 是 | 镜像名称 |
| Description | String | 否 | 镜像描述 |

**响应参数**：
| 参数名 | 类型 | 说明 |
|--------|------|------|
| ImageId | String | 创建的镜像ID |
| RequestId | String | 请求ID |

---

### 3.3 云电脑模板管理

#### 4. DescribeBundles - 查询云电脑模板
**功能**：查询系统模板和自定义模板的详细信息

**调用链路**：创建云桌面前，查询可用的模板配置

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| BundleType | String | 否 | 模板类型：SYSTEM(系统)/CUSTOM(自定义) |
| ImageId | Array | 否 | 镜像ID列表，过滤包含指定镜像的模板 |
| CpuCount | Integer | 否 | CPU核数过滤 |
| MemorySize | Integer | 否 | 内存大小过滤(GB) |

**响应参数**：
| 参数名 | 类型 | 说明 |
|--------|------|------|
| Bundles | Array | 模板列表 |
| Bundles[].BundleId | String | 模板ID |
| Bundles[].BundleName | String | 模板名称 |
| Bundles[].ImageId | String | 关联的镜像ID |
| Bundles[].ImageName | String | 镜像名称 |
| Bundles[].DesktopType | String | 云桌面规格 |
| Bundles[].RootDiskSizeGib | Integer | 系统盘大小(GB) |
| Bundles[].UserDiskSizeGib | Integer | 数据盘大小(GB) |
| Bundles[].CpuCount | Integer | CPU核数 |
| Bundles[].MemorySize | Integer | 内存大小(GB) |
| Bundles[].Platform | String | 平台类型 |

---

#### 5. CreateBundle - 创建自定义模板
**功能**：创建自定义云电脑模板，将镜像与硬件配置绑定

**调用链路**：基于自定义镜像创建模板，便于批量创建相同配置的云桌面

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| ImageId | String | 是 | 镜像ID，如 m-4zfb6zj728hhr**** |
| DesktopType | String | 是 | 云桌面规格，如 ecd.basic.large |
| RootDiskSizeGib | Integer | 是 | 系统盘大小(GB) |
| UserDiskSizeGib | Integer | 是 | 数据盘大小(GB) |
| BundleName | String | 否 | 模板名称 |
| Description | String | 否 | 模板描述 |

**响应参数**：
| 参数名 | 类型 | 说明 |
|--------|------|------|
| BundleId | String | 创建的模板ID |
| RequestId | String | 请求ID |

---

### 3.4 云桌面生命周期管理

#### 6. CreateDesktops - 创建云桌面（核心API）
**功能**：创建一台或多台云电脑，支持模板方式和无模板方式

**调用链路**：用户onboard的核心步骤，创建用户专属云桌面

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| OfficeSiteId | String | 是 | 办公网络ID |
| PolicyGroupId | String | 是 | 策略组ID |
| BundleId | String | 条件 | 云电脑模板ID（使用模板方式时必填） |
| DesktopAttachment | Object | 条件 | 无模板方式入参（与BundleId二选一） |
| DesktopAttachment.ImageId | String | 否 | 镜像ID（无模板方式） |
| DesktopAttachment.SystemDiskCategory | String | 否 | 系统盘类型：cloud_efficiency/cloud_ssd/cloud_essd |
| DesktopAttachment.SystemDiskSize | Integer | 否 | 系统盘大小(GB) |
| DesktopAttachment.DataDiskCategory | String | 否 | 数据盘类型 |
| DesktopAttachment.DataDiskSize | Integer | 否 | 数据盘大小(GB) |
| DesktopAttachment.DesktopType | String | 否 | 云桌面规格 |
| DesktopAttachment.DefaultLanguage | String | 否 | 默认语言：zh-CN/en-US等 |
| Amount | Integer | 否 | 创建数量，1-300，默认1 |
| ChargeType | String | 否 | 计费方式：PostPaid(按量)/PrePaid(包年包月) |
| Period | Integer | 否 | 包年包月时长 |
| PeriodUnit | String | 否 | 时长单位：Month/Year |
| AutoPay | Boolean | 否 | 是否自动支付，默认true |
| DesktopName | String | 否 | 云电脑名称 |
| EndUserId | Array | 否 | 授权用户ID列表 |
| UserAssignMode | String | 否 | 分配模式：ALL/PER_USER |
| SubnetId | String | 否 | 子网ID |
| Tag | Array | 否 | 标签键值对 |

**响应参数**：
| 参数名 | 类型 | 说明 |
|--------|------|------|
| DesktopId | Array | 创建的云电脑ID列表 |
| OrderId | Long | 订单ID（包年包月时返回） |
| RequestId | String | 请求ID |

**重要说明**：
- **模板方式**：传入BundleId，使用预定义的模板配置（包含镜像、磁盘、规格）
- **无模板方式**：传入DesktopAttachment，直接指定ImageId和各配置参数
- 两种方式二选一，不能同时传入

---

#### 7. DescribeDesktops - 查询云桌面详情
**功能**：查询云电脑的详细信息和状态

**调用链路**：创建云桌面后，轮询查询创建状态；日常管理查询

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| DesktopId | Array | 否 | 云电脑ID列表，1-100个 |
| DesktopStatus | String | 否 | 状态过滤：Running/Stopped/Starting/Stopping/Creating/Deleting等 |
| OfficeSiteId | String | 否 | 办公网络ID过滤 |
| UserName | String | 否 | 用户名过滤 |
| PageNumber | Integer | 否 | 页码 |
| PageSize | Integer | 否 | 每页条数 |

**响应参数**：
| 参数名 | 类型 | 说明 |
|--------|------|------|
| TotalCount | Integer | 总条数 |
| Desktops | Array | 云桌面列表 |
| Desktops[].DesktopId | String | 云桌面ID |
| Desktops[].DesktopStatus | String | 状态：Running/Stopped/Creating等 |
| Desktops[].DesktopName | String | 云桌面名称 |
| Desktops[].OfficeSiteId | String | 办公网络ID |
| Desktops[].PolicyGroupId | String | 策略组ID |
| Desktops[].BundleId | String | 模板ID |
| Desktops[].ImageId | String | 镜像ID |
| Desktops[].Cpu | Integer | CPU核数 |
| Desktops[].Memory | Integer | 内存大小(GB) |
| Desktops[].OsType | String | 操作系统类型 |
| Desktops[].CreationTime | String | 创建时间 |
| Desktops[].ChargeType | String | 计费方式 |
| Desktops[].EndUserIds | Array | 授权用户列表 |

---

#### 8. RebuildDesktops - 变更云桌面镜像
**功能**：为一台或多台云电脑变更镜像（重装系统）

**调用链路**：需要更新云桌面软件环境时，使用新镜像重建

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| DesktopId | Array | 是 | 云电脑ID列表 |
| ImageId | String | 否 | 变更后的新镜像ID |
| OperateType | String | 否 | 操作类型 |
| Language | String | 否 | 语言设置 |

**响应参数**：
| 参数名 | 类型 | 说明 |
|--------|------|------|
| RebuildResults | Array | 重建结果列表 |
| RebuildResults[].DesktopId | String | 云桌面ID |
| RebuildResults[].Code | String | 结果码 |
| RebuildResults[].Message | String | 结果信息 |
| RequestId | String | 请求ID |

**重要说明**：
- 变更镜像会清空系统盘数据，请提前备份
- 数据盘数据可以选择保留或清空

---

#### 9. StartDesktops / StopDesktops / RebootDesktops - 云桌面电源管理
**功能**：启动、停止、重启云桌面

**调用链路**：日常运维管理

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| DesktopId | Array | 是 | 云电脑ID列表 |

---

#### 10. DeleteDesktops - 释放云桌面
**功能**：释放一台或多台云电脑资源

**调用链路**：用户离职或资源清理时

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| DesktopId | Array | 是 | 云电脑ID列表 |
| Force | Boolean | 否 | 是否强制删除 |

---

### 3.5 用户授权管理

#### 11. ModifyUserEntitlement - 修改用户授权
**功能**：为用户新增或删除云电脑授权

**调用链路**：创建云桌面后，将桌面授权分配给具体用户

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| DesktopId | String | 是 | 云电脑ID |
| EndUserId | Array | 是 | 用户ID列表 |
| UserAssignMode | String | 是 | 分配模式：ADD(添加)/DELETE(删除) |

---

## 四、用户Onboard流程设计方案

### 方案一：基于模板的创建方式（推荐）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        用户Onboard流程（模板方式）                            │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: 创建办公网络（一次性）
┌────────────────────────────────────────────────────────────┐
│  API: CreateSimpleOfficeSite                                │
│  Input: RegionId=ap-southeast-1, OfficeSiteName, CidrBlock │
│  Output: OfficeSiteId                                       │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
Step 2: 准备自定义镜像（一次性）
┌────────────────────────────────────────────────────────────┐
│  方式A: 基于现有云桌面创建镜像                               │
│  ├─ 创建基础云桌面                                          │
│  ├─ 安装所需软件和配置                                       │
│  └─ API: CreateImage → ImageId                              │
│                                                             │
│  方式B: 使用已有镜像                                         │
│  └─ API: DescribeImages 查询可用镜像                         │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
Step 3: 创建云电脑模板（一次性）
┌────────────────────────────────────────────────────────────┐
│  API: CreateBundle                                          │
│  Input: RegionId, ImageId, DesktopType, DiskSize           │
│  Output: BundleId                                           │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
Step 4: 为用户创建云桌面（每次onboard）
┌────────────────────────────────────────────────────────────┐
│  API: CreateDesktops                                        │
│  Input: RegionId, OfficeSiteId, BundleId,                   │
│         PolicyGroupId, EndUserId, DesktopName              │
│  Output: DesktopId                                          │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
Step 5: 查询创建状态
┌────────────────────────────────────────────────────────────┐
│  API: DescribeDesktops                                      │
│  Input: RegionId, DesktopId                                 │
│  Output: DesktopStatus (Creating → Running)                │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
Step 6: 用户授权（如创建时未指定）
┌────────────────────────────────────────────────────────────┐
│  API: ModifyUserEntitlement                                 │
│  Input: RegionId, DesktopId, EndUserId, UserAssignMode=ADD │
│  Output: 授权成功                                            │
└────────────────────────────────────────────────────────────┘
```

### 方案二：无模板的创建方式

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       用户Onboard流程（无模板方式）                           │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: 创建办公网络（同方案一）
                              │
                              ▼
Step 2: 查询可用镜像
┌────────────────────────────────────────────────────────────┐
│  API: DescribeImages                                        │
│  Input: RegionId=ap-southeast-1, ImageType=CUSTOM          │
│  Output: Images列表 (包含ImageId)                           │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
Step 3: 直接创建云桌面（传入DesktopAttachment）
┌────────────────────────────────────────────────────────────┐
│  API: CreateDesktops                                        │
│  Input:                                                     │
│    - RegionId: ap-southeast-1                              │
│    - OfficeSiteId: 办公网络ID                              │
│    - PolicyGroupId: 策略组ID                               │
│    - DesktopAttachment: {                                  │
│        ImageId: "m-xxxxxxxxx",                             │
│        DesktopType: "ecd.basic.large",                     │
│        SystemDiskCategory: "cloud_essd",                   │
│        SystemDiskSize: 80,                                 │
│        DataDiskCategory: "cloud_essd",                     │
│        DataDiskSize: 100,                                  │
│        DefaultLanguage: "zh-CN"                            │
│      }                                                      │
│    - EndUserId: ["user@example.com"]                       │
│    - DesktopName: "用户专属桌面"                            │
│  Output: DesktopId                                          │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
Step 4-5: 查询状态和用户授权（同方案一）
```

---

## 五、API调用链路详细说明

### 5.1 完整Onboard调用链路

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   用户请求   │───▶│  创建办公网络     │───▶│  查询/准备镜像   │
└─────────────┘    │  (CreateSimple   │    │  (DescribeImages│
                   │   OfficeSite)    │    │   /CreateImage) │
                   └──────────────────┘    └─────────────────┘
                                                     │
                              ┌────────────────────┘
                              ▼
                   ┌──────────────────┐    ┌─────────────────┐
                   │  创建模板(可选)   │───▶│   创建云桌面     │
                   │  (CreateBundle)  │    │  (CreateDesktops)│
                   └──────────────────┘    └─────────────────┘
                                                     │
                              ┌────────────────────┘
                              ▼
                   ┌──────────────────┐    ┌─────────────────┐
                   │  查询创建状态     │───▶│   用户授权       │
                   │ (DescribeDesktops)│   │(ModifyUserEntitle│
                   └──────────────────┘    │    ment)        │
                                            └─────────────────┘
```

### 5.2 关键API输入输出示例

#### CreateSimpleOfficeSite 示例
```json
// Request
{
  "RegionId": "ap-southeast-1",
  "OfficeSiteName": "Singapore-Office",
  "CidrBlock": "172.16.0.0/12",
  "EnableInternetAccess": true,
  "DesktopAccessType": "INTERNET"
}

// Response
{
  "OfficeSiteId": "cn-sg-xxx",
  "RequestId": "1CBAFFAB-B697-4049-A9B1-67E1FC5F****"
}
```

#### CreateBundle 示例
```json
// Request
{
  "RegionId": "ap-southeast-1",
  "BundleName": "Custom-Dev-Template",
  "ImageId": "m-4zfb6zj728hhr****",
  "DesktopType": "ecd.basic.large",
  "RootDiskSizeGib": 80,
  "UserDiskSizeGib": 100,
  "Description": "开发环境模板，预装IDE和工具"
}

// Response
{
  "BundleId": "b-xxx",
  "RequestId": "1CBAFFAB-B697-4049-A9B1-67E1FC5F****"
}
```

#### CreateDesktops（模板方式）示例
```json
// Request
{
  "RegionId": "ap-southeast-1",
  "OfficeSiteId": "cn-sg-xxx",
  "PolicyGroupId": "pg-xxx",
  "BundleId": "b-xxx",
  "DesktopName": "User-Desktop-001",
  "Amount": 1,
  "ChargeType": "PostPaid",
  "EndUserId": ["user@company.com"],
  "UserAssignMode": "PER_USER"
}

// Response
{
  "DesktopId": [["ecd-gx2x1dhsmucyy****"]],
  "RequestId": "1CBAFFAB-B697-4049-A9B1-67E1FC5F****"
}
```

#### CreateDesktops（无模板方式）示例
```json
// Request
{
  "RegionId": "ap-southeast-1",
  "OfficeSiteId": "cn-sg-xxx",
  "PolicyGroupId": "pg-xxx",
  "DesktopAttachment": {
    "ImageId": "m-4zfb6zj728hhr****",
    "DesktopType": "ecd.basic.large",
    "SystemDiskCategory": "cloud_essd",
    "SystemDiskSize": 80,
    "DataDiskCategory": "cloud_essd",
    "DataDiskSize": 100,
    "DefaultLanguage": "zh-CN"
  },
  "DesktopName": "User-Desktop-002",
  "Amount": 1,
  "ChargeType": "PostPaid",
  "EndUserId": ["user2@company.com"]
}

// Response
{
  "DesktopId": [["ecd-xxxxxxxxxxxx****"]],
  "RequestId": "1CBAFFAB-B697-4049-A9B1-67E1FC5F****"
}
```

---

## 六、方案对比与建议

| 对比项 | 方案一：模板方式 | 方案二：无模板方式 |
|--------|-----------------|-------------------|
| **复杂度** | 中等（需先创建模板） | 简单（直接创建） |
| **灵活性** | 低（配置固定） | 高（每次可调整） |
| **维护性** | 高（模板统一管理） | 低（配置分散） |
| **批量创建** | 推荐（模板复用） | 不推荐 |
| **适用场景** | 标准化环境、批量onboard | 个性化环境、临时创建 |

### 推荐方案

**对于用户onboard场景，推荐使用方案一（模板方式）**，原因如下：

1. **标准化**：通过模板确保所有用户获得一致的桌面环境
2. **简化操作**：onboard时只需传入BundleId，无需关心底层配置
3. **易于维护**：镜像更新时只需创建新模板，不影响已有桌面
4. **版本管理**：可以为不同用户群体创建不同模板（开发模板、设计模板等）

---

## 七、注意事项

### 7.1 区域相关
- 新加坡区域ID固定为 `ap-southeast-1`
- 确保所有API调用都使用正确的RegionId
- 镜像、模板、办公网络等资源都是区域级别的，不能跨区使用

### 7.2 依赖关系
- 创建云桌面必须先有 **办公网络(OfficeSite)**
- 创建云桌面必须指定 **策略组(PolicyGroup)**
- 使用模板方式需要先有 **模板(Bundle)**
- 模板必须关联 **镜像(Image)**

### 7.3 异步操作
- CreateDesktops 是异步操作，创建需要一定时间
- 需要通过 DescribeDesktops 轮询查询状态
- 状态从 `Creating` 变为 `Running` 表示创建成功

### 7.4 计费相关
- 支持按量付费(PostPaid)和包年包月(PrePaid)
- 按量付费适合短期使用，包年包月适合长期使用
- 创建时可以通过 DescribePrice API 查询价格

### 7.5 镜像准备
- 建议先创建一台基础云桌面
- 安装所有需要的软件和配置
- 基于此创建自定义镜像
- 这样新用户onboard时桌面已预装好所需内容

---

## 八、API调用权限

调用阿里云无影云桌面API需要以下权限：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecd:CreateSimpleOfficeSite",
        "ecd:DescribeOfficeSites",
        "ecd:CreateBundle",
        "ecd:DescribeBundles",
        "ecd:CreateImage",
        "ecd:DescribeImages",
        "ecd:CreateDesktops",
        "ecd:DescribeDesktops",
        "ecd:RebuildDesktops",
        "ecd:StartDesktops",
        "ecd:StopDesktops",
        "ecd:RebootDesktops",
        "ecd:DeleteDesktops",
        "ecd:ModifyUserEntitlement",
        "ecd:DescribePrice"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 九、费用说明

### 9.1 计费组成

无影云桌面企业版的费用由以下几部分组成：

```
┌─────────────────────────────────────────────────────────────────┐
│                      无影云桌面费用组成                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   计算资源    │  │   存储资源    │  │      增值服务        │  │
│  │  (vCPU/内存) │  │(系统盘/数据盘)│  │ (带宽/云盘/应用等)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### 1. 计算资源费用
| 规格类型 | 配置示例 | 适用场景 |
|----------|----------|----------|
| 基础型 | 2核4G | 轻办公、文档处理 |
| 标准型 | 4核8G | 日常办公、开发 |
| 性能型 | 8核16G | 设计、视频剪辑 |
| GPU型 | 含GPU | 3D渲染、AI训练 |

#### 2. 存储资源费用
| 存储类型 | 计费项 | 参考价格 |
|----------|--------|----------|
| 系统盘 | 容量(GiB) | 约0.25元/GiB/月 |
| 数据盘 | 容量(GiB) | 约0.25元/GiB/月 |
| 性能级别 | PL0/PL1/PL2/PL3 | 不同级别价格不同 |

#### 3. 网络与增值服务
| 服务 | 计费方式 | 说明 |
|------|----------|------|
| 公网带宽 | 按带宽计费 | 可选，根据实际需求 |
| 无影云盘 | 按容量计费 | 可选，云端存储空间 |
| 应用中心 | 按应用计费 | 可选，预装商业软件 |

---

### 9.2 计费方式对比

| 计费方式 | 说明 | 适用场景 | 付费模式 |
|----------|------|----------|----------|
| **包年包月-不限时** | 购买时长内不限使用时长 | 长期固定使用 | 预付费 |
| **包年包月-限时长** | 每月固定可用时长(120/250/360小时) | 有规律的使用需求 | 预付费 |
| **按量付费** | 按实际使用小时数计费 | 临时、弹性需求 | 后付费 |

#### 计费公式

**包年包月（不限时）**：
```
费用 = 套餐价格 × 购买时长
```

**包年包月（限时长）**：
```
费用 = 套餐价格 × 购买时长
超出套餐时长部分 = 超出小时数 × 小时单价
```

**按量付费**：
```
费用 = 小时单价 × 实际运行小时数
```

---

### 9.3 参考价格（企业版）

> **注意**：以下价格为参考价格，实际价格以阿里云官网和DescribePrice API查询结果为准。新加坡区域价格可能与国内略有差异。

#### 4核8G配置（标准办公型）
| 计费方式 | 规格 | 参考价格 |
|----------|------|----------|
| 包年包月-不限时 | 4核8G + 80G系统盘 + 50G数据盘 | 约199元/月 |
| 包年包月-120小时/月 | 4核8G + 80G系统盘 + 50G数据盘 | 约59元/月 |
| 按量付费 | 4核8G | 约0.727元/小时 |

#### 其他配置参考
| 配置 | 包月不限时参考价 | 包月120小时参考价 |
|------|------------------|-------------------|
| 2核4G | 约150元/月 | 约45元/月 |
| 4核8G | 约199元/月 | 约59元/月 |
| 8核16G | 约350元/月 | 约138元/月 |
| 8核32G | 约500元/月 | 约200元/月 |

#### 存储费用参考
| 存储类型 | 价格 |
|----------|------|
| 系统盘 | 0.25元/GiB/月 |
| 数据盘 | 0.25元/GiB/月 |

---

### 9.4 价格查询API

#### DescribePrice - 查询新购价格

**功能**：在创建云桌前查询具体配置的价格

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| RegionId | String | 是 | 地域ID：`ap-southeast-1` |
| ResourceType | String | 是 | 资源类型：Desktop |
| InstanceType | String | 是 | 实例规格：如 ecd.basic.large |
| RootDiskSizeGib | Integer | 否 | 系统盘大小(GiB) |
| UserDiskSizeGib | Integer | 否 | 数据盘大小(GiB) |
| RootDiskCategory | String | 否 | 系统盘类型：cloud_efficiency/cloud_ssd/cloud_essd |
| UserDiskCategory | String | 否 | 数据盘类型 |
| RootDiskPerformanceLevel | String | 否 | 系统盘性能级别：PL0/PL1/PL2/PL3 |
| UserDiskPerformanceLevel | String | 否 | 数据盘性能级别 |
| Period | Integer | 否 | 购买时长 |
| PeriodUnit | String | 否 | 时长单位：Month/Year |
| Amount | Integer | 否 | 购买数量 |
| ChargeType | String | 否 | 计费类型：PrePaid/PostPaid |
| InternetChargeType | String | 否 | 网络计费类型 |
| Bandwidth | Integer | 否 | 带宽(Mbps) |

**响应参数**：
| 参数名 | 类型 | 说明 |
|--------|------|------|
| PriceInfo | Object | 价格信息 |
| PriceInfo.OriginalPrice | Float | 原价 |
| PriceInfo.DiscountPrice | Float | 折扣金额 |
| PriceInfo.TradePrice | Float | 实际交易价格 |
| PriceInfo.Currency | String | 货币单位：CNY |
| PriceInfo.Promotions | Array | 优惠活动信息 |
| PriceInfo.Rules | Array | 价格规则 |
| FreeCdsQuota | Integer | 免费云盘配额 |
| FreeCdsSize | Integer | 免费云盘大小 |
| RequestId | String | 请求ID |

**调用示例**：
```json
// Request
{
  "RegionId": "ap-southeast-1",
  "ResourceType": "Desktop",
  "InstanceType": "ecd.basic.large",
  "RootDiskSizeGib": 80,
  "UserDiskSizeGib": 100,
  "RootDiskCategory": "cloud_essd",
  "Period": 1,
  "PeriodUnit": "Month",
  "Amount": 1,
  "ChargeType": "PrePaid"
}

// Response
{
  "PriceInfo": {
    "OriginalPrice": 199.0,
    "DiscountPrice": 0.0,
    "TradePrice": 199.0,
    "Currency": "CNY",
    "Promotions": [],
    "Rules": []
  },
  "RequestId": "1CBAFFAB-B697-4049-A9B1-67E1FC5F****"
}
```

---

### 9.5 费用优化建议

#### 1. 选择合适的计费方式
| 使用场景 | 推荐计费方式 | 预估节省 |
|----------|-------------|----------|
| 每天8小时、5天/周办公 | 包月120小时 | 节省约40% |
| 7×24小时运行 | 包月不限时 | 节省约60% |
| 临时使用、不定时 | 按量付费 | 按需付费 |

#### 2. 存储优化
- 根据实际需求选择系统盘大小，避免过度配置
- 数据盘可按需扩容，初始配置不宜过大
- 选择合适的磁盘性能级别，非高性能场景选择PL0/PL1

#### 3. 网络优化
- 内网访问场景可不配置公网带宽
- 需要公网访问时，按实际带宽需求配置

#### 4. 批量购买优惠
- 批量创建云桌面时，关注阿里云的促销活动
- 长期使用的桌面建议选择包年，通常比包月更优惠

---

### 9.6 新加坡区域费用说明

#### 区域价格差异
- 不同地域的云电脑规格与价格**可能有所不同**
- 海外区域（包括新加坡）的价格通常与国内略有差异
- 建议通过 **DescribePrice API** 实时查询新加坡区域的准确价格

#### 汇率与结算
- 新加坡区域的费用通常以 **美元(USD)** 或 **人民币(CNY)** 结算
- 具体以阿里云官网显示为准

#### 费用预估示例（新加坡区域）

假设为一个10人团队创建标准办公环境：

```
配置：4核8G + 80G系统盘 + 50G数据盘
计费方式：包月不限时
数量：10台
时长：1个月

计算资源费用：199元/台/月 × 10台 = 1,990元/月
存储费用：
  - 系统盘：80G × 0.25元/G/月 × 10台 = 200元/月
  - 数据盘：50G × 0.25元/G/月 × 10台 = 125元/月

预估月费用总计：约 2,315元/月
预估年费用总计：约 27,780元/年
```

> 实际费用请以DescribePrice API查询结果为准，以上仅为参考估算。

---

## 十、总结

本方案提供了完整的阿里云无影云桌面用户onboard流程设计，核心API包括：

| 功能 | 核心API |
|------|---------|
| 创建办公网络 | CreateSimpleOfficeSite |
| 管理镜像 | DescribeImages / CreateImage |
| 创建模板 | CreateBundle / DescribeBundles |
| 创建云桌面 | CreateDesktops |
| 查询状态 | DescribeDesktops |
| 变更镜像 | RebuildDesktops |
| 用户授权 | ModifyUserEntitlement |
| 查询价格 | DescribePrice |

**推荐实施路径**：
1. 在新加坡区域创建办公网络（一次性）
2. 准备自定义镜像，预装所需软件（一次性）
3. 基于镜像创建模板（一次性）
4. 使用 **DescribePrice API** 查询价格，确认预算
5. 使用模板批量为用户创建云桌面（每次onboard）
6. 轮询查询创建状态，完成后通知用户
7. 定期使用 **DescribeDesktops** 监控桌面使用情况，优化成本

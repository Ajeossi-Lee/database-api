# Database API

技术栈为 FastAPI、SQLAlchemy 2.0（异步）、Alembic 和 PostgreSQL。

## 准备

需要 Python 3.12+。在仓库根目录安装依赖：

```powershell
uv sync
```

## 启动与切换环境

启动前设置 `APP_ENV`，程序会加载对应的环境文件。不设置时使用 `dev`。

| APP_ENV | 环境文件 |
| --- | --- |
| `dev` | `envs/.env.dev` |
| `test` | `envs/.env.test` |
| `staging` | `envs/.env.staging` |
| `prod` | `envs/.env.prod` |

没有对应文件时，复制 `envs/.env.example` 再填写数据库地址和密钥。示例文件不含真实密钥，可以提交；四个环境文件仍被忽略。

本地开发：

```powershell
$env:APP_ENV="dev"
uv run uvicorn app.main:app --reload
```

切换到其他环境时，只改 `APP_ENV`，例如 `$env:APP_ENV="prod"`。修改后需要重新启动进程。


运行测试时会自动使用 `test` 环境：

```powershell
uv run pytest
```

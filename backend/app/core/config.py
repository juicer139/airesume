"""全局配置模块。

使用 pydantic-settings 管理配置，好处有三：
1. 自动从环境变量和 .env 文件读取配置，代码里不出现任何明文密钥
2. 类型自动校验（MYSQL_PORT 写成 "abc" 会直接报错，而不是运行到一半才炸）
3. get_settings() 用 lru_cache 缓存，整个进程只读一次 .env，性能好

其他模块统一这样使用：
    from app.core.config import get_settings
    settings = get_settings()
"""
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """所有可配置项集中在这里。

    以后新模块需要配置时，往这里加字段即可，.env.example 同步补一份说明。
    字段名 = 环境变量名（大小写不敏感），有默认值意味着不配置也能启动。
    """

    model_config = SettingsConfigDict(
        env_file=".env",          # 配置文件位置（相对于启动命令所在目录）
        env_file_encoding="utf-8",
        extra="ignore",           # .env 里多写的变量不报错
    )

    # ---------- 应用基础 ----------
    APP_NAME: str = "AI Resume Analyzer"
    DEBUG: bool = True

    # ---------- MySQL（阶段 2 接入）----------
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "airesume"

    # ---------- JWT 认证（阶段 2 接入）----------
    # 生产环境务必换成随机长字符串：
    #   python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = "dev-only-insecure-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # token 有效期 24 小时

    # ---------- AI 服务（阶段 5 接入）----------
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.deepseek.com/v1"
    AI_MODEL: str = "deepseek-chat"

    # ---------- Redis / Celery（阶段 6 接入）----------
    REDIS_URL: str = "redis://localhost:6379/0"

    @property
    def DATABASE_URL(self) -> str:
        """SQLAlchemy 连接串。

        mysql+pymysql 指定驱动；charset=utf8mb4 支持中文和 emoji，
        简历里出现 emoji 名字是很常见的，不要用默认 utf8。
        quote_plus 对密码做 URL 编码：密码里含 @ : / 等特殊字符也不会把连接串弄坏。
        """
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{quote_plus(self.MYSQL_PASSWORD)}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            f"?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    """单例入口，全项目唯一获取配置的方式。"""
    return Settings()

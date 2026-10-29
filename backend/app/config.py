from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_prefix="BUILDMART_", extra="ignore")

    demo_password: str | None = None
    # Secure by default; only disable explicitly for local plain-HTTP development.
    secure_cookies: bool = True
    # Comma-separated IPs of reverse proxies whose X-Forwarded-For header is trusted.
    trusted_proxies: str = ""

    @property
    def trusted_proxy_set(self) -> set[str]:
        return {p.strip() for p in self.trusted_proxies.split(",") if p.strip()}


settings = Settings()

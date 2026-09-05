from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str

    # 업로드 이미지는 로컬 디스크에 저장한다 (실서비스 전환 시 S3 등으로 교체 지점).
    FILE_STORAGE_DIR: str = "uploads"
    FILE_BASE_URL: str = "http://localhost:8000/uploads"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024

    # 정산방 공유 링크 (`POST /rooms` 응답의 shareUrl)가 가리키는 프론트엔드 도메인.
    FRONTEND_BASE_URL: str = "https://example.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()

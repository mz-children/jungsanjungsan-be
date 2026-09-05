from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """API는 camelCase, 코드/DB는 snake_case. 요청은 camelCase와 snake_case 둘 다 받아주고
    (`populate_by_name`), 응답은 camelCase로 나간다."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

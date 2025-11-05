

from idp.framework.exception.metadata import ErrorCode


class MapperExceptionCode:
    MAPPER_CONFIG_INVALID = ErrorCode(
        code="430001",
        message="Mapper configuration is invalid",
        http_status=400,
    )
    MAPPER_TYPE_MISMATCH = ErrorCode(
        code="430002",
        message="Mapper type mismatch",
        http_status=400,
    )
    MAPPER_CONVERSION_ERROR = ErrorCode(
        code="430003",
        message="Mapper conversion error",
        http_status=400,
    )
    MAPPER_CYCLIC_DEPENDENCY = ErrorCode(
        code="430004",
        message="Mapper cyclic dependency",
        http_status=400,
    )
    MAPPER_REVERSE_CONFIG_INVALID = ErrorCode(
        code="430005",
        message="Mapper reverse configuration is invalid",
        http_status=400,
    )
    MAPPER_NESTED_CONFIG_INVALID = ErrorCode(
        code="430006",
        message="Mapper nested configuration is invalid",
        http_status=400,
    )
    MAPPER_COLLECTION_CONFIG_INVALID = ErrorCode(
        code="430007",
        message="Mapper collection configuration is invalid",
        http_status=400,
    )
    MAPPER_BATCH_PROCESSING_FAILED = ErrorCode(
        code="430008",
        message="Mapper batch processing failed",
        http_status=400,
    )
    MAPPER_TYPE_MISMATCH = ErrorCode(
        code="430009",
        message="Mapper type mismatch",
        http_status=400,
    )
    MAPPER_CONFIG_MISSING = ErrorCode(
        code="430010",
        message="Mapper configuration is missing",
        http_status=400,
    )
    MAPPER_SOURCE_NOT_FOUND = ErrorCode(
        code="430011",
        message="Mapper source not found",
        http_status=400,
    )
    MAPPER_TARGET_NOT_FOUND = ErrorCode(
        code="430012",
        message="Mapper target not found",
        http_status=400,
    )
    MAPPER_TYPE_MISMATCH = ErrorCode(
        code="430013",
        message="Mapper type mismatch",
        http_status=400,
    )
    MAPPER_CONFIG_MISSING = ErrorCode(
        code="430014",
        message="Mapper configuration is missing",
        http_status=400,
    )
    MAPPER_TYPE_CONVERSION_FAILED = ErrorCode(
        code="430015",
        message="Mapper type conversion failed",
        http_status=400,
    )

    MAPPER_CUSTOM_CONFIG_INVALID = ErrorCode(
        code="430016",
        message="Mapper custom configuration is invalid",
        http_status=400,
    )

    MAPPER_NOT_FOUND = ErrorCode(
        code="430017",
        message="Mapper not found",
        http_status=404,
    )

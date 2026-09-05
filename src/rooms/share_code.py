from nanoid import generate

# _COMMON.md: 12자 nanoid, 약 71비트 엔트로피. nanoid 기본 알파벳이
# room_share_code_fmt 제약(`^[A-Za-z0-9_-]{8,32}$`)과 그대로 맞아떨어진다.
SHARE_CODE_SIZE = 12


def generate_share_code() -> str:
    return generate(size=SHARE_CODE_SIZE)

from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[1] / '.env'


def update_env_values(values: dict[str, str | None]) -> None:
    existing: dict[str, str] = {}
    order: list[str] = []
    if ENV_PATH.exists():
        for raw_line in ENV_PATH.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            if key not in existing:
                order.append(key)
            existing[key] = value.strip()

    for key, value in values.items():
        if value is None:
            continue
        if key not in existing:
            order.append(key)
        existing[key] = value

    content = '\n'.join(f'{key}={existing.get(key, "")}' for key in order) + '\n'
    ENV_PATH.write_text(content, encoding='utf-8')
    ENV_PATH.chmod(0o600)

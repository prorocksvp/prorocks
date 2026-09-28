```python
#!/usr/bin/env python3
"""
Собирает профили маршрутизации из общего шаблона:

HAPP/
  ROUTING.JSON
  ROUTING.DEEPLINK
  ROUTING.ONADD.DEEPLINK

INCY/
  ROUTING.JSON
  ROUTING.ONADD.DEEPLINK

Источник:
  config/routing-template.json

Использование:
  python3 scripts/build_routing.py \
      --repo prorocksvp/prorocks \
      --tag 202609281200
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path


def encode_config(cfg: dict) -> str:
    """JSON -> Base64 для deeplink."""

    data = json.dumps(
        cfg,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")

    return base64.b64encode(data).decode("ascii")


def write_json(path: Path, cfg: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            cfg,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )


def main() -> int:
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--template",
        default="config/routing-template.json"
    )

    ap.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="USER/REPO на GitHub"
    )

    ap.add_argument(
        "--tag",
        required=True,
        help="тег сборки"
    )

    ap.add_argument(
        "--last-updated",
        default=str(int(time.time()))
    )

    args = ap.parse_args()

    # ---------------------------------------------------------
    # Проверяем repo
    # ---------------------------------------------------------

    if not args.repo or "/" not in args.repo:
        print(
            "Ошибка: укажите --repo USER/REPO "
            "(или запускайте через GitHub Actions)",
            file=sys.stderr
        )
        return 1

    # ---------------------------------------------------------
    # Читаем общий шаблон
    # ---------------------------------------------------------

    template = Path(args.template)

    if not template.exists():
        print(
            f"Ошибка: файл не найден: {template}",
            file=sys.stderr
        )
        return 1

    try:
        cfg = json.loads(
            template.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as e:
        print(
            f"Ошибка JSON в {template}: {e}",
            file=sys.stderr
        )
        return 1

    # ---------------------------------------------------------
    # Общие параметры
    # ---------------------------------------------------------

    # Стабильная ссылка.
    #
    # main/release/geosite.dat
    # main/release/geoip.dat
    #
    # При обновлении файлов ссылка не меняется.

    base = (
        f"https://cdn.jsdelivr.net/gh/"
        f"{args.repo}@main/release"
    )

    cfg["Geositeurl"] = f"{base}/geosite.dat"
    cfg["Geoipurl"] = f"{base}/geoip.dat"

    # Обновляем timestamp при каждой сборке.
    cfg["LastUpdated"] = args.last_updated

    # ---------------------------------------------------------
    # HAPP
    # ---------------------------------------------------------

    happ_dir = Path("HAPP")
    happ_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    write_json(
        happ_dir / "ROUTING.JSON",
        cfg
    )

    # Base64
    happ_b64 = encode_config(cfg)

    # Ручное добавление
    (happ_dir / "ROUTING.DEEPLINK").write_text(
        f"happ://routing/add/{happ_b64}\n",
        encoding="utf-8"
    )

    # Автоматическое добавление/обновление
    (happ_dir / "ROUTING.ONADD.DEEPLINK").write_text(
        f"happ://routing/onadd/{happ_b64}\n",
        encoding="utf-8"
    )

    # ---------------------------------------------------------
    # INCY
    # ---------------------------------------------------------

    incy_dir = Path("INCY")
    incy_dir.mkdir(parents=True, exist_ok=True)

    # Тот же JSON, что и для Happ.
    #
    # Все DirectSites / ProxySites / BlockSites
    # и остальные параметры берутся из одного шаблона.
    write_json(
        incy_dir / "ROUTING.JSON",
        cfg
    )

    # INCY использует:
    #
    # incy://routing/onadd/{base64}
    #
    incy_b64 = encode_config(cfg)

    (incy_dir / "ROUTING.ONADD.DEEPLINK").write_text(
        f"incy://routing/onadd/{incy_b64}\n",
        encoding="utf-8"
    )

    # ---------------------------------------------------------
    # Вывод
    # ---------------------------------------------------------

    print()
    print("========================================")
    print(" Routing profiles successfully generated")
    print("========================================")
    print()

    print(f"Profile: {cfg.get('Name')}")
    print(f"Tag: {args.tag}")
    print(f"LastUpdated: {args.last_updated}")
    print()

    print("HAPP:")
    print("  HAPP/ROUTING.JSON")
    print("  HAPP/ROUTING.DEEPLINK")
    print("  HAPP/ROUTING.ONADD.DEEPLINK")
    print()

    print("INCY:")
    print("  INCY/ROUTING.JSON")
    print("  INCY/ROUTING.ONADD.DEEPLINK")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

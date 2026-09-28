#!/usr/bin/env python3
"""
Собирает итоговые профили маршрутизации из общего шаблона:

  HAPP/ROUTING.JSON
  HAPP/ROUTING.DEEPLINK
  HAPP/ROUTING.ONADD.DEEPLINK

  INCY/ROUTING.JSON
  INCY/ROUTING.ONADD.DEEPLINK

Источник:
  config/routing-template.json

Все правила маршрутизации берутся из одного шаблона.
Поэтому добавление домена в routing-template.json
автоматически попадает и в Happ, и в INCY.

Использование:

  python3 scripts/build_routing.py \
      --repo prorocksvp/prorocks \
      --tag 202609280818

В GitHub Actions --repo берётся из GITHUB_REPOSITORY.
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path


def encode_config(cfg: dict) -> str:
    """
    Кодирует JSON-конфигурацию в Base64
    для deeplink.
    """

    data = json.dumps(
        cfg,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")

    return base64.b64encode(data).decode("ascii")


def write_json(path: Path, cfg: dict) -> None:
    """
    Записывает JSON с красивым форматированием.
    """

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
    parser = argparse.ArgumentParser(
        description="Build Happ and INCY routing profiles"
    )

    parser.add_argument(
        "--template",
        default="config/routing-template.json",
        help="Путь к общему шаблону маршрутизации"
    )

    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="GitHub repository в формате USER/REPO"
    )

    parser.add_argument(
        "--tag",
        required=True,
        help="Тег текущей сборки"
    )

    parser.add_argument(
        "--last-updated",
        default=str(int(time.time())),
        help="Значение LastUpdated"
    )

    parser.add_argument(
        "--happ-outdir",
        default="HAPP",
        help="Каталог результата Happ"
    )

    parser.add_argument(
        "--incy-outdir",
        default="INCY",
        help="Каталог результата INCY"
    )

    args = parser.parse_args()

    # ---------------------------------------------------------
    # Проверка репозитория
    # ---------------------------------------------------------

    if not args.repo or "/" not in args.repo:
        print(
            "Ошибка: укажите --repo USER/REPO "
            "(или запускайте скрипт в GitHub Actions)",
            file=sys.stderr
        )
        return 1

    # ---------------------------------------------------------
    # Читаем шаблон
    # ---------------------------------------------------------

    template_path = Path(args.template)

    if not template_path.exists():
        print(
            f"Ошибка: шаблон не найден: {template_path}",
            file=sys.stderr
        )
        return 1

    try:
        cfg = json.loads(
            template_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        print(
            f"Ошибка JSON в {template_path}: {error}",
            file=sys.stderr
        )
        return 1

    if not isinstance(cfg, dict):
        print(
            "Ошибка: корень routing-template.json должен быть JSON-объектом",
            file=sys.stderr
        )
        return 1

    # ---------------------------------------------------------
    # Формируем ссылки на geosite.dat / geoip.dat
    # ---------------------------------------------------------

    # Используем main, поэтому URL остаётся постоянным.
    #
    # После новой сборки содержимое:
    #
    #   release/geosite.dat
    #   release/geoip.dat
    #
    # меняется, но URL остаётся тем же.

    base = (
        f"https://cdn.jsdelivr.net/gh/"
        f"{args.repo}@main/release"
    )

    cfg["Geositeurl"] = f"{base}/geosite.dat"
    cfg["Geoipurl"] = f"{base}/geoip.dat"

    # Меняем время обновления при каждой сборке.
    cfg["LastUpdated"] = str(args.last_updated)

    # ---------------------------------------------------------
    # Создаём отдельные копии конфигурации
    # ---------------------------------------------------------

    # Сейчас формат routing-template.json совместим
    # одновременно с Happ и INCY.
    #
    # Используем отдельные dict, чтобы в дальнейшем
    # форматы можно было изменять независимо.

    happ_cfg = dict(cfg)
    incy_cfg = dict(cfg)

    # ---------------------------------------------------------
    # HAPP
    # ---------------------------------------------------------

    happ_dir = Path(args.happ_outdir)
    happ_dir.mkdir(parents=True, exist_ok=True)

    # Итоговый JSON
    write_json(
        happ_dir / "ROUTING.JSON",
        happ_cfg
    )

    # Base64 для deeplink
    happ_b64 = encode_config(happ_cfg)

    # Ручное добавление
    (happ_dir / "ROUTING.DEEPLINK").write_text(
        f"happ://routing/add/{happ_b64}\n",
        encoding="utf-8"
    )

    # Автоматическое добавление
    (happ_dir / "ROUTING.ONADD.DEEPLINK").write_text(
        f"happ://routing/onadd/{happ_b64}\n",
        encoding="utf-8"
    )

    # ---------------------------------------------------------
    # INCY
    # ---------------------------------------------------------

    incy_dir = Path(args.incy_outdir)
    incy_dir.mkdir(parents=True, exist_ok=True)

    # Итоговый JSON
    write_json(
        incy_dir / "ROUTING.JSON",
        incy_cfg
    )

    # Base64 для INCY
    incy_b64 = encode_config(incy_cfg)

    # INCY использует именно:
    #
    # incy://routing/onadd/{base64}
    #
    (incy_dir / "ROUTING.ONADD.DEEPLINK").write_text(
        f"incy://routing/onadd/{incy_b64}\n",
        encoding="utf-8"
    )

    # ---------------------------------------------------------
    # Проверяем, что основные массивы существуют
    # ---------------------------------------------------------

    routing_fields = (
        "DirectSites",
        "DirectIp",
        "ProxySites",
        "ProxyIp",
        "BlockSites",
        "BlockIp",
    )

    for field in routing_fields:
        if field not in cfg:
            print(
                f"Предупреждение: поле {field} отсутствует "
                f"в {template_path}",
                file=sys.stderr
            )

    # ---------------------------------------------------------
    # Информация о сборке
    # ---------------------------------------------------------

    print()
    print("========================================")
    print("Routing profiles successfully generated")
    print("========================================")
    print()

    print(f"Profile:     {cfg.get('Name', 'Unknown')}")
    print(f"Repository:  {args.repo}")
    print(f"Tag:         {args.tag}")
    print(f"LastUpdated: {args.last_updated}")
    print()

    print("HAPP:")
    print(f"  {happ_dir / 'ROUTING.JSON'}")
    print(f"  {happ_dir / 'ROUTING.DEEPLINK'}")
    print(f"  {happ_dir / 'ROUTING.ONADD.DEEPLINK'}")
    print()

    print("INCY:")
    print(f"  {incy_dir / 'ROUTING.JSON'}")
    print(f"  {incy_dir / 'ROUTING.ONADD.DEEPLINK'}")
    print()

    # Показываем количество правил
    print("Routing rules:")

    for field in routing_fields:
        value = cfg.get(field, [])

        if isinstance(value, list):
            print(f"  {field}: {len(value)}")

    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

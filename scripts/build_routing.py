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

Перед сборкой синхронизирует локальную ветку main
с origin/main, чтобы избежать ошибки:

  ! [rejected] HEAD -> main (fetch first)

Использование:

  python3 scripts/build_routing.py 
      --repo prorocksvp/prorocks 
      --tag 202609280822
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def run_git(*args: str) -> None:
    """Выполнить git-команду и остановиться при ошибке."""

    print(f"+ git {' '.join(args)}")

    result = subprocess.run(
        ["git", *args],
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Git command failed: git {' '.join(args)}"
        )


def encode_config(cfg: dict) -> str:
    """JSON -> Base64 для deeplink."""

    data = json.dumps(
        cfg,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")

    return base64.b64encode(data).decode("ascii")


def write_json(path: Path, cfg: dict) -> None:
    """Записывает JSON с форматированием."""

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            cfg,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )


def sync_main_branch() -> None:
    """
    Синхронизирует текущую ветку с origin/main.

    Это выполняется ДО генерации файлов.
    Поэтому build commit создаётся поверх
    самого свежего состояния удалённого main.
    """

    # Получаем актуальное состояние origin/main.
    run_git("fetch", "origin", "main")

    # Проверяем текущую ветку.
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True
    )

    current_branch = result.stdout.strip()

    # В GitHub Actions ожидаем main.
    if current_branch != "main":
        print(
            f"Предупреждение: текущая ветка '{current_branch}', "
            f"ожидалась 'main'."
        )
        return

    # Если origin/main ушёл вперёд,
    # переносим локальные изменения поверх него.
    run_git("rebase", "origin/main")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Happ and INCY routing profiles"
    )

    parser.add_argument(
        "--template",
        default="config/routing-template.json",
        help="Путь к общему шаблону"
    )

    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="GitHub repository USER/REPO"
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
        help="Каталог Happ"
    )

    parser.add_argument(
        "--incy-outdir",
        default="INCY",
        help="Каталог INCY"
    )

    args = parser.parse_args()

    # ---------------------------------------------------------
    # Проверка repository
    # ---------------------------------------------------------

    if not args.repo or "/" not in args.repo:
        print(
            "Ошибка: укажите --repo USER/REPO "
            "(или запускайте через GitHub Actions)",
            file=sys.stderr
        )
        return 1

    # ---------------------------------------------------------
    # Синхронизация с origin/main
    # ---------------------------------------------------------

    try:
        sync_main_branch()
    except RuntimeError as error:
        print(
            f"Ошибка синхронизации Git: {error}",
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
            "Ошибка: routing-template.json должен "
            "содержать JSON-объект",
            file=sys.stderr
        )
        return 1

    # ---------------------------------------------------------
    # Общие URL geosite / geoip
    # ---------------------------------------------------------

    base = (
        f"https://cdn.jsdelivr.net/gh/"
        f"{args.repo}@main/release"
    )

    cfg["Geositeurl"] = f"{base}/geosite.dat"
    cfg["Geoipurl"] = f"{base}/geoip.dat"

    # Timestamp заставляет приложения учитывать
    # изменение конфигурации.
    cfg["LastUpdated"] = str(args.last_updated)

    # Отдельные копии для двух клиентов.
    happ_cfg = dict(cfg)
    incy_cfg = dict(cfg)

    # ---------------------------------------------------------
    # HAPP
    # ---------------------------------------------------------

    happ_dir = Path(args.happ_outdir)
    happ_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        happ_dir / "ROUTING.JSON",
        happ_cfg
    )

    happ_b64 = encode_config(happ_cfg)

    (happ_dir / "ROUTING.DEEPLINK").write_text(
        f"happ://routing/add/{happ_b64}\n",
        encoding="utf-8"
    )

    (happ_dir / "ROUTING.ONADD.DEEPLINK").write_text(
        f"happ://routing/onadd/{happ_b64}\n",
        encoding="utf-8"
    )

    # ---------------------------------------------------------
    # INCY
    # ---------------------------------------------------------

    incy_dir = Path(args.incy_outdir)
    incy_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        incy_dir / "ROUTING.JSON",
        incy_cfg
    )

    incy_b64 = encode_config(incy_cfg)

    (incy_dir / "ROUTING.ONADD.DEEPLINK").write_text(
        f"incy://routing/onadd/{incy_b64}\n",
        encoding="utf-8"
    )

    # ---------------------------------------------------------
    # Проверка полей маршрутизации
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
    # Информация
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

    print("Routing rules:")

    for field in routing_fields:
        value = cfg.get(field, [])

        if isinstance(value, list):
            print(f"  {field}: {len(value)}")

    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

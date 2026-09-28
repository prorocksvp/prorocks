#!/usr/bin/env python3
"""
Build HAPP and INCY routing configs from one shared template.

Source:
    config/routing-template.json

Generated:
    HAPP/ROUTING.JSON
    HAPP/ROUTING.DEEPLINK
    HAPP/ROUTING.ONADD.DEEPLINK

    INCY/ROUTING.JSON
    INCY/ROUTING.ONADD.DEEPLINK

The routing rules are NOT duplicated.
Both clients receive exactly the same routing configuration.
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path


def encode_config(cfg: dict) -> str:
    """Encode routing config as Base64."""
    raw = json.dumps(
        cfg,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    return base64.b64encode(raw).decode("ascii")


def write_json(path: Path, cfg: dict) -> None:
    """Write formatted JSON."""
    path.write_text(
        json.dumps(
            cfg,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, content: str) -> None:
    """Write text file."""
    path.write_text(
        content.rstrip() + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build HAPP and INCY routing configs from one template."
    )

    parser.add_argument(
        "--template",
        default="config/routing-template.json",
    )

    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="GitHub repository, e.g. prorocksvp/prorocks",
    )

    parser.add_argument(
        "--tag",
        required=True,
        help="Release/build tag",
    )

    parser.add_argument(
        "--last-updated",
        default=str(int(time.time())),
        help="LastUpdated value",
    )

    parser.add_argument(
        "--happ-outdir",
        default="HAPP",
    )

    parser.add_argument(
        "--incy-outdir",
        default="INCY",
    )

    args = parser.parse_args()

    # ---------------------------------------------------------
    # Validate repository
    # ---------------------------------------------------------

    if not args.repo or "/" not in args.repo:
        print(
            "ERROR: --repo must be USER/REPO "
            "or GITHUB_REPOSITORY must be available.",
            file=sys.stderr,
        )
        return 1

    # ---------------------------------------------------------
    # Read template
    # ---------------------------------------------------------

    template_path = Path(args.template)

    if not template_path.exists():
        print(
            f"ERROR: template not found: {template_path}",
            file=sys.stderr,
        )
        return 1

    try:
        cfg = json.loads(
            template_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: invalid JSON in {template_path}: {exc}",
            file=sys.stderr,
        )
        return 1

    if not isinstance(cfg, dict):
        print(
            "ERROR: routing template must contain a JSON object.",
            file=sys.stderr,
        )
        return 1

    # ---------------------------------------------------------
    # Stable GeoSite / GeoIP URLs
    # ---------------------------------------------------------

    base_url = (
        f"https://cdn.jsdelivr.net/gh/"
        f"{args.repo}@main/release"
    )

    cfg["Geositeurl"] = f"{base_url}/geosite.dat"
    cfg["Geoipurl"] = f"{base_url}/geoip.dat"

    # This changes on every build and allows clients to detect
    # that the configuration has been updated.
    cfg["LastUpdated"] = args.last_updated

    # ---------------------------------------------------------
    # Output directories
    # ---------------------------------------------------------

    happ_dir = Path(args.happ_outdir)
    incy_dir = Path(args.incy_outdir)

    happ_dir.mkdir(parents=True, exist_ok=True)
    incy_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # Create ONE Base64 payload from ONE config
    # ---------------------------------------------------------

    b64 = encode_config(cfg)

    # =========================================================
    # HAPP
    # =========================================================

    write_json(
        happ_dir / "ROUTING.JSON",
        cfg,
    )

    write_text(
        happ_dir / "ROUTING.DEEPLINK",
        f"happ://routing/add/{b64}",
    )

    write_text(
        happ_dir / "ROUTING.ONADD.DEEPLINK",
        f"happ://routing/onadd/{b64}",
    )

    # =========================================================
    # INCY
    # =========================================================

    write_json(
        incy_dir / "ROUTING.JSON",
        cfg,
    )

    write_text(
        incy_dir / "ROUTING.ONADD.DEEPLINK",
        f"incy://routing/onadd/{b64}",
    )

    # ---------------------------------------------------------
    # Output information
    # ---------------------------------------------------------

    print()
    print("==========================================")
    print(" Routing build completed successfully")
    print("==========================================")
    print()
    print(f"Profile:      {cfg.get('Name', 'unknown')}")
    print(f"Repository:   {args.repo}")
    print(f"Build tag:    {args.tag}")
    print(f"LastUpdated:  {args.last_updated}")
    print()

    print("Routing rules:")
    print(f"  DirectSites: {len(cfg.get('DirectSites', []))}")
    print(f"  ProxySites:  {len(cfg.get('ProxySites', []))}")
    print(f"  BlockSites:  {len(cfg.get('BlockSites', []))}")
    print(f"  DirectIp:    {len(cfg.get('DirectIp', []))}")
    print(f"  ProxyIp:     {len(cfg.get('ProxyIp', []))}")
    print(f"  BlockIp:     {len(cfg.get('BlockIp', []))}")
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

    print("Geo files:")
    print(f"  {cfg['Geositeurl']}")
    print(f"  {cfg['Geoipurl']}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

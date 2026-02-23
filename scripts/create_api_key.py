"""
Rastera Engine — API Key Provisioning Script

Usage:
    python scripts/create_api_key.py --tenant-slug <slug> [--name <label>]

Run inside the container:
    docker compose exec api python scripts/create_api_key.py --tenant-slug demo-coffee

The raw key is printed once to stdout.  It is never stored — only the
SHA-256 hex digest is persisted in tenant_api_keys.
"""
import argparse
import asyncio
import hashlib
import secrets
import sys

from sqlalchemy import select

# Make sure the app package is importable when run from the repo root.
sys.path.insert(0, ".")

from app.db import AsyncSessionLocal
from app.models import Tenant, TenantApiKey


def _generate_key() -> str:
    """Return a new raw API key:  rk_  +  32 random bytes as URL-safe base64."""
    raw = secrets.token_urlsafe(32)
    return f"rk_{raw}"


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def create_key(tenant_slug: str, name: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            print(f"ERROR: Tenant {tenant_slug!r} not found.", file=sys.stderr)
            sys.exit(1)

        raw_key = _generate_key()
        key_hash = _hash_key(raw_key)

        record = TenantApiKey(
            tenant_id=tenant.id,
            name=name,
            key_hash=key_hash,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

    print(f"\nAPI key created for tenant '{tenant_slug}' (name: {name})")
    print("RAW KEY (save this — it will not be shown again):\n")
    print(f"  {raw_key}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new API key for a tenant.")
    parser.add_argument("--tenant-slug", required=True, help="Tenant slug (e.g. demo-coffee)")
    parser.add_argument("--name", default="default", help="Label for this key (e.g. production)")
    args = parser.parse_args()
    asyncio.run(create_key(args.tenant_slug, args.name))


if __name__ == "__main__":
    main()

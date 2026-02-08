#!/usr/bin/env python3
"""CLI management commands for OmniHub.
Sprint 6: Export utility for pilot data backup.

Usage:
    python manage.py export --tenant grand-hotel
    python manage.py export --tenant grand-hotel --type reservations
"""
import asyncio
import argparse
import csv
import io
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')


async def get_db():
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'test_database')]
    return db, client


async def resolve_tenant(db, slug):
    tenant = await db.tenants.find_one({"slug": slug}, {"_id": 0})
    if not tenant:
        print(f"ERROR: Tenant '{slug}' not found.")
        sys.exit(1)
    return tenant


async def export_contacts(db, tenant_id, output_dir):
    contacts = await db.contacts.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(10000)
    path = os.path.join(output_dir, "contacts.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Name", "Phone", "Email", "Tags", "Created At"])
        for c in contacts:
            writer.writerow([
                c.get("id", ""), c.get("name", ""), c.get("phone", ""),
                c.get("email", ""), ",".join(c.get("tags", [])), c.get("created_at", "")
            ])
    print(f"  Exported {len(contacts)} contacts -> {path}")


async def export_reservations(db, tenant_id, output_dir):
    items = await db.reservations.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(10000)
    path = os.path.join(output_dir, "reservations.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Confirmation Code", "Guest Name", "Room Type",
                         "Check-in", "Check-out", "Guests", "Total", "Currency", "Status", "Created At"])
        for r in items:
            writer.writerow([
                r.get("id", ""), r.get("confirmation_code", ""), r.get("guest_name", ""),
                r.get("room_type", ""), r.get("check_in", ""), r.get("check_out", ""),
                r.get("guests_count", ""), r.get("price_total", ""), r.get("currency", ""),
                r.get("status", ""), r.get("created_at", "")
            ])
    print(f"  Exported {len(items)} reservations -> {path}")


async def export_offers(db, tenant_id, output_dir):
    items = await db.offers.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(10000)
    path = os.path.join(output_dir, "offers.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Guest Name", "Room Type", "Check-in", "Check-out",
                         "Price", "Currency", "Status", "Source", "Created At"])
        for o in items:
            writer.writerow([
                o.get("id", ""), o.get("guest_name", ""), o.get("room_type", ""),
                o.get("check_in", ""), o.get("check_out", ""),
                o.get("price_total", o.get("price", "")), o.get("currency", ""),
                o.get("status", ""), o.get("source", ""), o.get("created_at", "")
            ])
    print(f"  Exported {len(items)} offers -> {path}")


async def export_loyalty_members(db, tenant_id, output_dir):
    items = await db.loyalty_accounts.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(10000)
    path = os.path.join(output_dir, "loyalty_members.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Contact ID", "Points", "Tier", "Enrolled At"])
        for m in items:
            writer.writerow([
                m.get("id", ""), m.get("contact_id", ""),
                m.get("points_balance", m.get("points", 0)),
                m.get("tier_name", m.get("tier", "")),
                m.get("enrolled_at", m.get("created_at", ""))
            ])
    print(f"  Exported {len(items)} loyalty members -> {path}")


async def run_export(tenant_slug, export_type):
    db, client = await get_db()
    tenant = await resolve_tenant(db, tenant_slug)
    tenant_id = tenant["id"]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = f"/tmp/omnihub_export_{tenant_slug}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Exporting data for tenant: {tenant['name']} ({tenant_slug})")
    print(f"Output directory: {output_dir}")

    exporters = {
        "contacts": export_contacts,
        "reservations": export_reservations,
        "offers": export_offers,
        "loyalty_members": export_loyalty_members,
    }

    if export_type and export_type in exporters:
        await exporters[export_type](db, tenant_id, output_dir)
    else:
        for name, fn in exporters.items():
            await fn(db, tenant_id, output_dir)

    print(f"\nExport complete: {output_dir}")
    client.close()


def main():
    parser = argparse.ArgumentParser(description="OmniHub Management CLI")
    sub = parser.add_subparsers(dest="command")

    export_parser = sub.add_parser("export", help="Export tenant data to CSV")
    export_parser.add_argument("--tenant", required=True, help="Tenant slug")
    export_parser.add_argument("--type", choices=["contacts", "reservations", "offers", "loyalty_members"],
                               help="Specific export type (default: all)")

    args = parser.parse_args()

    if args.command == "export":
        asyncio.run(run_export(args.tenant, args.type))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

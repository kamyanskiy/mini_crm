"""CLI application for CRM admin tasks."""

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import AsyncSessionLocal
from core.security import hash_password
from models.organization import Organization
from models.organization_member import MemberRole, OrganizationMember
from models.user import User

app = typer.Typer(
    name="crm-admin",
    help="CRM Administration CLI",
    add_completion=False,
)

console = Console()


@app.command("create-admin")
def create_admin(
    email: str = typer.Option(..., "--email", "-e", help="Admin email address"),
    password: str = typer.Option(..., "--password", "-p", help="Admin password (min 8 chars)"),
    name: str = typer.Option(..., "--name", "-n", help="Admin full name"),
    org_name: str = typer.Option("Admin Organization", "--org", "-o", help="Organization name"),
) -> None:
    """Create an admin user with OWNER role in a new organization."""
    if len(password) < 8:
        console.print("[red]❌ Password must be at least 8 characters![/red]")
        raise typer.Exit(1)

    async def _create() -> None:
        async with AsyncSessionLocal() as db:
            try:
                # Check if user exists
                result = await db.execute(select(User).where(User.email == email))
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    console.print(f"[red]❌ User '{email}' already exists![/red]")
                    raise typer.Exit(1)

                # Create user
                hashed_password = hash_password(password)
                user = User(
                    email=email,
                    hashed_password=hashed_password,
                    name=name,
                    is_active=True,
                )
                db.add(user)
                await db.flush()

                # Create organization
                organization = Organization(name=org_name)
                db.add(organization)
                await db.flush()

                # Add user as OWNER
                member = OrganizationMember(
                    organization_id=organization.id,
                    user_id=user.id,
                    role=MemberRole.OWNER,
                )
                db.add(member)

                await db.commit()

                # Display success
                table = Table(title="✅ Admin User Created", show_header=True)
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("User ID", str(user.id))
                table.add_row("Email", user.email)
                table.add_row("Name", user.name)
                table.add_row("Organization", organization.name)
                table.add_row("Role", MemberRole.OWNER.value.upper())

                console.print(table)

            except Exception as e:
                await db.rollback()
                console.print(f"[red]❌ Error: {e}[/red]")
                raise typer.Exit(1)

    asyncio.run(_create())


@app.command("list-users")
def list_users() -> None:
    """List all users in the system."""

    async def _list() -> None:
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(select(User))
                users = result.scalars().all()

                if not users:
                    console.print("[yellow]No users found[/yellow]")
                    return

                table = Table(title="Users", show_header=True)
                table.add_column("ID", style="cyan")
                table.add_column("Email", style="green")
                table.add_column("Name", style="white")
                table.add_column("Active", style="yellow")

                for user in users:
                    table.add_row(
                        str(user.id),
                        user.email,
                        user.name,
                        "✅" if user.is_active else "❌",
                    )

                console.print(table)

            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")
                raise typer.Exit(1)

    asyncio.run(_list())


@app.command("list-orgs")
def list_organizations() -> None:
    """List all organizations in the system."""

    async def _list() -> None:
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(select(Organization))
                orgs = result.scalars().all()

                if not orgs:
                    console.print("[yellow]No organizations found[/yellow]")
                    return

                table = Table(title="Organizations", show_header=True)
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Created At", style="white")

                for org in orgs:
                    table.add_row(
                        str(org.id),
                        org.name,
                        org.created_at.strftime("%Y-%m-%d %H:%M"),
                    )

                console.print(table)

            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")
                raise typer.Exit(1)

    asyncio.run(_list())


@app.command("init")
def init_admin_from_env() -> None:
    """Initialize admin user from environment variables (for entrypoint)."""

    async def _init() -> None:
        from core.init_admin import init_admin_user

        async with AsyncSessionLocal() as session:
            await init_admin_user(session)

    asyncio.run(_init())


if __name__ == "__main__":
    app()

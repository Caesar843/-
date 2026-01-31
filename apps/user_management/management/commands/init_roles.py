from django.core.management.base import BaseCommand

from apps.user_management.models import Role


class Command(BaseCommand):
    help = "Initialize default roles for the system"

    def handle(self, *args, **kwargs):
        default_roles = [
            {
                "role_type": "ADMIN",
                "name": "Admin",
                "description": "System administrator with full access.",
            },
            {
                "role_type": "MANAGEMENT",
                "name": "Management",
                "description": "Management role with reporting access.",
            },
            {
                "role_type": "OPERATION",
                "name": "Operation",
                "description": "Operation role for daily management.",
            },
            {
                "role_type": "FINANCE",
                "name": "Finance",
                "description": "Finance role for billing and finance records.",
            },
            {
                "role_type": "SHOP",
                "name": "Shop",
                "description": "Shop user with access to own shop data.",
            },
        ]

        created_count = 0
        existing_count = 0

        for role_config in default_roles:
            role, created = Role.objects.get_or_create(
                role_type=role_config["role_type"],
                defaults={
                    "name": role_config["name"],
                    "description": role_config["description"],
                },
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created role: {role.name}"))
            else:
                existing_count += 1
                self.stdout.write(self.style.NOTICE(f"Role already exists: {role.name}"))

        self.stdout.write(self.style.SUCCESS("\nInitialization complete!"))
        self.stdout.write(self.style.SUCCESS(f"Created: {created_count} roles"))
        self.stdout.write(self.style.SUCCESS(f"Existing: {existing_count} roles"))

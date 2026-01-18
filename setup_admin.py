from django.contrib.auth.models import User
from apps.user_management.models import UserProfile, Role

# Create super admin role if not exists
super_admin_role, created = Role.objects.get_or_create(
    role_type='SUPER_ADMIN',
    defaults={
        'name': '超级管理员',
        'description': '拥有系统最高权限，可配置系统规则，管理所有数据和用户'
    }
)

# Get or create admin user
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@example.com',
        'first_name': 'Admin',
        'last_name': 'User'
    }
)

# Set password if user was just created
if created:
    admin_user.set_password('admin123')
    admin_user.save()

# Create user profile if not exists
profile, created = UserProfile.objects.get_or_create(
    user=admin_user,
    defaults={
        'role': super_admin_role
    }
)

print(f"Admin user: {admin_user.username}")
print(f"Role: {profile.role.name} ({profile.role.role_type})")
print("Setup completed successfully!")
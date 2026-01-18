from django.contrib.auth.models import User
from apps.user_management.models import UserProfile, Role

# Check if roles exist
print("Checking roles...")
roles = Role.objects.all()
print(f"Found {roles.count()} roles:")
for role in roles:
    print(f"- {role.name} ({role.role_type})")

# Check admin user
print("\nChecking admin user...")
try:
    admin_user = User.objects.get(username='admin')
    print(f"Found admin user: {admin_user.username}")
    
    # Check if user has profile
    try:
        profile = admin_user.profile
        print(f"Admin user has profile: {profile}")
        print(f"Role: {profile.role.name} ({profile.role.role_type})")
    except UserProfile.DoesNotExist:
        print("Admin user does NOT have a profile!")
        # Create profile for admin user
        print("Creating profile for admin user...")
        super_admin_role = Role.objects.get(role_type='SUPER_ADMIN')
        profile = UserProfile.objects.create(
            user=admin_user,
            role=super_admin_role
        )
        print(f"Created profile for admin user with role: {super_admin_role.name}")
        
except User.DoesNotExist:
    print("Admin user does not exist!")
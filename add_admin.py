from app import app, db
from models import User
import datetime

def add_admin_user():
    with app.app_context():
        # First check if the user exists
        user = User.query.filter_by(email='vishalsnw007@gmail.com').first()
        
        if user:
            # If user exists, make them admin
            user.is_admin = True
            db.session.commit()
            print(f"User vishalsnw007@gmail.com has been granted admin privileges.")
        else:
            # Create a new admin user if they don't exist
            # Generate a unique mobile identifier for the user
            mobile = f"admin_{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"[:15]
            
            new_user = User(
                email='vishalsnw007@gmail.com',
                mobile=mobile,
                is_admin=True,
                is_premium=True,
                registration_date=datetime.datetime.utcnow(),
                trial_end_date=datetime.datetime.utcnow() + datetime.timedelta(days=365),  # 1 year trial
                premium_end_date=datetime.datetime.utcnow() + datetime.timedelta(days=365)  # 1 year premium
            )
            
            # Set the PIN to 1234
            new_user.set_pin('1234')
            
            # Generate a random referral code
            import random
            import string
            referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            new_user.referral_code = referral_code
            
            db.session.add(new_user)
            db.session.commit()
            print(f"Created new admin user vishalsnw007@gmail.com with PIN 1234")

if __name__ == "__main__":
    add_admin_user()
"""
User Service - Business Logic Layer
Handles user-related business operations
"""

from models.user import User
from models.attempt import Attempt

class UserService:
    def __init__(self):
        self.user_model = User()
        self.attempt_model = Attempt()
    
    def register_user(self, name, email, password):
        """Register a new user with business logic validation"""
        # Business logic validation
        if not name or len(name.strip()) < 2:
            return {'success': False, 'message': 'Name must be at least 2 characters long'}
        
        if not email or '@' not in email:
            return {'success': False, 'message': 'Please provide a valid email address'}
        
        if not password or len(password) < 6:
            return {'success': False, 'message': 'Password must be at least 6 characters long'}
        
        # Create user
        user_id = self.user_model.create_user(name, email, password)
        
        if user_id:
            return {'success': True, 'message': 'Registration successful! Please login.'}
        else:
            return {'success': False, 'message': 'Email already exists'}
    
    def login_user(self, email, password):
        """Authenticate user login with business logic"""
        if not email or not password:
            return {'success': False, 'message': 'Please provide both email and password'}
        
        user = self.user_model.authenticate_user(email, password)
        
        if user:
            return {
                'success': True, 
                'message': 'Login successful!',
                'user': user
            }
        else:
            return {'success': False, 'message': 'Invalid email or password'}
    
    def get_user_dashboard_data(self, user_id):
        """Get comprehensive dashboard data for user"""
        # Get basic user info
        user = self.user_model.get_user_by_id(user_id)
        if not user:
            return None
        
        # Get user statistics
        stats = self.attempt_model.get_user_stats(user_id)
        
        # Get weak topics
        weak_topics = self.attempt_model.get_weak_topics(user_id)
        
        # Calculate additional metrics
        total_study_time = stats['total_attempted'] * 5  # 5 minutes per question
        score_out_of_10 = round((stats['accuracy'] / 100) * 10, 1)
        
        return {
            'user': user,
            'stats': stats,
            'weak_topics': weak_topics,
            'total_study_time': total_study_time,
            'score_out_of_10': score_out_of_10
        }

"""
Authentication Manager
Handles login, session validation, and password management.
Maintains security constraints and audit trails.
"""

from datetime import datetime, timedelta
try:
    from .db_init import hash_password, verify_password
except ImportError:
    from db_init import hash_password, verify_password


class AuthenticationManager:
    """Manages authentication and session handling."""
    
    def __init__(self, db_manager, core_db_name='system_core', session_timeout_minutes=30):
        self.db_manager = db_manager
        self.core_db = core_db_name
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.active_sessions = {}  # {session_token: {member_id, login_time, ...}}
        self.max_login_attempts = 5

    def _next_audit_id(self):
        try:
            audit_table, _ = self.db_manager.get_table(self.core_db, 'audit_log')
            records = audit_table.get_all()
            if not records:
                return 1
            max_id = 0
            for _, data in records:
                value = data.get('audit_id', 0)
                if isinstance(value, int):
                    max_id = max(max_id, value)
            return max_id + 1
        except Exception:
            return 1
    
    def login(self, username, password):
        """
        Log in a member and create a session token.
        
        Args:
            username: Member username
            password: Member password
        
        Returns:
            dict: {'success': bool, 'session_token': str, 'member_id': int, 'message': str}
        """
        try:
            # Find member
            members_table, _ = self.db_manager.get_table(self.core_db, 'members')
            all_members = members_table.get_all()
            
            member = None
            for _, member_data in all_members:
                if member_data['username'] == username:
                    member = member_data
                    break
            
            if not member:
                return {'success': False, 'session_token': None, 'message': 'Username does not exist'}
            
            if member['status'] != 'active':
                return {'success': False, 'session_token': None, 
                       'message': f'Account is {member["status"]}'}
            
            # Get credential record
            credentials_table, _ = self.db_manager.get_table(self.core_db, 'credentials')
            all_credentials = credentials_table.get_all()
            
            credential = None
            credential_id = None
            for cred_id, cred_data in all_credentials:
                if cred_data['member_id'] == member['member_id']:
                    credential = cred_data
                    credential_id = cred_id
                    break
            
            if not credential:
                return {'success': False, 'session_token': None, 'message': 'Credential error'}
            
            # Check account lockout
            if credential['locked']:
                return {'success': False, 'session_token': None, 'message': 'Account is locked'}
            
            # Verify password
            if not verify_password(password, credential['password_hash'], credential['salt']):
                # Increment failed attempts
                credential['login_attempts'] += 1
                if credential['login_attempts'] >= self.max_login_attempts:
                    credential['locked'] = 1
                    credentials_table.update(credential_id, credential)
                    return {'success': False, 'session_token': None, 
                           'message': 'Too many failed attempts. Account locked.'}
                
                credentials_table.update(credential_id, credential)
                return {'success': False, 'session_token': None, 'message': 'Password does not match'}
            
            # Successful login
            import secrets
            session_token = secrets.token_hex(32)
            
            # Update credential record
            credential['login_attempts'] = 0
            credential['last_login'] = datetime.now().isoformat()
            credentials_table.update(credential_id, credential)
            
            # Create session
            self.active_sessions[session_token] = {
                'member_id': member['member_id'],
                'username': member['username'],
                'login_time': datetime.now(),
                'last_activity': datetime.now()
            }
            
            # Log audit
            self._log_auth_audit('login_success', member['member_id'], username)
            
            return {
                'success': True,
                'session_token': session_token,
                'member_id': member['member_id'],
                'message': f'Welcome, {member["full_name"]}!'
            }
        
        except Exception as e:
            return {'success': False, 'session_token': None, 'message': f'Login error: {str(e)}'}
    
    def validate_session(self, session_token):
        """
        Validate if a session token is active and not expired.
        
        Returns:
            dict: {'valid': bool, 'member_id': int/None, 'message': str}
        """
        if session_token not in self.active_sessions:
            return {'valid': False, 'member_id': None, 'message': 'Invalid session token'}
        
        session = self.active_sessions[session_token]
        login_time = session['login_time']
        
        if datetime.now() - login_time > self.session_timeout:
            del self.active_sessions[session_token]
            return {'valid': False, 'member_id': None, 'message': 'Session expired'}
        
        # Update activity time
        session['last_activity'] = datetime.now()
        
        return {'valid': True, 'member_id': session['member_id'], 'message': 'Session valid'}
    
    def logout(self, session_token):
        """
        Log out a member and invalidate session token.
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        if session_token in self.active_sessions:
            session = self.active_sessions[session_token]
            member_id = session['member_id']
            del self.active_sessions[session_token]
            
            self._log_auth_audit('logout', member_id, session['username'])
            
            return {'success': True, 'message': 'Logged out successfully'}
        
        return {'success': False, 'message': 'Invalid session token'}
    
    def change_password(self, member_id, old_password, new_password):
        """
        Change password for a member.
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            # Get member and credential
            members_table, _ = self.db_manager.get_table(self.core_db, 'members')
            credentials_table, _ = self.db_manager.get_table(self.core_db, 'credentials')
            
            member = members_table.get(member_id)
            if not member:
                return {'success': False, 'message': 'Member not found'}
            
            all_credentials = credentials_table.get_all()
            credential = None
            credential_id = None
            for cred_id, cred_data in all_credentials:
                if cred_data['member_id'] == member_id:
                    credential = cred_data
                    credential_id = cred_id
                    break
            
            if not credential:
                return {'success': False, 'message': 'Credential record not found'}
            
            # Verify old password
            if not verify_password(old_password, credential['password_hash'], credential['salt']):
                return {'success': False, 'message': 'Current password is incorrect'}
            
            # Set new password
            new_hash, new_salt = hash_password(new_password)
            credential['password_hash'] = new_hash
            credential['salt'] = new_salt
            credential['updated_at'] = datetime.now().isoformat()
            
            credentials_table.update(credential_id, credential)
            
            self._log_auth_audit('password_changed', member_id, member['username'])
            
            return {'success': True, 'message': 'Password changed successfully'}
        
        except Exception as e:
            return {'success': False, 'message': f'Password change failed: {str(e)}'}
    
    def unlock_account(self, member_id):
        """
        Unlock a locked account (admin function).
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            credentials_table, _ = self.db_manager.get_table(self.core_db, 'credentials')
            members_table, _ = self.db_manager.get_table(self.core_db, 'members')
            
            member = members_table.get(member_id)
            if not member:
                return {'success': False, 'message': 'Member not found'}
            
            all_credentials = credentials_table.get_all()
            for cred_id, cred_data in all_credentials:
                if cred_data['member_id'] == member_id:
                    cred_data['locked'] = 0
                    cred_data['login_attempts'] = 0
                    credentials_table.update(cred_id, cred_data)
                    
                    self._log_auth_audit('account_unlocked', member_id, member['username'])
                    
                    return {'success': True, 'message': f'Account {member["username"]} unlocked'}
            
            return {'success': False, 'message': 'Credential record not found'}
        
        except Exception as e:
            return {'success': False, 'message': f'Unlock failed: {str(e)}'}
    
    def get_active_sessions(self):
        """Get all active sessions (for admin monitoring)."""
        sessions = []
        for token, session_data in self.active_sessions.items():
            login_duration = datetime.now() - session_data['login_time']
            sessions.append({
                'member_id': session_data['member_id'],
                'username': session_data['username'],
                'login_time': session_data['login_time'].isoformat(),
                'session_duration_seconds': login_duration.total_seconds()
            })
        return sessions
    
    def _log_auth_audit(self, action, member_id, username):
        """Log authentication-related audit entries."""
        try:
            audit_table, _ = self.db_manager.get_table(self.core_db, 'audit_log')
            audit_record = {
                'audit_id': self._next_audit_id(),
                'action_type': action,
                'table_name': 'authentication',
                'record_id': member_id,
                'member_id': member_id,
                'change_details': f'{action} for user {username}',
                'timestamp': datetime.now().isoformat()
            }
            audit_table.insert(audit_record)
        except:
            pass  # Silently fail to not block auth

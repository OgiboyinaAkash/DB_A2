"""
Member Management System
Handles member creation, deletion, updates with strict data integrity.
Ensures consistent state across members, credentials, and group mappings.
"""

from datetime import datetime
try:
    from .db_init import hash_password, verify_password
except ImportError:
    from db_init import hash_password, verify_password


class MemberManager:
    """Manages member lifecycle with data integrity constraints."""
    
    def __init__(self, db_manager, core_db_name='system_core'):
        """
        Initialize member manager.
        
        Args:
            db_manager: DatabaseManager instance
            core_db_name: Name of core system database
        """
        self.db_manager = db_manager
        self.core_db = core_db_name
        self.audit_log = []

    def _next_table_id(self, table_name, id_field):
        try:
            table, _ = self.db_manager.get_table(self.core_db, table_name)
            records = table.get_all()
            if not records:
                return 1
            max_id = 0
            for _, data in records:
                value = data.get(id_field, 0)
                if isinstance(value, int):
                    max_id = max(max_id, value)
            return max_id + 1
        except Exception:
            return 1
    
    def create_member(self, username, email, full_name, department, password):
        """
        Create a new member with atomic transaction semantics.
        
        Ensures:
        - No duplicate usernames or emails
        - Credentials are created simultaneously
        - Audit log entry is recorded
        
        Returns:
            dict: {'success': bool, 'member_id': int, 'message': str}
        """
        timestamp = datetime.now().isoformat()
        
        # Validate input
        if not username or not email or not full_name or not password:
            return {'success': False, 'message': 'All fields required'}
        
        # Check for duplicates (in real system, would query B+ tree)
        members_table, _ = self.db_manager.get_table(self.core_db, 'members')
        all_members = members_table.get_all()
        
        for existing_member in all_members:
            if existing_member[1]['username'] == username:
                return {'success': False, 'message': f'Username {username} already exists'}
            if existing_member[1]['email'] == email:
                return {'success': False, 'message': f'Email {email} already registered'}
        
        # Create member record
        member_id = self._next_table_id('members', 'member_id')
        
        member_record = {
            'member_id': member_id,
            'username': username,
            'email': email,
            'full_name': full_name,
            'department': department,
            'status': 'active',
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        members_table.insert(member_record)
        
        # Create corresponding credential record
        try:
            credential_id = self._next_table_id('credentials', 'credential_id')
            
            password_hash, salt = hash_password(password)
            credential_record = {
                'credential_id': credential_id,
                'member_id': member_id,
                'password_hash': password_hash,
                'salt': salt,
                'last_login': None,
                'login_attempts': 0,
                'locked': 0,
                'created_at': timestamp,
                'updated_at': timestamp
            }
            
            credentials_table, _ = self.db_manager.get_table(self.core_db, 'credentials')
            credentials_table.insert(credential_record)
            
            # Log audit entry
            self._log_audit('create', 'members', member_id, member_id, 
                          f'Created member {username}')
            
            return {
                'success': True,
                'member_id': member_id,
                'message': f'Member {username} created successfully',
                'record': member_record
            }
        
        except Exception as e:
            # Rollback: delete member if credential creation fails
            members_table.delete(member_id)
            return {
                'success': False,
                'message': f'Credential creation failed: {str(e)}. Member creation rolled back.'
            }
    
    def delete_member(self, member_id):
        """
        Delete a member and all related data (cascade delete).
        
        Ensures:
        - Credential record is deleted
        - Group mappings are removed
        - Audit log is updated
        
        Returns:
            dict: {'success': bool, 'deleted_count': int, 'message': str}
        """
        timestamp = datetime.now().isoformat()
        deleted_count = 0
        
        try:
            # Get member info for audit
            members_table, _ = self.db_manager.get_table(self.core_db, 'members')
            member = members_table.get(member_id)
            
            if not member:
                return {'success': False, 'message': f'Member {member_id} not found'}
            
            # Delete credential(s) associated with member
            credentials_table, _ = self.db_manager.get_table(self.core_db, 'credentials')
            all_credentials = credentials_table.get_all()
            
            for cred_id, cred_data in all_credentials:
                if cred_data['member_id'] == member_id:
                    credentials_table.delete(cred_id)
                    deleted_count += 1
            
            # Delete group mappings
            mappings_table, _ = self.db_manager.get_table(self.core_db, 'member_group_mappings')
            all_mappings = mappings_table.get_all()
            
            for mapping_id, mapping_data in all_mappings:
                if mapping_data['member_id'] == member_id:
                    mappings_table.delete(mapping_id)
                    deleted_count += 1
            
            # Delete member record
            members_table.delete(member_id)
            deleted_count += 1
            
            # Log audit
            self._log_audit('delete', 'members', member_id, member_id,
                          f'Deleted member {member["username"]} and {deleted_count-1} related records')
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Member {member_id} deleted with {deleted_count} total records removed'
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Delete failed: {str(e)}'}
    
    def update_member(self, member_id, updates):
        """
        Update member record with audit trail.
        
        Args:
            member_id: Member to update
            updates: dict of fields to update
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        timestamp = datetime.now().isoformat()
        
        try:
            members_table, _ = self.db_manager.get_table(self.core_db, 'members')
            member = members_table.get(member_id)
            
            if not member:
                return {'success': False, 'message': f'Member {member_id} not found'}
            
            # Create updated record
            updated_member = member.copy()
            updated_member.update(updates)
            updated_member['updated_at'] = timestamp
            
            # Update in table
            members_table.update(member_id, updated_member)
            
            # Log audit
            self._log_audit('update', 'members', member_id, member_id,
                          f'Updated member {member_id}: {str(updates)}')
            
            return {
                'success': True,
                'message': f'Member {member_id} updated successfully',
                'record': updated_member
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Update failed: {str(e)}'}
    
    def get_member(self, member_id):
        """Retrieve member record by ID."""
        try:
            members_table, _ = self.db_manager.get_table(self.core_db, 'members')
            return members_table.get(member_id)
        except Exception as e:
            return None
    
    def list_all_members(self):
        """Get all members."""
        try:
            members_table, _ = self.db_manager.get_table(self.core_db, 'members')
            records = members_table.get_all()
            return [record[1] for record in records]
        except Exception as e:
            return []
    
    def authenticate_member(self, username, password):
        """
        Authenticate a member by username and password.
        
        Returns:
            dict: {'authenticated': bool, 'member_id': int/None, 'message': str}
        """
        try:
            # Find member by username
            members_table, _ = self.db_manager.get_table(self.core_db, 'members')
            all_members = members_table.get_all()
            
            member = None
            for _, member_data in all_members:
                if member_data['username'] == username:
                    member = member_data
                    break
            
            if not member:
                return {'authenticated': False, 'message': 'Invalid username'}
            
            if member['status'] != 'active':
                return {'authenticated': False, 'message': f'Account is {member["status"]}'}
            
            # Get credentials
            credentials_table, _ = self.db_manager.get_table(self.core_db, 'credentials')
            all_credentials = credentials_table.get_all()
            
            credential = None
            for _, cred_data in all_credentials:
                if cred_data['member_id'] == member['member_id']:
                    credential = cred_data
                    break
            
            if not credential:
                return {'authenticated': False, 'message': 'Credential record not found'}
            
            if credential['locked']:
                return {'authenticated': False, 'message': 'Account is locked'}
            
            # Verify password
            if verify_password(password, credential['password_hash'], credential['salt']):
                self._log_audit('login', 'members', member['member_id'], member['member_id'],
                              f'Successful login for {username}')
                return {
                    'authenticated': True,
                    'member_id': member['member_id'],
                    'message': 'Authentication successful'
                }
            else:
                self._log_audit('login', 'members', member['member_id'], member['member_id'],
                              f'Failed login attempt for {username}')
                return {'authenticated': False, 'message': 'Invalid password'}
        
        except Exception as e:
            return {'authenticated': False, 'message': f'Auth error: {str(e)}'}
    
    def _log_audit(self, action_type, table_name, record_id, member_id, details):
        """Record audit log entry."""
        try:
            audit_table, _ = self.db_manager.get_table(self.core_db, 'audit_log')
            audit_record = {
                'audit_id': self._next_table_id('audit_log', 'audit_id'),
                'action_type': action_type,
                'table_name': table_name,
                'record_id': record_id,
                'member_id': member_id,
                'change_details': details,
                'timestamp': datetime.now().isoformat()
            }
            audit_table.insert(audit_record)
            self.audit_log.append(audit_record)
        except Exception as e:
            pass  # Silently fail audit logging to not block operations

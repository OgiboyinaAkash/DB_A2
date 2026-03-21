"""
Group Management System
Handles groups and member-to-group mappings.
Maintains referential integrity between members and groups.
"""

from datetime import datetime


class GroupManager:
    """Manages groups and member-group relationships."""
    
    def __init__(self, db_manager, core_db_name='system_core'):
        self.db_manager = db_manager
        self.core_db = core_db_name

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
    
    def create_group(self, group_name, description):
        """
        Create a new group.
        
        Returns:
            dict: {'success': bool, 'group_id': int, 'message': str}
        """
        timestamp = datetime.now().isoformat()
        
        if not group_name:
            return {'success': False, 'message': 'Group name is required'}
        
        # Check for duplicate group names
        groups_table, _ = self.db_manager.get_table(self.core_db, 'groups')
        all_groups = groups_table.get_all()
        
        for _, group_data in all_groups:
            if group_data['group_name'] == group_name:
                return {'success': False, 'message': f'Group {group_name} already exists'}
        
        group_id = self._next_table_id('groups', 'group_id')
        
        group_record = {
            'group_id': group_id,
            'group_name': group_name,
            'description': description or '',
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        groups_table.insert(group_record)
        
        return {
            'success': True,
            'group_id': group_id,
            'message': f'Group {group_name} created successfully',
            'record': group_record
        }
    
    def delete_group(self, group_id):
        """
        Delete a group and all member mappings for it.
        
        Returns:
            dict: {'success': bool, 'deleted_mappings': int, 'message': str}
        """
        try:
            groups_table, _ = self.db_manager.get_table(self.core_db, 'groups')
            group = groups_table.get(group_id)
            
            if not group:
                return {'success': False, 'message': f'Group {group_id} not found'}
            
            # Delete all mappings for this group
            mappings_table, _ = self.db_manager.get_table(self.core_db, 'member_group_mappings')
            all_mappings = mappings_table.get_all()
            
            deleted_mappings = 0
            for mapping_id, mapping_data in all_mappings:
                if mapping_data['group_id'] == group_id:
                    mappings_table.delete(mapping_id)
                    deleted_mappings += 1
            
            # Delete group
            groups_table.delete(group_id)
            
            return {
                'success': True,
                'deleted_mappings': deleted_mappings,
                'message': f'Group {group["group_name"]} deleted with {deleted_mappings} members removed'
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Delete failed: {str(e)}'}
    
    def add_member_to_group(self, member_id, group_id, role='user'):
        """
        Add a member to a group.
        
        Args:
            member_id: Member to add
            group_id: Group to add to
            role: Role in group ('admin', 'user', 'viewer')
        
        Returns:
            dict: {'success': bool, 'mapping_id': int, 'message': str}
        """
        timestamp = datetime.now().isoformat()
        
        try:
            # Verify member exists
            members_table, _ = self.db_manager.get_table(self.core_db, 'members')
            member = members_table.get(member_id)
            if not member:
                return {'success': False, 'message': f'Member {member_id} not found'}
            
            # Verify group exists
            groups_table, _ = self.db_manager.get_table(self.core_db, 'groups')
            group = groups_table.get(group_id)
            if not group:
                return {'success': False, 'message': f'Group {group_id} not found'}
            
            # Check for duplicate mapping
            mappings_table, _ = self.db_manager.get_table(self.core_db, 'member_group_mappings')
            all_mappings = mappings_table.get_all()
            
            for _, mapping_data in all_mappings:
                if mapping_data['member_id'] == member_id and mapping_data['group_id'] == group_id:
                    return {'success': False, 'message': f'Member {member_id} already in group {group_id}'}
            
            mapping_id = self._next_table_id('member_group_mappings', 'mapping_id')
            
            mapping_record = {
                'mapping_id': mapping_id,
                'member_id': member_id,
                'group_id': group_id,
                'role_in_group': role,
                'assigned_at': timestamp
            }
            
            mappings_table.insert(mapping_record)
            
            return {
                'success': True,
                'mapping_id': mapping_id,
                'message': f'Member {member_id} added to group {group_id} as {role}',
                'record': mapping_record
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Add member failed: {str(e)}'}
    
    def remove_member_from_group(self, member_id, group_id):
        """
        Remove a member from a group.
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            mappings_table, _ = self.db_manager.get_table(self.core_db, 'member_group_mappings')
            all_mappings = mappings_table.get_all()
            
            for mapping_id, mapping_data in all_mappings:
                if mapping_data['member_id'] == member_id and mapping_data['group_id'] == group_id:
                    mappings_table.delete(mapping_id)
                    return {
                        'success': True,
                        'message': f'Member {member_id} removed from group {group_id}'
                    }
            
            return {'success': False, 'message': f'Mapping not found for member {member_id} in group {group_id}'}
        
        except Exception as e:
            return {'success': False, 'message': f'Remove failed: {str(e)}'}
    
    def get_group_members(self, group_id):
        """
        Get all members in a group.
        
        Returns:
            list: List of member records
        """
        try:
            mappings_table, _ = self.db_manager.get_table(self.core_db, 'member_group_mappings')
            members_table, _ = self.db_manager.get_table(self.core_db, 'members')
            
            all_mappings = mappings_table.get_all()
            member_ids = [mapping_data['member_id'] for _, mapping_data in all_mappings 
                         if mapping_data['group_id'] == group_id]
            
            members = []
            for member_id in member_ids:
                member = members_table.get(member_id)
                if member:
                    members.append(member)
            
            return members
        
        except Exception as e:
            return []
    
    def get_member_groups(self, member_id):
        """
        Get all groups a member belongs to.
        
        Returns:
            list: List of group records with role information
        """
        try:
            mappings_table, _ = self.db_manager.get_table(self.core_db, 'member_group_mappings')
            groups_table, _ = self.db_manager.get_table(self.core_db, 'groups')
            
            all_mappings = mappings_table.get_all()
            group_data = []
            
            for _, mapping_data in all_mappings:
                if mapping_data['member_id'] == member_id:
                    group = groups_table.get(mapping_data['group_id'])
                    if group:
                        group['role_in_group'] = mapping_data['role_in_group']
                        group_data.append(group)
            
            return group_data
        
        except Exception as e:
            return []
    
    def list_all_groups(self):
        """Get all groups."""
        try:
            groups_table, _ = self.db_manager.get_table(self.core_db, 'groups')
            records = groups_table.get_all()
            return [record[1] for record in records]
        except Exception as e:
            return []

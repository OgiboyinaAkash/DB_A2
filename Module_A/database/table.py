try:
    from .bplustree import BPlusTree
except ImportError:
    from bplustree import BPlusTree

class Table:
    def __init__(self, name, schema, order=8, search_key=None):
        self.name = name                             # Name of the table
        self.schema = schema                         # Table schema: dict of {column_name: data_type}
        self.order = order                           # Order of the B+ Tree (max number of children)
        self.data = BPlusTree(order=order)           # Underlying B+ Tree to store the data
        self.search_key = search_key                 # Primary or search key used for indexing (must be in schema)

    def validate_record(self, record):
        """
        Validate that the given record matches the table schema:
        - All required columns are present
        - Data types are correct
        """
        if not isinstance(record, dict):
            return False, "Record must be a dictionary"

        missing_fields = [field for field in self.schema if field not in record]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"

        for field, expected_type in self.schema.items():
            value = record.get(field)
            if value is None:
                continue
            if expected_type == float and isinstance(value, int):
                continue
            if not isinstance(value, expected_type):
                return False, (
                    f"Invalid type for '{field}': expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )

        return True, "Record is valid"

    def insert(self, record):
        """
        Insert a new record into the table.
        The record should be a dictionary matching the schema.
        The key used for insertion should be the value of the `search_key` field.
        """
        if self.search_key is None:
            return False, "Table search_key is not configured"

        is_valid, message = self.validate_record(record)
        if not is_valid:
            return False, message

        if self.search_key not in record:
            return False, f"search_key '{self.search_key}' must be present in record"

        record_id = record[self.search_key]
        self.data.insert(record_id, record)
        return True, record_id

    def get(self, record_id):
        """
        Retrieve a single record by its ID (i.e., the value of the `search_key`)
        """
        return self.data.search(record_id)

    def get_all(self):
        """
        Retrieve all records stored in the table in sorted order by search key
        """
        return self.data.get_all()

    def update(self, record_id, new_record):
        """
        Update a record identified by `record_id` with `new_record` data.
        Usually overwrites the existing entry.
        """
        existing = self.get(record_id)
        if existing is None:
            return False, f"Record with id '{record_id}' not found"

        merged = existing.copy()
        merged.update(new_record)

        if self.search_key not in merged:
            return False, f"search_key '{self.search_key}' missing after update"

        if merged[self.search_key] != record_id:
            return False, "Updating search_key value is not supported"

        is_valid, message = self.validate_record(merged)
        if not is_valid:
            return False, message

        updated = self.data.update(record_id, merged)
        if not updated:
            return False, "Update failed"
        return True, f"Record '{record_id}' updated successfully"

    def delete(self, record_id):
        """
        Delete the record from the table by its `record_id`
        """
        deleted = self.data.delete(record_id)
        if not deleted:
            return False, f"Record with id '{record_id}' not found"
        return True, f"Record '{record_id}' deleted successfully"

    def range_query(self, *args):
        """
        Perform a range query using the search key.
        Returns records where start_value <= key <= end_value
        """
        if len(args) == 2:
            start_value, end_value = args
        elif len(args) == 3:
            _, start_value, end_value = args
        else:
            raise ValueError("range_query expects (start, end) or (field, start, end)")
        return self.data.range_query(start_value, end_value)

    def search(self, constraints):
        """
        Perform a linear scan over table records using exact-match constraints.
        """
        if not isinstance(constraints, dict):
            return []

        results = []
        for record_id, record in self.get_all():
            matched = True
            for field, expected_value in constraints.items():
                if record.get(field) != expected_value:
                    matched = False
                    break
            if matched:
                results.append((record_id, record))
        return results

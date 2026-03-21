class BruteForceDB:
    """Simple list-backed store used as a brute-force baseline."""

    def __init__(self):
        self.records = []

    def insert(self, key, value):
        for idx, (existing_key, _) in enumerate(self.records):
            if existing_key == key:
                self.records[idx] = (key, value)
                return
        self.records.append((key, value))

    def search(self, key):
        for existing_key, value in self.records:
            if existing_key == key:
                return value
        return None

    def delete(self, key):
        for idx, (existing_key, _) in enumerate(self.records):
            if existing_key == key:
                self.records.pop(idx)
                return True
        return False

    def range_query(self, start_key, end_key):
        result = []
        for key, value in self.records:
            if start_key <= key <= end_key:
                result.append((key, value))
        result.sort(key=lambda item: item[0])
        return result

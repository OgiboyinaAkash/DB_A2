import importlib

try:
    Digraph = importlib.import_module("graphviz").Digraph
except ModuleNotFoundError:
    Digraph = None
from bisect import bisect_left, bisect_right
from math import ceil

# B+ Tree Node class. Can be used as either internal or leaf node.
class BPlusTreeNode:
    def __init__(self, order, is_leaf=True):
        self.order = order                  # Maximum number of children a node can have
        self.is_leaf = is_leaf              # Flag to check if node is a leaf
        self.keys = []                      # List of keys in the node
        self.values = []                    # Used in leaf nodes to store associated values
        self.children = []                  # Used in internal nodes to store child pointers
        self.next = None                    # Points to next leaf node for range queries

    def is_full(self):
        # A node is full if it has reached the maximum number of keys (order - 1)
        return len(self.keys) >= self.order - 1


class BPlusTree:
    def __init__(self, order=8):
        if order < 3:
            raise ValueError("B+ Tree order must be at least 3")
        self.order = order                          # Maximum number of children per internal node
        self.root = BPlusTreeNode(order)            # Start with an empty leaf node as root

    def _min_leaf_keys(self):
        return ceil((self.order - 1) / 2)

    def _min_internal_keys(self):
        return ceil(self.order / 2) - 1

    def _leftmost_leaf(self):
        node = self.root
        while not node.is_leaf and node.children:
            node = node.children[0]
        return node

    def _first_key(self, node):
        current = node
        while not current.is_leaf and current.children:
            current = current.children[0]
        return current.keys[0] if current.keys else None

    def _refresh_internal_keys(self, node):
        if node.is_leaf:
            return
        node.keys = [self._first_key(node.children[i]) for i in range(1, len(node.children))]


    def search(self, key):
        """Search for a key in the B+ tree and return the associated value"""
        return self._search(self.root, key)

    def _search(self, node, key):
        """Helper function to recursively search for a key starting from the given node"""
        if node.is_leaf:
            idx = bisect_left(node.keys, key)
            if idx < len(node.keys) and node.keys[idx] == key:
                return node.values[idx]
            return None

        idx = bisect_right(node.keys, key)
        return self._search(node.children[idx], key)


    def insert(self, key, value):
        """Insert a new key-value pair into the B+ tree"""
        root = self.root

        if root.is_full():
            new_root = BPlusTreeNode(self.order, is_leaf=False)
            new_root.children.append(root)
            self.root = new_root
            self._split_child(new_root, 0)

        self._insert_non_full(self.root, key, value)

    def _insert_non_full(self, node, key, value):
        """Insert key-value into a node that is not full"""
        if node.is_leaf:
            idx = bisect_left(node.keys, key)
            if idx < len(node.keys) and node.keys[idx] == key:
                node.values[idx] = value
                return

            node.keys.insert(idx, key)
            node.values.insert(idx, value)
            return

        idx = bisect_right(node.keys, key)
        child = node.children[idx]

        if child.is_full():
            self._split_child(node, idx)
            idx = bisect_right(node.keys, key)

        self._insert_non_full(node.children[idx], key, value)
        self._refresh_internal_keys(node)

    def _split_child(self, parent, index):
        """
        Split the child node at given index in the parent.
        This is triggered when the child is full.
        """
        child = parent.children[index]
        new_node = BPlusTreeNode(self.order, is_leaf=child.is_leaf)

        if child.is_leaf:
            split_index = (len(child.keys) + 1) // 2

            new_node.keys = child.keys[split_index:]
            new_node.values = child.values[split_index:]

            child.keys = child.keys[:split_index]
            child.values = child.values[:split_index]

            new_node.next = child.next
            child.next = new_node
        else:
            split_children = len(child.children) // 2

            new_node.children = child.children[split_children:]
            child.children = child.children[:split_children]

            self._refresh_internal_keys(child)
            self._refresh_internal_keys(new_node)

        parent.children.insert(index + 1, new_node)
        self._refresh_internal_keys(parent)


    def delete(self, key):
        """Delete a key from the B+ tree"""
        deleted = self._delete(self.root, key)

        if not self.root.is_leaf and len(self.root.children) == 1:
            self.root = self.root.children[0]

        if self.root.is_leaf and not self.root.keys:
            self.root = BPlusTreeNode(self.order)

        return deleted

    def _delete(self, node, key):
        """Recursive helper function for delete operation"""
        if node.is_leaf:
            idx = bisect_left(node.keys, key)
            if idx >= len(node.keys) or node.keys[idx] != key:
                return False
            node.keys.pop(idx)
            node.values.pop(idx)
            return True

        idx = bisect_right(node.keys, key)
        deleted = self._delete(node.children[idx], key)
        if not deleted:
            return False

        if idx >= len(node.children):
            idx = len(node.children) - 1

        child = node.children[idx]
        min_keys = self._min_leaf_keys() if child.is_leaf else self._min_internal_keys()

        if len(child.keys) < min_keys:
            idx = self._fill_child(node, idx)

        self._refresh_internal_keys(node)
        return True

    def _fill_child(self, node, index):
        """Ensure that the child node has enough keys to allow safe deletion"""
        child = node.children[index]
        min_keys = self._min_leaf_keys() if child.is_leaf else self._min_internal_keys()

        if index > 0:
            left_sibling = node.children[index - 1]
            left_min = self._min_leaf_keys() if left_sibling.is_leaf else self._min_internal_keys()
            if len(left_sibling.keys) > left_min:
                self._borrow_from_prev(node, index)
                return index

        if index < len(node.children) - 1:
            right_sibling = node.children[index + 1]
            right_min = self._min_leaf_keys() if right_sibling.is_leaf else self._min_internal_keys()
            if len(right_sibling.keys) > right_min:
                self._borrow_from_next(node, index)
                return index

        if index > 0:
            self._merge(node, index - 1)
            return index - 1

        if index < len(node.children) - 1:
            self._merge(node, index)
            return index

        # Single child case; no structural action needed.
        if len(child.keys) < min_keys:
            self._refresh_internal_keys(node)
        return index

    def _borrow_from_prev(self, node, index):
        """Borrow a key from the left sibling"""
        child = node.children[index]
        left_sibling = node.children[index - 1]

        if child.is_leaf:
            child.keys.insert(0, left_sibling.keys.pop())
            child.values.insert(0, left_sibling.values.pop())
        else:
            moved_child = left_sibling.children.pop()
            child.children.insert(0, moved_child)
            self._refresh_internal_keys(left_sibling)
            self._refresh_internal_keys(child)

        self._refresh_internal_keys(node)

    def _borrow_from_next(self, node, index):
        """Borrow a key from the right sibling"""
        child = node.children[index]
        right_sibling = node.children[index + 1]

        if child.is_leaf:
            child.keys.append(right_sibling.keys.pop(0))
            child.values.append(right_sibling.values.pop(0))
        else:
            moved_child = right_sibling.children.pop(0)
            child.children.append(moved_child)
            self._refresh_internal_keys(right_sibling)
            self._refresh_internal_keys(child)

        self._refresh_internal_keys(node)

    def _merge(self, node, index):
        """Merge two child nodes into one"""
        left_child = node.children[index]
        right_child = node.children[index + 1]

        if left_child.is_leaf:
            left_child.keys.extend(right_child.keys)
            left_child.values.extend(right_child.values)
            left_child.next = right_child.next
        else:
            left_child.children.extend(right_child.children)
            self._refresh_internal_keys(left_child)

        node.children.pop(index + 1)
        self._refresh_internal_keys(node)


    def update(self, key, new_value):
        """Update the value associated with a key"""
        node = self.root
        while not node.is_leaf:
            idx = bisect_right(node.keys, key)
            node = node.children[idx]

        idx = bisect_left(node.keys, key)
        if idx < len(node.keys) and node.keys[idx] == key:
            node.values[idx] = new_value
            return True
        return False


    def range_query(self, start_key, end_key):
        """
        Return all key-value pairs where start_key <= key <= end_key.
        Utilizes the linked list structure of leaf nodes.
        """
        if start_key > end_key:
            return []

        result = []
        node = self.root

        while not node.is_leaf:
            idx = bisect_right(node.keys, start_key)
            node = node.children[idx]

        while node:
            for key, value in zip(node.keys, node.values):
                if key < start_key:
                    continue
                if key > end_key:
                    return result
                result.append((key, value))
            node = node.next

        return result

    def get_all(self):
        """Get all key-value pairs in the tree in sorted order"""
        result = []
        leaf = self._leftmost_leaf()
        while leaf:
            result.extend(zip(leaf.keys, leaf.values))
            leaf = leaf.next
        return result

    def _get_all(self, node, result):
        """Recursive helper function to gather all key-value pairs"""
        if node.is_leaf:
            result.extend(zip(node.keys, node.values))
            return

        for child in node.children:
            self._get_all(child, result)


    def visualize_tree(self, filename=None):
        """
        Visualize the tree using graphviz.
        Optional filename can be provided to save the output.
        """
        if Digraph is None:
            raise ImportError(
                "graphviz package is required for visualization. Install it with: pip install graphviz"
            )

        dot = Digraph(comment="B+ Tree")
        self._add_nodes(dot, self.root)
        self._add_edges(dot, self.root)
        self._add_leaf_links(dot)

        if filename:
            dot.render(filename, format="png", cleanup=True)

        return dot

    def _add_nodes(self, dot, node):
        """Add graph nodes for visualization"""
        node_id = str(id(node))
        if node.is_leaf:
            keys_str = ", ".join(str(key) for key in node.keys)
            label = f"Leaf\n[{keys_str}]"
            dot.node(node_id, label=label, shape="box", style="filled", fillcolor="lightblue")
            return

        keys_str = ", ".join(str(key) for key in node.keys)
        label = f"Internal\n[{keys_str}]"
        dot.node(node_id, label=label, shape="box", style="filled", fillcolor="lightgray")
        for child in node.children:
            self._add_nodes(dot, child)

    def _add_edges(self, dot, node):
        """Add graph edges for visualization"""
        if node.is_leaf:
            return

        for child in node.children:
            dot.edge(str(id(node)), str(id(child)))
            self._add_edges(dot, child)

    def _add_leaf_links(self, dot):
        """Add dashed edges to represent linked leaf nodes."""
        leaf = self._leftmost_leaf()
        while leaf and leaf.next:
            dot.edge(
                str(id(leaf)),
                str(id(leaf.next)),
                style="dashed",
                color="blue",
                label="next",
                weight="0",
            )
            leaf = leaf.next

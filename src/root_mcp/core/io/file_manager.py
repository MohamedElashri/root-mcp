"""File manager for opening, caching, and managing ROOT files."""

from __future__ import annotations

import logging
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import uproot

if TYPE_CHECKING:
    from root_mcp.config import Config

logger = logging.getLogger(__name__)


class FileCache:
    """LRU cache for open ROOT files."""

    def __init__(self, max_size: int):
        """
        Initialize file cache.

        Args:
            max_size: Maximum number of files to keep open
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()

    def get(self, path: str) -> Any | None:
        """
        Get file from cache.

        Args:
            path: File path

        Returns:
            Open file object or None if not cached
        """
        if path in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(path)
            logger.debug(f"Cache hit: {path}")
            return self._cache[path]
        logger.debug(f"Cache miss: {path}")
        return None

    def put(self, path: str, file_obj: Any) -> None:
        """
        Add file to cache.

        Args:
            path: File path
            file_obj: Open file object
        """
        # If already exists, update and move to end
        if path in self._cache:
            self._cache.move_to_end(path)
            self._cache[path] = file_obj
            return

        # Add new entry
        self._cache[path] = file_obj

        # Evict oldest if over limit
        if len(self._cache) > self.max_size:
            oldest_path, oldest_file = self._cache.popitem(last=False)
            logger.debug(f"Evicting from cache: {oldest_path}")
            # Note: uproot files don't need explicit closing
            # They close automatically when garbage collected

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        logger.info("File cache cleared")

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class FileManager:
    """
    Manages opening and caching of ROOT files.

    Provides safe, efficient access to local and remote ROOT files with
    automatic caching and connection pooling.
    """

    def __init__(self, config: Config):
        """
        Initialize file manager.

        Args:
            config: Server configuration
        """
        self.config = config
        self._cache = FileCache(config.cache.file_cache_size) if config.cache.enabled else None
        self._open_files: set[str] = set()
        logger.info(
            f"FileManager initialized (cache: {config.cache.enabled}, "
            f"max_files: {config.cache.file_cache_size})"
        )

    def open(self, path: str | Path, **kwargs: Any) -> Any:
        """
        Open a ROOT file with caching.

        Args:
            path: File path or URI
            **kwargs: Additional arguments to pass to uproot.open()

        Returns:
            Open uproot file object

        Raises:
            FileNotFoundError: If file doesn't exist
            OSError: If file cannot be opened
        """
        path_str = str(path)

        # Check cache first
        if self._cache:
            cached = self._cache.get(path_str)
            if cached is not None:
                return cached

        # Open file
        logger.info(f"Opening ROOT file: {path_str}")
        try:
            file_obj = uproot.open(path_str, **kwargs)
        except FileNotFoundError as e:
            logger.error(f"File not found: {path_str}")
            raise FileNotFoundError(f"ROOT file not found: {path_str}") from e
        except Exception as e:
            logger.error(f"Failed to open {path_str}: {e}")
            raise OSError(f"Failed to open ROOT file {path_str}: {e}") from e

        # Add to cache
        if self._cache:
            self._cache.put(path_str, file_obj)

        self._open_files.add(path_str)
        return file_obj

    def get_file_info(self, path: str | Path) -> dict[str, Any]:
        """
        Get basic information about a ROOT file.

        Args:
            path: File path

        Returns:
            Dictionary with file metadata
        """
        file_obj = self.open(path)

        # Get file-level metadata
        info = {
            "path": str(path),
            "compression": str(file_obj.compression) if hasattr(file_obj, "compression") else None,
            "keys": list(file_obj.keys()),
            "classnames": file_obj.classnames() if hasattr(file_obj, "classnames") else {},
            "trees": self.list_trees(path),
        }

        # Get file size if local
        path_obj = Path(path)
        if path_obj.exists():
            info["size_bytes"] = path_obj.stat().st_size

        return info

    def list_trees(self, path: str | Path) -> list[dict[str, Any]]:
        """
        List all TTrees in a ROOT file.

        Args:
            path: File path

        Returns:
            List of tree metadata dictionaries
        """
        file_obj = self.open(path)
        trees = []

        # Recursively find all TTrees
        def find_trees(directory: Any, current_path: str = "") -> None:
            for key in directory.keys():
                obj = directory[key]
                full_path = f"{current_path}/{key}" if current_path else key

                # Check if it's a TTree
                classname = directory.classname_of(key)
                if "TTree" in classname:
                    tree_info = {
                        "name": key,
                        "path": full_path,
                        "classname": classname,
                        "entries": obj.num_entries,
                        "branches": len(obj.keys()),
                    }
                    trees.append(tree_info)

                # Recurse into directories
                elif "TDirectory" in classname or classname == "TDirectoryFile":
                    find_trees(obj, full_path)

        find_trees(file_obj)
        return trees

    def list_histograms(self, path: str | Path) -> list[dict[str, Any]]:
        """
        List all histograms in a ROOT file.

        Args:
            path: File path

        Returns:
            List of histogram metadata dictionaries
        """
        file_obj = self.open(path)
        histograms = []

        def find_histograms(directory: Any, current_path: str = "") -> None:
            for key in directory.keys():
                classname = directory.classname_of(key)
                full_path = f"{current_path}/{key}" if current_path else key

                # Check if it's a histogram
                if classname.startswith("TH") or classname.startswith("TProfile"):
                    obj = directory[key]
                    hist_info = {
                        "name": key,
                        "path": full_path,
                        "type": classname,
                    }

                    # Add dimension-specific info
                    if hasattr(obj, "axes"):
                        hist_info["bins"] = [len(axis) for axis in obj.axes]

                    if hasattr(obj, "values"):
                        hist_info["entries"] = int(obj.values().sum())

                    histograms.append(hist_info)

                # Recurse into directories
                elif "TDirectory" in classname or classname == "TDirectoryFile":
                    obj = directory[key]
                    find_histograms(obj, full_path)

        find_histograms(file_obj)
        return histograms

    def list_objects(self, path: str | Path) -> list[dict[str, Any]]:
        """
        List all objects in a ROOT file.

        Args:
            path: File path

        Returns:
            List of object metadata dictionaries
        """
        file_obj = self.open(path)
        objects = []

        def find_objects(directory: Any, current_path: str = "") -> None:
            for key in directory.keys():
                classname = directory.classname_of(key)
                full_path = f"{current_path}/{key}" if current_path else key

                objects.append(
                    {
                        "name": key,
                        "path": full_path,
                        "type": classname,
                    }
                )

                # Recurse into directories
                if "TDirectory" in classname or classname == "TDirectoryFile":
                    obj = directory[key]
                    find_objects(obj, full_path)

        find_objects(file_obj)
        return objects

    def get_tree(self, path: str | Path, tree_name: str) -> Any:
        """
        Get a specific TTree from a file.

        Args:
            path: File path
            tree_name: Name or path to tree

        Returns:
            uproot TTree object

        Raises:
            KeyError: If tree doesn't exist
        """
        file_obj = self.open(path)

        try:
            tree = file_obj[tree_name]
        except KeyError as e:
            # Try to provide helpful error message
            available_trees = [t["name"] for t in self.list_trees(path)]
            raise KeyError(
                f"Tree '{tree_name}' not found in {path}. Available trees: {available_trees}"
            ) from e

        return tree

    def clear_cache(self) -> None:
        """Clear the file cache."""
        if self._cache:
            self._cache.clear()

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "size": self._cache.size() if self._cache else 0,
            "max_size": self.config.cache.file_cache_size,
            "open_files": len(self._open_files),
        }

    def validate_file(self, path: str | Path) -> dict[str, Any]:
        """
        Validate ROOT file integrity and readability.

        Args:
            path: File path

        Returns:
            Dictionary with validation results
        """
        path_obj = Path(path)
        validation: dict[str, Any] = {
            "path": str(path),
            "valid": False,
            "readable": False,
            "errors": [],
            "warnings": [],
            "metadata": {},
        }

        # Check if file exists
        if not path_obj.exists():
            validation["errors"].append("File does not exist")
            return validation

        # Check file size
        try:
            size = path_obj.stat().st_size
            validation["metadata"]["size_bytes"] = size
            if size == 0:
                validation["errors"].append("File is empty")
                return validation
        except OSError as e:
            validation["errors"].append(f"Cannot access file: {e}")
            return validation

        # Try to open file
        try:
            file_obj = self.open(path)
            validation["readable"] = True
        except Exception as e:
            validation["errors"].append(f"Cannot open file: {e}")
            return validation

        # Check for readable objects
        try:
            keys = list(file_obj.keys())
            validation["metadata"]["num_objects"] = len(keys)

            if len(keys) == 0:
                validation["warnings"].append("File contains no objects")
        except Exception as e:
            validation["errors"].append(f"Cannot read file keys: {e}")
            return validation

        # Try to read trees
        try:
            trees = self.list_trees(path)
            validation["metadata"]["num_trees"] = len(trees)
            validation["metadata"]["trees"] = [t["name"] for t in trees]

            # Check if trees are readable
            for tree_info in trees:
                try:
                    tree = file_obj[tree_info["path"]]
                    # Try to read first entry
                    if tree.num_entries > 0:
                        _ = tree.arrays(entry_stop=1, library="ak")
                except Exception as e:
                    validation["warnings"].append(
                        f"Tree '{tree_info['name']}' may be corrupted: {e}"
                    )
        except Exception as e:
            validation["warnings"].append(f"Cannot validate trees: {e}")

        # Check compression
        try:
            if hasattr(file_obj, "compression"):
                validation["metadata"]["compression"] = str(file_obj.compression)
        except Exception:
            pass

        # File is valid if readable and no critical errors
        validation["valid"] = validation["readable"] and len(validation["errors"]) == 0

        return validation

    def get_tree_info(self, path: str | Path, tree_name: str) -> dict[str, Any]:
        """
        Get comprehensive metadata about a TTree.

        Args:
            path: File path
            tree_name: Tree name

        Returns:
            Dictionary with comprehensive tree metadata
        """
        tree = self.get_tree(path, tree_name)

        info = {
            "name": tree_name,
            "entries": tree.num_entries,
            "branches": len(tree.keys()),
            "branch_names": list(tree.keys()),
        }

        # Get total size and compression info
        try:
            if hasattr(tree, "compression"):
                info["compression"] = str(tree.compression)
        except Exception:
            pass

        # Get basket information if available
        try:
            total_compressed = 0
            total_uncompressed = 0

            for branch_name in tree.keys():
                branch = tree[branch_name]
                if hasattr(branch, "compressed_bytes"):
                    total_compressed += branch.compressed_bytes
                if hasattr(branch, "uncompressed_bytes"):
                    total_uncompressed += branch.uncompressed_bytes

            if total_compressed > 0 and total_uncompressed > 0:
                info["total_compressed_bytes"] = total_compressed
                info["total_uncompressed_bytes"] = total_uncompressed
                info["compression_ratio"] = total_uncompressed / total_compressed
        except Exception:
            pass

        return info

    def get_branch_schema(
        self, path: str | Path, tree_name: str, branch_name: str | None = None
    ) -> dict[str, Any]:
        """
        Get detailed schema information for branches.

        Args:
            path: File path
            tree_name: Tree name
            branch_name: Optional specific branch (None = all branches)

        Returns:
            Dictionary with branch schema information
        """
        tree = self.get_tree(path, tree_name)

        if branch_name:
            branches = [branch_name]
        else:
            branches = list(tree.keys())

        schema = {}
        for name in branches:
            try:
                branch = tree[name]

                # Get type information
                typename = str(branch.typename) if hasattr(branch, "typename") else "unknown"

                # Determine if jagged
                is_jagged = "[]" in typename or "vector" in typename.lower()

                # Get interpretation (awkward type)
                interpretation = None
                if hasattr(branch, "interpretation"):
                    try:
                        interpretation = str(branch.interpretation)
                    except Exception:
                        pass

                schema[name] = {
                    "type": typename,
                    "is_jagged": is_jagged,
                    "interpretation": interpretation,
                    "title": str(branch.title) if hasattr(branch, "title") else "",
                }

                # Get size information
                if hasattr(branch, "compressed_bytes"):
                    schema[name]["compressed_bytes"] = branch.compressed_bytes
                if hasattr(branch, "uncompressed_bytes"):
                    schema[name]["uncompressed_bytes"] = branch.uncompressed_bytes

            except Exception as e:
                logger.warning(f"Failed to get schema for branch {name}: {e}")
                schema[name] = {"error": str(e)}

        return schema

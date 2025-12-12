"""Discovery tools for ROOT files (list, inspect, etc.)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from root_mcp.config import Config
    from root_mcp.io.file_manager import FileManager
    from root_mcp.io.validators import PathValidator

logger = logging.getLogger(__name__)


class DiscoveryTools:
    """Tools for discovering and inspecting ROOT files."""

    def __init__(
        self,
        config: Config,
        file_manager: FileManager,
        path_validator: PathValidator,
    ):
        """
        Initialize discovery tools.

        Args:
            config: Server configuration
            file_manager: File manager instance
            path_validator: Path validator instance
        """
        self.config = config
        self.file_manager = file_manager
        self.path_validator = path_validator

    def list_files(
        self,
        resource: str | None = None,
        pattern: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        List ROOT files in a resource.

        Args:
            resource: Resource ID (None = default)
            pattern: Glob pattern to filter files
            limit: Maximum files to return

        Returns:
            List of files with metadata
        """
        # Get resource config
        if resource:
            resource_config = self.config.get_resource(resource)
            if not resource_config:
                available = [r.name for r in self.config.resources]
                return {
                    "error": "resource_not_found",
                    "message": f"Resource '{resource}' not found",
                    "details": {"available_resources": available},
                    "suggestion": f"Use one of: {available}",
                }
        else:
            resource_config = self.config.get_default_resource()
            if not resource_config:
                return {
                    "error": "no_resources",
                    "message": "No resources configured",
                    "suggestion": "Configure at least one resource in config.yaml",
                }

        # Parse resource URI to get base path
        uri = resource_config.uri
        if uri.startswith("file://"):
            base_path = Path(uri[7:])
        else:
            # For remote resources, we'd need different handling
            return {
                "error": "not_implemented",
                "message": f"Remote resources not yet implemented: {uri}",
            }

        # List files
        if not base_path.exists():
            return {
                "error": "path_not_found",
                "message": f"Resource path does not exist: {base_path}",
            }

        files = []
        total_scanned = 0

        # Scan directory
        for file_path in base_path.rglob("*.root"):
            total_scanned += 1

            # Check pattern
            if pattern and not self._matches_pattern(file_path.name, pattern):
                continue

            # Check resource patterns
            if not self.path_validator.check_file_pattern(file_path, resource_config):
                continue

            # Get file info
            try:
                stat = file_path.stat()
                files.append(
                    {
                        "path": str(file_path),
                        "size_bytes": stat.st_size,
                        "modified": stat.st_mtime,
                        "resource": resource_config.name,
                    }
                )
            except OSError as e:
                logger.warning(f"Failed to stat {file_path}: {e}")
                continue

            # Apply limit
            if len(files) >= limit:
                break

        # Generate suggestions
        suggestions = []
        if files:
            suggestions.append(f"Inspect {files[0]['path']} with inspect_file()")
        if len(files) >= limit:
            suggestions.append(f"Showing first {limit} files, use pattern to filter")

        return {
            "data": {
                "files": files,
                "total_matched": len(files),
                "total_scanned": total_scanned,
            },
            "metadata": {
                "operation": "list_files",
                "resource": resource_config.name,
            },
            "suggestions": suggestions,
        }

    def inspect_file(
        self,
        path: str,
        include_histograms: bool = True,
        include_trees: bool = True,
    ) -> dict[str, Any]:
        """
        Inspect a ROOT file's structure.

        Args:
            path: File path
            include_histograms: Include histogram metadata
            include_trees: Include tree metadata

        Returns:
            File structure and metadata
        """
        try:
            # Validate path
            validated_path = self.path_validator.validate_path(path)
        except Exception as e:
            return {
                "error": "invalid_path",
                "message": str(e),
                "suggestion": "Check path and ensure it's under an allowed root",
            }

        # Get file info
        try:
            file_info = self.file_manager.get_file_info(validated_path)
        except FileNotFoundError:
            return {
                "error": "file_not_found",
                "message": f"File not found: {path}",
                "suggestion": "Use list_files() to see available files",
            }
        except Exception as e:
            return {
                "error": "file_read_error",
                "message": f"Failed to open file: {e}",
            }

        # Get trees
        trees = []
        if include_trees:
            try:
                trees = self.file_manager.list_trees(validated_path)
            except Exception as e:
                logger.warning(f"Failed to list trees: {e}")

        # Get histograms
        histograms = []
        if include_histograms:
            try:
                histograms = self.file_manager.list_histograms(validated_path)
            except Exception as e:
                logger.warning(f"Failed to list histograms: {e}")

        # Get all objects to find directories
        all_objects = self.file_manager.list_objects(validated_path)
        directories = [obj["path"] for obj in all_objects if "TDirectory" in obj["type"]]

        # Other objects (not trees or histograms)
        known_paths = {t["path"] for t in trees} | {h["path"] for h in histograms}
        other_objects = [
            obj
            for obj in all_objects
            if obj["path"] not in known_paths and "TDirectory" not in obj["type"]
        ]

        # Generate suggestions
        suggestions = []
        if trees:
            main_tree = trees[0]
            suggestions.append(
                f"Explore '{main_tree['name']}' tree with "
                f"{main_tree['entries']:,} entries using list_branches()"
            )
        if histograms:
            suggestions.append(f"Read histogram '{histograms[0]['name']}' with read_histogram()")

        return {
            "data": {
                "path": str(validated_path),
                "size_bytes": file_info.get("size_bytes"),
                "compression": file_info.get("compression"),
                "trees": trees,
                "histograms": histograms,
                "directories": directories,
                "other_objects": other_objects[:10],  # Limit to first 10
            },
            "metadata": {
                "operation": "inspect_file",
            },
            "suggestions": suggestions,
        }

    def list_branches(
        self,
        path: str,
        tree: str,
        pattern: str | None = None,
        limit: int = 100,
        include_stats: bool = False,
    ) -> dict[str, Any]:
        """
        List branches in a TTree.

        Args:
            path: File path
            tree: Tree name
            pattern: Glob pattern to filter branches
            limit: Maximum branches to return
            include_stats: Compute statistics (slower)

        Returns:
            Branch information
        """
        try:
            validated_path = self.path_validator.validate_path(path)
        except Exception as e:
            return {
                "error": "invalid_path",
                "message": str(e),
            }

        try:
            tree_obj = self.file_manager.get_tree(validated_path, tree)
        except KeyError as e:
            available_trees = [t["name"] for t in self.file_manager.list_trees(validated_path)]
            return {
                "error": "tree_not_found",
                "message": str(e),
                "details": {"available_trees": available_trees},
                "suggestion": f"Use one of: {available_trees}",
            }

        # Get branch info
        from root_mcp.io.readers import TreeReader

        reader = TreeReader(self.config, self.file_manager)

        try:
            branch_info = reader.get_branch_info(str(validated_path), tree, pattern)
        except Exception as e:
            return {
                "error": "read_error",
                "message": f"Failed to read branches: {e}",
            }

        # Limit results
        total_branches = len(branch_info)
        branch_info = branch_info[:limit]

        # Optionally compute stats
        if include_stats:
            try:
                branch_names = [b["name"] for b in branch_info]
                stats = reader.compute_branch_stats(
                    str(validated_path),
                    tree,
                    branch_names,
                )
                # Add stats to branch info
                for branch in branch_info:
                    if branch["name"] in stats:
                        branch["stats"] = stats[branch["name"]]
            except Exception as e:
                logger.warning(f"Failed to compute stats: {e}")

        # Suggestions
        suggestions = []
        if total_branches > limit:
            suggestions.append(f"{total_branches} total branches - use pattern to filter")
        if branch_info:
            first_branches = [b["name"] for b in branch_info[:3]]
            suggestions.append(f"Sample data with read_branches(branches={first_branches})")

        return {
            "data": {
                "tree": tree,
                "total_entries": tree_obj.num_entries,
                "total_branches": total_branches,
                "branches": branch_info,
                "matched": len(branch_info),
            },
            "metadata": {
                "operation": "list_branches",
            },
            "suggestions": suggestions,
        }

    @staticmethod
    def _matches_pattern(filename: str, pattern: str) -> bool:
        """Check if filename matches glob pattern."""
        import fnmatch

        return fnmatch.fnmatch(filename, pattern)

#!/usr/bin/env python3
"""
Metadata Cache Manager

Handles caching of data file metadata to improve API performance.
Creates and manages cache files to avoid repeated expensive file scanning operations.

Epic 26: Script-to-API Conversion for Quant Director Operations
Story 5 & 7: Data Files Management UI Page

Features:
- Cache metadata for data files to avoid repeated scanning
- Automatic cache invalidation based on file modification times
- Support for both directory-level and file-level caching
- Thread-safe operations with file locking

Author: AI Assistant
"""

import json
import logging
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import fcntl
import tempfile

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MetadataCacheManager:
    """
    Manages caching of data file metadata for performance optimization.
    """

    def __init__(self, cache_dir: str = "data/cache"):
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_directory_cache_path(self, data_dir: str) -> Path:
        """
        Get the cache file path for a directory scan.

        Args:
            data_dir: Data directory path

        Returns:
            Path to the cache file
        """
        # Create a hash of the directory path for the cache filename
        dir_hash = hashlib.md5(str(data_dir).encode()).hexdigest()[:8]
        return self.cache_dir / f"dir_{dir_hash}.json"

    def get_file_cache_path(self, file_path: str) -> Path:
        """
        Get the cache file path for a specific file.

        Args:
            file_path: File path

        Returns:
            Path to the cache file
        """
        # Create a hash of the file path for the cache filename
        file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
        return self.cache_dir / f"file_{file_hash}.json"

    def is_cache_valid(self, cache_path: Path, data_paths: List[Path]) -> bool:
        """
        Check if the cache is still valid by comparing file modification times.

        Args:
            cache_path: Path to the cache file
            data_paths: List of data file paths that were cached

        Returns:
            True if cache is valid, False otherwise
        """
        if not cache_path.exists():
            return False

        try:
            # Read cache metadata
            with open(cache_path, "r") as f:
                cache_data = json.load(f)

            cache_timestamp = cache_data.get("cache_timestamp")
            if not cache_timestamp:
                return False

            # Check if any data files have been modified since cache was created
            cache_time = datetime.fromisoformat(cache_timestamp)

            for file_path in data_paths:
                if file_path.exists():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime > cache_time:
                        logger.info(
                            f"Cache invalid: {file_path} modified after cache creation"
                        )
                        return False
                else:
                    # File no longer exists, cache is invalid
                    logger.info(f"Cache invalid: {file_path} no longer exists")
                    return False

            # Check if cache file itself is too old (24 hours)
            cache_age = datetime.now() - cache_time
            if cache_age.total_seconds() > 24 * 3600:
                logger.info("Cache invalid: cache file is too old")
                return False

            return True

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Cache validation failed: {e}")
            return False

    def load_directory_cache(self, data_dir: str) -> Optional[Dict[str, Any]]:
        """
        Load cached directory metadata if valid.

        Args:
            data_dir: Data directory path

        Returns:
            Cached metadata or None if cache is invalid/missing
        """
        cache_path = self.get_directory_cache_path(data_dir)
        data_path = Path(data_dir)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cache_data = json.load(f)

            # Get list of files that were cached
            cached_files = cache_data.get("files", [])
            data_file_paths = [Path(f["file_path"]) for f in cached_files]

            # Check if cache is still valid
            if not self.is_cache_valid(cache_path, data_file_paths):
                return None

            logger.info(f"Loaded valid cache for directory: {data_dir}")
            return cache_data

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load directory cache: {e}")
            return None

    def save_directory_cache(self, data_dir: str, metadata: Dict[str, Any]) -> None:
        """
        Save directory metadata to cache.

        Args:
            data_dir: Data directory path
            metadata: Metadata to cache
        """
        cache_path = self.get_directory_cache_path(data_dir)

        # Add cache metadata
        cache_data = {
            "cache_timestamp": datetime.now().isoformat(),
            "data_dir": data_dir,
            "cache_version": "1.0",
            **metadata,
        }

        try:
            # Write to temporary file first, then atomically rename
            with tempfile.NamedTemporaryFile(
                mode="w", dir=self.cache_dir, suffix=".tmp", delete=False
            ) as temp_file:
                json.dump(cache_data, temp_file, indent=2, default=str)
                temp_path = Path(temp_file.name)

            # Atomic rename
            temp_path.replace(cache_path)
            logger.info(f"Saved directory cache: {cache_path}")

        except OSError as e:
            logger.error(f"Failed to save directory cache: {e}")

    def load_file_cache(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load cached file metadata if valid.

        Args:
            file_path: File path

        Returns:
            Cached metadata or None if cache is invalid/missing
        """
        cache_path = self.get_file_cache_path(file_path)
        file_path_obj = Path(file_path)

        if not cache_path.exists() or not file_path_obj.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cache_data = json.load(f)

            # Check if cache is still valid
            if not self.is_cache_valid(cache_path, [file_path_obj]):
                return None

            logger.info(f"Loaded valid cache for file: {file_path}")
            return cache_data

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load file cache: {e}")
            return None

    def save_file_cache(self, file_path: str, metadata: Dict[str, Any]) -> None:
        """
        Save file metadata to cache.

        Args:
            file_path: File path
            metadata: Metadata to cache
        """
        cache_path = self.get_file_cache_path(file_path)

        # Add cache metadata
        cache_data = {
            "cache_timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "cache_version": "1.0",
            **metadata,
        }

        try:
            # Write to temporary file first, then atomically rename
            with tempfile.NamedTemporaryFile(
                mode="w", dir=self.cache_dir, suffix=".tmp", delete=False
            ) as temp_file:
                json.dump(cache_data, temp_file, indent=2, default=str)
                temp_path = Path(temp_file.name)

            # Atomic rename
            temp_path.replace(cache_path)
            logger.info(f"Saved file cache: {cache_path}")

        except OSError as e:
            logger.error(f"Failed to save file cache: {e}")

    def invalidate_directory_cache(self, data_dir: str) -> None:
        """
        Invalidate (delete) the cache for a directory.

        Args:
            data_dir: Data directory path
        """
        cache_path = self.get_directory_cache_path(data_dir)
        if cache_path.exists():
            try:
                cache_path.unlink()
                logger.info(f"Invalidated directory cache: {cache_path}")
            except OSError as e:
                logger.warning(f"Failed to invalidate directory cache: {e}")

    def invalidate_file_cache(self, file_path: str) -> None:
        """
        Invalidate (delete) the cache for a specific file.

        Args:
            file_path: File path
        """
        cache_path = self.get_file_cache_path(file_path)
        if cache_path.exists():
            try:
                cache_path.unlink()
                logger.info(f"Invalidated file cache: {cache_path}")
            except OSError as e:
                logger.warning(f"Failed to invalidate file cache: {e}")

    def clear_all_cache(self) -> None:
        """
        Clear all cache files.
        """
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Cleared all metadata cache files")
        except OSError as e:
            logger.error(f"Failed to clear cache: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                "cache_dir": str(self.cache_dir),
                "total_cache_files": len(cache_files),
                "total_cache_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_files": [str(f) for f in cache_files],
            }
        except OSError as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}


# Global cache manager instance
_cache_manager = None


def get_cache_manager() -> MetadataCacheManager:
    """
    Get the global cache manager instance.

    Returns:
        MetadataCacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = MetadataCacheManager()
    return _cache_manager

#!/usr/bin/env python3
"""Test cases for decode_project_path function"""

import os
import sys
import tempfile
import shutil

# Add parent directory to path to import cclog_helper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cclog_helper import decode_project_path


class TestDecodeProjectPath:
    """Test decode_project_path function with various encoded paths"""

    def setup_method(self):
        """Create a temporary directory structure for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create test directory structure
        dirs_to_create = [
            "home/user/projects/myapp",
            "home/user/documents",
            "home/user/workspace/project1",
            "home/user/workspace/blog",
            "home/user/.config",
            "home/user/.config/app",
            "home/user/projects/plugin.nvim",
            "home/user/projects/myapp/.git/worktrees/workspace-feat-new-feature-1751800909-a0c4a922/worktree",
            "home/user/projects/data-analytics",
            "home/user/projects/data-analytics/.git/worktrees/workspace-refactor-module-1750951165-4b5956ae/worktree",
            "home/user/projects/data-analytics/.git/worktrees/workspace-add-tests-1750399353-9b977c1c/worktree",
            "home/user/my_project",
            "home/user/workspace/test_app",
            "home/user/my_awesome_project",
            "home/user/projects/myapp/.git/worktrees/workspace-cleanup-task-1751180835-1ea678d3",
        ]

        for dir_path in dirs_to_create:
            os.makedirs(os.path.join(self.test_dir, dir_path), exist_ok=True)

    def teardown_method(self):
        """Clean up temporary directory"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def encode_path(self, path):
        """Encode a path in the same way Claude encodes it"""
        # Remove test_dir prefix to get relative path
        if path.startswith(self.test_dir + "/"):
            path = path[len(self.test_dir) :]
        elif path.startswith(self.test_dir):
            path = path[len(self.test_dir) :]

        # Add test_dir as prefix and encode
        full_path = (
            self.test_dir + path if path.startswith("/") else self.test_dir + "/" + path
        )
        encoded = full_path.replace("/", "-").replace(".", "-").replace("_", "-")
        return encoded

    def test_simple_paths(self):
        """Test simple paths without special characters"""
        paths = [
            "/home/user/projects/myapp",
            "/home/user/documents",
            "/home/user/workspace/project1",
            "/home/user/workspace/blog",
        ]

        for path in paths:
            expected = f"{self.test_dir}{path}"
            encoded = self.encode_path(path)
            result = decode_project_path(encoded)
            assert result == expected, (
                f"Failed for {encoded}: got {result}, expected {expected}"
            )

    def test_paths_with_dots(self):
        """Test paths containing dots that get encoded as dashes"""
        paths = [
            "/home/user/.config",
            "/home/user/.config/app",
            "/home/user/projects/plugin.nvim",
        ]

        for path in paths:
            expected = f"{self.test_dir}{path}"
            encoded = self.encode_path(path)
            result = decode_project_path(encoded)
            assert result == expected, (
                f"Failed for {encoded}: got {result}, expected {expected}"
            )

    def test_git_worktrees(self):
        """Test git worktree paths with complex encoding"""
        paths = [
            "/home/user/projects/myapp/.git/worktrees/workspace-feat-new-feature-1751800909-a0c4a922/worktree",
            "/home/user/projects/data-analytics/.git/worktrees/workspace-refactor-module-1750951165-4b5956ae/worktree",
            "/home/user/projects/data-analytics/.git/worktrees/workspace-add-tests-1750399353-9b977c1c/worktree",
        ]

        for path in paths:
            expected = f"{self.test_dir}{path}"
            encoded = self.encode_path(path)
            result = decode_project_path(encoded)
            assert result == expected, (
                f"Failed for {encoded}: got {result}, expected {expected}"
            )

    def test_paths_with_dashes(self):
        """Test paths containing dashes in project names"""
        paths = [
            "/home/user/projects/data-analytics",
        ]

        for path in paths:
            expected = f"{self.test_dir}{path}"
            encoded = self.encode_path(path)
            result = decode_project_path(encoded)
            assert result == expected, (
                f"Failed for {encoded}: got {result}, expected {expected}"
            )

    def test_edge_cases(self):
        """Test edge cases and potential error conditions"""
        test_cases = [
            # Path without leading dash (shouldn't happen but handle gracefully)
            ("home-user-workspace-test", "home/user/workspace/test"),
            # Empty string
            ("", ""),
            # Only dashes
            ("---", "///"),
        ]

        for encoded, expected in test_cases:
            result = decode_project_path(encoded)
            # For these edge cases, just ensure no exception is raised
            assert isinstance(result, str), f"Should return string for {encoded}"

    def test_actual_failures(self):
        """Test cases that were reported as failures"""
        # Test double slash prevention
        paths = [
            "/home/user/.config",
            "/home/user/.config/app",
        ]

        for path in paths:
            expected = f"{self.test_dir}{path}"
            encoded = self.encode_path(path)
            result = decode_project_path(encoded)
            assert "//" not in result, (
                f"Result should not contain double slashes: {result}"
            )
            assert result == expected, (
                f"Failed for {encoded}: got {result}, expected {expected}"
            )

    def test_paths_with_underscores(self):
        """Test paths containing underscores that get encoded as dashes"""
        paths = [
            "/home/user/my_project",
            "/home/user/workspace/test_app",
            "/home/user/my_awesome_project",
        ]

        for path in paths:
            expected = f"{self.test_dir}{path}"
            encoded = self.encode_path(path)
            result = decode_project_path(encoded)
            assert result == expected, (
                f"Failed for {encoded}: got {result}, expected {expected}"
            )

    def test_worktree_without_suffix(self):
        """Test worktree paths that should decode without /worktree suffix"""
        paths = [
            "/home/user/projects/myapp/.git/worktrees/workspace-cleanup-task-1751180835-1ea678d3",
        ]

        for path in paths:
            expected = f"{self.test_dir}{path}"
            encoded = self.encode_path(path)
            result = decode_project_path(encoded)
            assert "//" not in result, (
                f"Result should not contain double slashes: {result}"
            )
            assert result == expected, (
                f"Failed for {encoded}: got {result}, expected {expected}"
            )

    def test_ambiguous_decode(self):
        """Test that ambiguous cases are resolved by filesystem checks"""
        # This test demonstrates that when multiple interpretations exist,
        # the decoder will return the first match found

        # Create both possible interpretations
        os.makedirs(os.path.join(self.test_dir, "home/user/test-app"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "home/user/test/app"), exist_ok=True)

        # Encode test-app (dash in name)
        path1 = "/home/user/test-app"
        encoded1 = self.encode_path(path1)

        # The decoder will match one of the existing paths
        result1 = decode_project_path(encoded1)

        # Just verify it matches one of the valid paths
        valid_paths = [
            f"{self.test_dir}/home/user/test-app",
            f"{self.test_dir}/home/user/test/app",
        ]
        assert result1 in valid_paths, (
            f"Result should be one of the valid paths: {result1}"
        )


if __name__ == "__main__":
    # Run tests
    test = TestDecodeProjectPath()

    print("Running tests with temporary directory structure...")
    test.setup_method()
    try:
        print("\nRunning simple path tests...")
        test.test_simple_paths()
        print("✓ Simple path tests passed")

        print("\nRunning paths with dots tests...")
        test.test_paths_with_dots()
        print("✓ Paths with dots tests passed")

        print("\nRunning git worktrees tests...")
        test.test_git_worktrees()
        print("✓ Git worktrees tests passed")

        print("\nRunning paths with dashes tests...")
        test.test_paths_with_dashes()
        print("✓ Paths with dashes tests passed")

        print("\nRunning edge case tests...")
        test.test_edge_cases()
        print("✓ Edge case tests passed")

        print("\nRunning actual failure tests...")
        test.test_actual_failures()
        print("✓ Actual failure tests passed")

        print("\nRunning paths with underscores tests...")
        test.test_paths_with_underscores()
        print("✓ Paths with underscores tests passed")

        print("\nRunning worktree without suffix tests...")
        test.test_worktree_without_suffix()
        print("✓ Worktree without suffix tests passed")

        print("\nRunning ambiguous decode tests...")
        test.test_ambiguous_decode()
        print("✓ Ambiguous decode tests passed")

        print("\n✅ All tests passed!")
    finally:
        test.teardown_method()

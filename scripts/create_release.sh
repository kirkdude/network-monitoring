#!/bin/bash
# Release Management Script for LDS Notification Tools
# Creates semantic versioned releases with Git tags and source archives

set -e -o pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RELEASES_DIR="$PROJECT_ROOT/releases"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
# shellcheck disable=SC2034
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${CYAN}$1${NC}"
}

log_success() {
    echo -e "${GREEN}$1${NC}"
}

log_warning() {
    echo -e "${YELLOW}$1${NC}" >&2
}

log_error() {
    echo -e "${RED}$1${NC}" >&2
}

# Show usage
show_usage() {
    cat << EOF
Release Management Script for LDS Notification Tools

Usage: $0 [OPTIONS] VERSION

Create a semantic versioned release with Git tags and source archives.

VERSION:
  Semantic version in format X.Y.Z (e.g., 1.2.3)
  - X: Major version (breaking changes)
  - Y: Minor version (new features, backward compatible)
  - Z: Patch version (bug fixes, backward compatible)

Options:
  --dry-run           Show what would be done without making changes
  --force             Force creation even if tag exists
  --no-archive        Skip creating source archives
  --push              Push tags to remote repository
  -h, --help          Show this help

Examples:
  $0 1.2.3                    # Create release v1.2.3
  $0 --dry-run 1.2.3          # Preview release creation
  $0 --push 1.2.3             # Create and push to remote
  $0 --force 1.2.3            # Force create even if tag exists

Prerequisites:
  - Clean working directory (no uncommitted changes)
  - Git repository with at least one commit
  - Valid semantic version number

EOF
}

# Validate semantic version format
validate_version() {
    local version="$1"

    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid version format: $version"
        log_error "Expected format: X.Y.Z (e.g., 1.2.3)"
        return 1
    fi

    return 0
}

# Check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a Git repository"
        return 1
    fi
    return 0
}

# Check if working directory is clean
check_clean_working_dir() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Skipping working directory check"
        return 0
    fi

    if ! git diff-index --quiet HEAD --; then
        log_error "Working directory is not clean"
        log_error "Please commit or stash your changes before creating a release"
        log_info "Uncommitted changes:"
        git status --porcelain | sed 's/^/  /'
        return 1
    fi

    return 0
}

# Check if tag already exists
check_tag_exists() {
    local tag="$1"

    if git rev-parse "$tag" >/dev/null 2>&1; then
        if [[ "$FORCE" == "true" ]]; then
            log_warning "Tag $tag already exists but --force specified"
            return 0
        else
            log_error "Tag $tag already exists"
            log_error "Use --force to overwrite or choose a different version"
            return 1
        fi
    fi

    return 0
}

# Get current version from Git
get_current_version() {
    local current_tag
    current_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")

    if [[ "$current_tag" == "none" ]]; then
        echo "No previous releases"
    else
        echo "$current_tag"
    fi
}

# Compare versions to ensure we're moving forward
validate_version_progression() {
    local new_version="$1"
    local current_tag

    current_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

    if [[ -z "$current_tag" ]]; then
        log_info "This will be the first release"
        return 0
    fi

    # Remove 'v' prefix if present for comparison
    local current_version="${current_tag#v}"

    # Check if versions are the same
    if [[ "$new_version" == "$current_version" ]]; then
        if [[ "$FORCE" != "true" ]]; then
            log_error "Version $new_version is the same as current version $current_tag"
            return 1
        else
            log_warning "Version $new_version is the same as current version $current_tag. Proceeding due to --force."
        fi
    else
        # Perform semantic version comparison to prevent downgrades
        if ! compare_semantic_versions "$new_version" "$current_version"; then
            if [[ "$FORCE" != "true" ]]; then
                log_error "New version v$new_version is not greater than current version $current_tag."
                log_error "Use --force to proceed if this is intentional."
                return 1
            else
                log_warning "New version v$new_version is not greater than current version $current_tag. Proceeding due to --force."
            fi
        fi
    fi

    log_info "Upgrading from $current_tag to v$new_version"
    return 0
}

# Compare two semantic versions
# Returns 0 if version1 > version2, 1 otherwise
compare_semantic_versions() {
    local version1="$1"
    local version2="$2"

    # Split versions into components
    IFS='.' read -r v1_major v1_minor v1_patch <<< "$version1"
    IFS='.' read -r v2_major v2_minor v2_patch <<< "$version2"

    # Default to 0 if components are missing
    v1_major=${v1_major:-0}; v1_minor=${v1_minor:-0}; v1_patch=${v1_patch:-0}
    v2_major=${v2_major:-0}; v2_minor=${v2_minor:-0}; v2_patch=${v2_patch:-0}

    # Compare major version
    if ((v1_major > v2_major)); then
        return 0
    elif ((v1_major < v2_major)); then
        return 1
    fi

    # Major versions are equal, compare minor version
    if ((v1_minor > v2_minor)); then
        return 0
    elif ((v1_minor < v2_minor)); then
        return 1
    fi

    # Major and minor versions are equal, compare patch version
    if ((v1_patch > v2_patch)); then
        return 0
    else
        return 1
    fi
}

# Create the Git tag
create_git_tag() {
    local version="$1"
    local tag="v$version"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would create tag: $tag"
        return 0
    fi

    log_info "Creating Git tag: $tag"

    # Create annotated tag with release information
    local tag_message
    tag_message="Release $tag

Automated release created by create_release.sh

Release Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Git Commit: $(git rev-parse HEAD)
"

    if [[ "$FORCE" == "true" ]] && git rev-parse "$tag" >/dev/null 2>&1; then
        log_warning "Deleting existing tag: $tag"
        git tag -d "$tag"
    fi

    if git tag -a "$tag" -m "$tag_message"; then
        log_success "✓ Created tag: $tag"
    else
        log_error "Failed to create tag: $tag"
        return 1
    fi

    return 0
}

# Create source archives
create_source_archives() {
    local version="$1"
    local archive_prefix="$2"
    local tar_file="$3"
    local zip_file="$4"
    local tag="v$version"

    if [[ "$NO_ARCHIVE" == "true" ]]; then
        log_info "Skipping archive creation (--no-archive specified)"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would create archives in $RELEASES_DIR/"
        log_info "  - $(basename "$tar_file")"
        log_info "  - $(basename "$zip_file")"
        return 0
    fi

    log_info "Creating source archives..."

    # Create releases directory
    mkdir -p "$RELEASES_DIR"

    # Create tar.gz archive
    log_info "Creating $tar_file"
    if git archive --format=tar.gz --prefix="${archive_prefix}/" "$tag" > "$tar_file"; then
        log_success "✓ Created: $tar_file"
    else
        log_error "Failed to create tar.gz archive"
        return 1
    fi

    # Create zip archive
    log_info "Creating $zip_file"
    if git archive --format=zip --prefix="${archive_prefix}/" "$tag" > "$zip_file"; then
        log_success "✓ Created: $zip_file"
    else
        log_error "Failed to create zip archive"
        return 1
    fi

    # Show archive sizes
    log_info "Archive sizes:"
    # shellcheck disable=SC2012
    ls -lh "$tar_file" "$zip_file" | awk '{print "  " $5 " " $9}' | sed "s|$RELEASES_DIR/||g"

    return 0
}

# Push tags to remote
push_to_remote() {
    local version="$1"
    local tag="v$version"

    if [[ "$PUSH" != "true" ]]; then
        log_info "To push this release to remote repository:"
        log_info "  git push origin $tag"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would push tag to remote: $tag"
        return 0
    fi

    log_info "Pushing tag to remote repository..."

    if git push origin "$tag"; then
        log_success "✓ Pushed tag to remote: $tag"
    else
        log_error "Failed to push tag to remote"
        log_warning "Tag was created locally but not pushed"
        return 1
    fi

    return 0
}

# Show release summary
show_release_summary() {
    local version="$1"
    local tar_file="$2"
    local zip_file="$3"
    local tag="v$version"

    echo
    log_success "=== Release Summary ==="
    echo
    log_info "Version: $version"
    log_info "Git Tag: $tag"
    log_info "Commit: $(git rev-parse HEAD)"

    if [[ "$NO_ARCHIVE" != "true" && "$DRY_RUN" != "true" ]]; then
        echo
        log_info "Release Archives:"
        if [[ -f "$tar_file" ]]; then
            echo "  ✓ $tar_file"
        fi
        if [[ -f "$zip_file" ]]; then
            echo "  ✓ $zip_file"
        fi
    fi

    echo
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "This was a dry run - no changes were made"
        echo
        log_info "To create the release for real:"
        log_info "  $0 $version"
    else
        log_success "Release v$version created successfully!"
        echo
        if [[ "$PUSH" != "true" ]]; then
            log_info "Next steps:"
            log_info "  1. Push the tag: git push origin $tag"
            log_info "  2. Create GitHub release (optional)"
            log_info "  3. Update documentation (if needed)"
        fi
    fi
}

# Parse command line arguments
parse_arguments() {
    DRY_RUN="false"
    FORCE="false"
    NO_ARCHIVE="false"
    PUSH="false"
    VERSION=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --force)
                FORCE="true"
                shift
                ;;
            --no-archive)
                NO_ARCHIVE="true"
                shift
                ;;
            --push)
                PUSH="true"
                shift
                ;;
            -*)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                if [[ -z "$VERSION" ]]; then
                    VERSION="$1"
                else
                    log_error "Multiple versions specified: $VERSION and $1"
                    exit 1
                fi
                shift
                ;;
        esac
    done

    if [[ -z "$VERSION" ]]; then
        log_error "Version is required"
        show_usage
        exit 1
    fi
}

# Main execution
main() {
    log_info "=== LDS Notification Tools Release Creator ==="
    echo

    # Validate inputs
    validate_version "$VERSION" || exit 1
    check_git_repo || exit 1
    check_clean_working_dir || exit 1
    check_tag_exists "v$VERSION" || exit 1
    validate_version_progression "$VERSION" || exit 1

    # Show current state
    local current_version
    current_version=$(get_current_version)
    log_info "Current version: $current_version"
    log_info "New version: v$VERSION"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - No changes will be made"
    fi

    echo

    # Define archive paths once
    local archive_prefix="network-monitoring-v$VERSION"
    local tar_file="$RELEASES_DIR/${archive_prefix}.tar.gz"
    local zip_file="$RELEASES_DIR/${archive_prefix}.zip"

    # Create the release
    create_git_tag "$VERSION" || exit 1
    create_source_archives "$VERSION" "$archive_prefix" "$tar_file" "$zip_file" || exit 1
    push_to_remote "$VERSION" || exit 1

    # Show summary
    show_release_summary "$VERSION" "$tar_file" "$zip_file"
}

# Parse arguments and run
parse_arguments "$@"
main

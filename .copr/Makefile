# Universal Copr SRPM builder for FreeUnit.
#
# Snapshot builds:
#   make -f .copr/Makefile srpm outdir=./out spec=unit.spec
#
# Release builds:
#   make -f .copr/Makefile srpm \
#     UPSTREAM_REF=refs/tags/1.35.3 \
#     RELEASE=1 \
#     outdir=./out \
#     spec=unit.spec
#
# Prerelease builds:
#   make -f .copr/Makefile srpm \
#     UPSTREAM_REF=refs/tags/1.36.0-rc1 \
#     RELEASE=0.rc1 \
#     outdir=./out \
#     spec=unit.spec
#
# Default behavior:
#   - UPSTREAM_REF=master
#   - VERSION is read from upstream version file
#   - RELEASE auto-generated for snapshots:
#       0.<UTC timestamp>.git<short sha>

UPSTREAM_REPO ?= https://github.com/freeunitorg/freeunit.git
UPSTREAM_REF ?= master

BUILD_DIR ?= _build
WORKTREE := $(BUILD_DIR)/freeunit

SNAPSHOT_STAMP := $(shell date -u +%Y%m%d%H%M)

srpm:
	rm -rf "$(BUILD_DIR)"
	mkdir -p "$(BUILD_DIR)"
	git clone --depth=1 --branch "$(UPSTREAM_REF)" "$(UPSTREAM_REPO)" "$(WORKTREE)"

	VERSION="$$(. "$(WORKTREE)/version" && echo $$NXT_VERSION)"; \
	SHA="$$(git -C "$(WORKTREE)" rev-parse --short HEAD)"; \
	if echo "$(UPSTREAM_REF)" | grep -q '^refs/tags/'; then \
		RELEASE="$${RELEASE:-1}"; \
	else \
		RELEASE="$${RELEASE:-0.$(SNAPSHOT_STAMP).git$$SHA}"; \
	fi; \
	$(MAKE) -C "$(WORKTREE)/pkg/rpm" \
		VERSION="$$VERSION" \
		RELEASE="$$RELEASE" \
		specs

	mkdir -p "$(outdir)"
	cp "$(WORKTREE)"/pkg/rpm/rpmbuild/SPECS/unit.spec .
	cp "$(WORKTREE)"/pkg/rpm/rpmbuild/SOURCES/unit-*.tar.gz .

	rpmbuild -bs \
		--define "_sourcedir $(PWD)" \
		--define "_specdir $(PWD)" \
		--define "_srcrpmdir $(outdir)" \
		unit.spec

clean:
	rm -rf "$(BUILD_DIR)" unit.spec unit-*.tar.gz


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

UPSTREAM_GIT_REF := $(patsubst refs/tags/%,%,$(patsubst refs/heads/%,%,$(UPSTREAM_REF)))

TOPDIR := $(CURDIR)
BUILD_DIR := $(TOPDIR)/_build
WORKTREE := $(BUILD_DIR)/freeunit
UPSTREAM_RPMSOURCES := $(WORKTREE)/pkg/rpm/rpmbuild/SOURCES

SNAPSHOT_STAMP := $(shell date -u +%Y%m%d%H%M)

srpm:
	rm -rf "$(BUILD_DIR)"
	mkdir -p "$(BUILD_DIR)"

	dnf -y install git libxml2 libxslt
	git clone --depth 1 --branch "$(UPSTREAM_GIT_REF)" "$(UPSTREAM_REPO)" "$(WORKTREE)"

	VERSION="$$(. "$(WORKTREE)/version" && echo $$NXT_VERSION)"; \
	if echo "$(UPSTREAM_REF)" | grep -q '^refs/tags/'; then \
		RELEASE="$${RELEASE:-1}"; \
	else \
		RELEASE="$${RELEASE:-0.$(SNAPSHOT_STAMP)}"; \
	fi; \
	$(MAKE) -C "$(WORKTREE)/pkg/rpm" \
		VERSION="$$VERSION" \
		RELEASE="$$RELEASE" \
		specs \
		"rpmbuild/SOURCES/unit-$$VERSION.tar.gz"

	mkdir -p "$(outdir)"

	cp "$(WORKTREE)"/pkg/rpm/rpmbuild/SPECS/unit.spec "$(TOPDIR)/unit.spec"

	rpmbuild -bs \
		--define "_sourcedir $(UPSTREAM_RPMSOURCES)" \
		--define "_specdir $(TOPDIR)" \
		--define "_srcrpmdir $(outdir)" \
		"$(TOPDIR)/unit.spec"

clean:
	rm -rf "$(BUILD_DIR)" "$(TOPDIR)/unit.spec" "$(TOPDIR)/unit-*.tar.gz"

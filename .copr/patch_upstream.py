#!/usr/bin/env python3
"""Patch freeunit for COPR: no curl in pkg/contrib; SRPM generates contrib-fetch.sh from Makefiles."""
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve()

CURL_PKG_MARK = "missing contrib tarball"
CURL_ANCH_START = "ifeq ($(shell curl --version >/dev/null 2>&1 || echo FAIL),)"
XZ_BLOCK_START = "\nifeq ($(shell which xz >/dev/null 2>&1 || echo FAIL),)"

CURL_PATCH_MARKER = "# COPR: HTTP fetch moved out of makefile (generated contrib-fetch.sh at SRPM via gen_contrib_fetch.py)"

# Replaces anchors [CURL_ANCH_START .. XZ_BLOCK_START) with commented curl/wget + stub download_pkg.
CURL_AND_PKG_NEW = """# COPR: HTTP fetch moved out of makefile (generated contrib-fetch.sh at SRPM via gen_contrib_fetch.py)
# ifeq ($(shell curl --version >/dev/null 2>&1 || echo FAIL),)
# download = curl -f -L -- "$(1)" > "$@"
# else ifeq ($(shell wget --version >/dev/null 2>&1 || echo FAIL),)
# download = (rm -f $@.tmp && \\
#  wget --passive -c -p -O $@.tmp "$(1)" && \\
#  touch $@.tmp && \\
#  mv $@.tmp $@ )
# else ifeq ($(which fetch >/dev/null 2>&1 || echo FAIL),)
# download = (rm -f $@.tmp && \\
#  fetch -p -o $@.tmp "$(1)" && \\
#  touch $@.tmp && \\
#  mv $@.tmp $@)
# else
# download = $(error Neither curl nor wget found)
# endif
#
# download_pkg = $(call download,$(CONTRIB_FREEUNIT)/$(2)/$(lastword $(subst /, ,$(@)))) || \\
#  ( $(call download,$(1)) && echo "Please upload $(lastword $(subst /, ,$(@))) to $(CONTRIB_FREEUNIT)" )

download_pkg = @test -s '$@' || { printf >&2 '%s\\n' 'missing contrib tarball (run SRPM contrib-fetch step / gen_contrib_fetch.py): $@'; exit 1; }

"""

SKIP_BLOCK = (
    "\n"
    "# Offline mock (Fedora COPR rpm builds disable outbound network by default).\n"
    "# Contrib archives ship under pkg/contrib/tarballs/ (SRPM contrib-fetch.sh).\n"
    "ifneq ($(SKIP_CONTRIB_NET),)\n"
    "download_git = @test -s '$@' || "
    "{ printf >&2 '%s\\n' 'SKIP_CONTRIB_NET: missing bundled contrib file: $@'; exit 1; }\n"
    "endif\n\n"
)

NEEDLE = "include $(SRC)/*/Makefile\n\n# Targets\n"

WASI_SKIP_MARKER = "# COPR: wasi-sysroot disabled"

# unit.spec.in — libunit-wasm needs wasi-sysroot; disable both until WASI tarball/SUMS align.
SPEC_LIBUNIT_WASM_BUILD = """%if (0%{?fedora}) || (0%{?rhel} >= 8) || (0%{?amzn2})
%{__make} %{?_smp_mflags} -C pkg/contrib .libunit-wasm
%endif"""

SPEC_LIBUNIT_WASM_BUILD_DISABLED = """# COPR: libunit-wasm disabled (needs wasi-sysroot)
# %if (0%{?fedora}) || (0%{?rhel} >= 8) || (0%{?amzn2})
# %{__make} %{?_smp_mflags} -C pkg/contrib .libunit-wasm
# %endif"""

SPEC_LIBUNIT_WASM_INSTALL = """%if (0%{?fedora}) || (0%{?rhel} >= 8) || (0%{?amzn2})
%{__mkdir} -p %{buildroot}%{_includedir}/unit/
%{__install} -m 644 pkg/contrib/libunit-wasm/src/c/libunit-wasm.a %{buildroot}%{_libdir}/
%{__install} -m 644 pkg/contrib/libunit-wasm/src/c/include/unit/unit-wasm.h %{buildroot}%{_includedir}/unit/
%endif"""

SPEC_LIBUNIT_WASM_INSTALL_DISABLED = """# COPR: libunit-wasm install disabled (needs wasi-sysroot)
# %if (0%{?fedora}) || (0%{?rhel} >= 8) || (0%{?amzn2})
# %{__mkdir} -p %{buildroot}%{_includedir}/unit/
# %{__install} -m 644 pkg/contrib/libunit-wasm/src/c/libunit-wasm.a %{buildroot}%{_libdir}/
# %{__install} -m 644 pkg/contrib/libunit-wasm/src/c/include/unit/unit-wasm.h %{buildroot}%{_includedir}/unit/
# %endif"""

RUST_OTEL_MARKER = "# COPR: rust for configure --otel"
RUST_BUILD_REQUIRES = """BuildRequires: rust
BuildRequires: cargo"""


def _find_active(haystack: str, needle: str) -> int:
    """Index of needle on a Makefile line whose first non-whitespace char is not '#'."""
    pos = 0
    while pos < len(haystack):
        i = haystack.find(needle, pos)
        if i == -1:
            return -1
        bol = haystack.rfind("\n", 0, i) + 1
        eol = haystack.find("\n", i)
        line = haystack[bol:] if eol == -1 else haystack[bol:eol]
        stripped = line.lstrip()
        if stripped.startswith("#"):
            pos = i + len(needle)
            continue
        return i
    return -1


def patch_contrib_makefile(cm: Path) -> None:
    txt = cm.read_text(encoding="utf-8")

    xz_at = txt.find(XZ_BLOCK_START)
    if xz_at == -1:
        sys.exit(f"{cm}: anchor before xz toolchain block not found")

    patched_curl = CURL_PATCH_MARKER in txt[:xz_at] and CURL_PKG_MARK in txt[:xz_at]

    curl_at = _find_active(txt, CURL_ANCH_START)

    if not patched_curl:
        if curl_at == -1 or curl_at >= xz_at:
            sys.exit(f"{cm}: curl download block anchor not found (upstream changed?)")
        txt = txt[:curl_at] + CURL_AND_PKG_NEW + txt[xz_at:]
        if txt.find(XZ_BLOCK_START) == -1:
            sys.exit(f"{cm}: xz toolchain block disappeared after patching (upstream changed?)")
    else:
        if curl_at != -1 and curl_at < txt.find(XZ_BLOCK_START):
            sys.exit(
                f"{cm}: inconsistent contrib Makefile: patched stub markers but curl block remains"
            )

    if "ifneq ($(SKIP_CONTRIB_NET),)" in txt and "SKIP_CONTRIB_NET: missing bundled" in txt:
        cm.write_text(txt, encoding="utf-8")
        return
    if NEEDLE not in txt:
        sys.exit(f"{cm}: expected marker before # Targets")
    txt = txt.replace(
        NEEDLE,
        "include $(SRC)/*/Makefile\n" + SKIP_BLOCK + "# Targets\n",
        1,
    )
    cm.write_text(txt, encoding="utf-8")


def _comment_pkgs_line(mf: Path, pkg_line: str, reason: str) -> None:
    txt = mf.read_text(encoding="utf-8")
    if WASI_SKIP_MARKER in txt:
        return
    if pkg_line not in txt:
        sys.exit(f"{mf}: expected {pkg_line!r}")
    block = f"{WASI_SKIP_MARKER} ({reason})\n# {pkg_line}\n"
    mf.write_text(txt.replace(pkg_line + "\n", block, 1), encoding="utf-8")


def patch_disable_wasi_contrib(worktree: Path) -> None:
    _comment_pkgs_line(
        worktree / "pkg/contrib/src/wasi-sysroot/Makefile",
        "PKGS += wasi-sysroot",
        "SHA512 mismatch on upstream tarball",
    )
    _comment_pkgs_line(
        worktree / "pkg/contrib/src/libunit-wasm/Makefile",
        "PKGS += libunit-wasm",
        "depends on wasi-sysroot",
    )


def patch_spec(si: Path) -> None:
    txt = si.read_text(encoding="utf-8")
    needle = "%{__make} %{?_smp_mflags} -C pkg/contrib .njs"
    guard = "export SKIP_CONTRIB_NET=1\n"
    if guard not in txt:
        pair = "%build\n" + needle
        if pair not in txt:
            sys.exit(f"{si}: missing %%build / contrib .njs block")
        ins = (
            "%build\n# Bundled contrib tarballs under %%{SOURCE0}; mock has no network.\n"
            + guard
            + "\n"
            + needle
        )
        txt = txt.replace(pair, ins, 1)

    if SPEC_LIBUNIT_WASM_BUILD in txt:
        txt = txt.replace(SPEC_LIBUNIT_WASM_BUILD, SPEC_LIBUNIT_WASM_BUILD_DISABLED, 1)
    if SPEC_LIBUNIT_WASM_INSTALL in txt:
        txt = txt.replace(SPEC_LIBUNIT_WASM_INSTALL, SPEC_LIBUNIT_WASM_INSTALL_DISABLED, 1)

    if RUST_OTEL_MARKER not in txt:
        anchor = "BuildRequires: llvm\n"
        if anchor not in txt:
            sys.exit(f"{si}: expected {anchor!r} for rust BuildRequires")
        txt = txt.replace(
            anchor,
            anchor + RUST_OTEL_MARKER + "\n" + RUST_BUILD_REQUIRES + "\n",
            1,
        )

    si.write_text(txt, encoding="utf-8")


def main() -> None:
    contrib = ROOT / "pkg/contrib/Makefile"
    spec = ROOT / "pkg/rpm/unit.spec.in"
    for p in (contrib, spec):
        if not p.is_file():
            sys.exit(f"missing: {p}")
    patch_contrib_makefile(contrib)
    patch_disable_wasi_contrib(ROOT)
    patch_spec(spec)


if __name__ == "__main__":
    main()

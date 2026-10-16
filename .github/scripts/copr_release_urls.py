#!/usr/bin/env python3
"""Report the URL of every published quads-client RPM of a release.

Copr serves the project's results from its Pulp backend, which hides the RPMs
from the download index, so the URLs are read from the repository metadata
instead: the Copr API locates the newest succeeded build of the release
version, and the version-release of that build selects the RPMs to report
from the metadata of every chroot the project builds.

Modes:
  urls <version>  print the absolute URL of every quads-client and
                  quads-client-gui RPM of the version's newest succeeded
                  build, one per line, exit 1 while the build is not
                  published
  --self-test     run the offline metadata parsing checks

Exit status: 0 on success, 1 when nothing is published for the version, 2 when
the repository or the Copr API cannot be read or a lookup fails for any other
reason, 3 when a build of the version exists but did not succeed.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import urllib.error
import urllib.request

PACKAGE = "quads-client"
RPM_NAMES = ("quads-client", "quads-client-gui")
OWNER = "quadsdev"
COPR_PROJECT = "python3-quads"
PROJECT = f"https://download.copr.fedorainfracloud.org/results/{OWNER}/{COPR_PROJECT}"
API = "https://copr.fedorainfracloud.org/api_3"
TIMEOUT = 60
BUILD_LIMIT = 200
EXIT_MISSING = 1
EXIT_UNREADABLE = 2
EXIT_FAILED = 3
# Build states that never produce a published RPM.
DEAD_STATES = ("canceled", "failed", "skipped")

# The locations are written into the release notes as markdown, so only plain
# paths to RPM files are accepted.
LOCATION = re.compile(r"[A-Za-z0-9._+/-]+\.(?:src\.)?rpm")

REPOMD = b'<repomd><data type="primary">' b'<location href="repodata/abc-primary.xml.gz"/></data></repomd>'
PRIMARY = (
    b"<metadata>"
    b'<package type="rpm">'
    b"<name>quads-client</name><arch>noarch</arch>"
    b'<version epoch="0" ver="0.10.0" rel="20261012"/>'
    b'<location href="11113567-quads-client/quads-client-0.10.0-20261012.noarch.rpm"/>'
    b"</package>"
    b'<package type="rpm">'
    b"<name>quads-client</name><arch>src</arch>"
    b'<version epoch="0" ver="0.10.0" rel="20261012"/>'
    b'<location href="11113567-quads-client/quads-client-0.10.0-20261012.src.rpm"/>'
    b"</package>"
    b'<package type="rpm">'
    b"<name>quads-client-gui</name><arch>noarch</arch>"
    b'<version epoch="0" ver="0.10.0" rel="20261012"/>'
    b'<location href="11113567-quads-client/quads-client-gui-0.10.0-20261012.noarch.rpm"/>'
    b"</package>"
    b'<package type="rpm">'
    b"<name>quads-client</name><arch>noarch</arch>"
    b'<version epoch="0" ver="0.9.0" rel="20261008"/>'
    b'<location href="11094413-quads-client/quads-client-0.9.0-20261008.noarch.rpm"/>'
    b"</package>"
    b'<package type="rpm">'
    b"<name>quads</name><arch>noarch</arch>"
    b'<version epoch="0" ver="3.0.2" rel="20261012"/>'
    b'<location href="11111888-quads/quads-3.0.2-20261012.noarch.rpm"/>'
    b"</package>"
    b"</metadata>"
)


class UndeterminedError(RuntimeError):
    """Raised when the answer cannot be determined."""


class BuildFailedError(RuntimeError):
    """Raised when a build of the version exists but can never publish."""


def fetch(url: str, headers: dict[str, str] | None = None) -> bytes:
    """Return the body of url, following redirects, bypassing shared caches."""
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", **(headers or {})})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return bytes(response.read())


def primary_href(repomd: bytes) -> str:
    """Return the relative path of the primary metadata file in repomd.xml."""
    match = re.search(rb'<location href="(repodata/[^"]*primary\.xml\.gz)"', repomd)
    if match is None:
        raise UndeterminedError("no primary metadata declared in repomd.xml")
    return match.group(1).decode()


def packages(primary: bytes) -> list[tuple[str, str, str]]:
    """Return (NVR, arch, location) for the RPMs in primary metadata."""
    packages: list[tuple[str, str, str]] = []
    for package in re.findall(rb'<package type="rpm">(.*?)</package>', primary, re.S):
        arch = re.search(rb"<arch>([^<]+)</arch>", package)
        name = re.search(rb"<name>([^<]+)</name>", package)
        version = re.search(rb'<version epoch="[^"]*" ver="([^"]+)" rel="([^"]+)"/>', package)
        location = re.search(rb'<location href="([^"]+)"/>', package)
        if not (arch and name and version and location):
            raise UndeterminedError("unexpected package entry in the repository metadata")
        path = location.group(1).decode()
        if not LOCATION.fullmatch(path):
            raise UndeterminedError(f"unexpected package location: {path!r}")
        nvr = b"-".join((name.group(1), version.group(1), version.group(2)))
        packages.append((nvr.decode(), arch.group(1).decode(), path))
    return packages


def fetch_primary(chroot: str) -> bytes:
    """Return the primary metadata of one chroot's repository."""
    base = f"{PROJECT}/{chroot}"
    href = primary_href(fetch(f"{base}/repodata/repomd.xml"))
    return gzip.decompress(fetch(f"{base}/{href}"))


def artifact_locations(primary: bytes, version_release: str) -> list[str]:
    """Return the binary RPM locations of the wanted packages of one version-release."""
    # shortcut: the release is matched as built, without a dist tag; a spec
    # that adds %{?dist} releases per chroot and needs per-chroot matching.
    return sorted(
        location
        for nvr, arch, location in packages(primary)
        if arch != "src" and nvr.removesuffix(f"-{version_release}") in RPM_NAMES
    )


def build_version_release(version: str) -> str:
    """Return the version-release of the newest succeeded build, empty when none.

    source_package.version carries the version and the release of the build,
    for example 0.10.0-20261012, because the spec releases by build date. The
    list is newest first, so a build of a new version is never hidden by the
    page limit. A build of the version that can never publish raises instead,
    so waiting for it does not waste the window.
    """
    url = (
        f"{API}/build/list?ownername={OWNER}&projectname={COPR_PROJECT}"
        f"&packagename={PACKAGE}&order=id&order_type=DESC&offset=0&limit={BUILD_LIMIT}"
    )
    items = json.loads(fetch(url))["items"]
    dead = ""
    for build in items:
        source = build.get("source_package", {})
        version_release = str(source.get("version", ""))
        if source.get("name") != PACKAGE or not version_release.startswith(f"{version}-"):
            continue
        if build.get("state") == "succeeded":
            return version_release
        if not dead and build.get("state") in DEAD_STATES:
            dead = f"{version_release} {build['state']}"
    if dead:
        raise BuildFailedError(f"the Copr build of {dead}")
    return ""


def chroots() -> list[str]:
    """Return the Fedora chroots the project builds, warning about the rest."""
    url = f"{API}/project?ownername={OWNER}&projectname={COPR_PROJECT}"
    built = json.loads(fetch(url)).get("chroot_repos", {})
    match = re.compile(r"fedora-(?:rawhide|\d+)-x86_64")
    chosen = sorted(chroot for chroot in built if match.fullmatch(chroot))
    for skipped in sorted(set(built) - set(chosen)):
        print(f"warning: {skipped} is not linked", file=sys.stderr)
    return chosen


def file_exists(url: str) -> bool:
    """Return whether the artifact at url can be fetched; 404 means no file."""
    try:
        fetch(url, {"Range": "bytes=0-0"})
    except urllib.error.HTTPError as error:
        if error.code in (404, 410):
            return False
        raise
    return True


def urls(version: str) -> list[str]:
    """Return the fetchable artifacts of the version in every project chroot."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise UndeterminedError(f"not a release version: {version!r}")
    version_release = build_version_release(version)
    if not version_release:
        print(f"no succeeded build of {PACKAGE} {version} yet", file=sys.stderr)
        return []
    project_chroots = chroots()
    if not project_chroots:
        raise UndeterminedError("the project reports no Fedora chroot")
    found: list[str] = []
    for chroot in project_chroots:
        chroot_urls = [
            url
            for url in (
                f"{PROJECT}/{chroot}/{location}"
                for location in artifact_locations(fetch_primary(chroot), version_release)
            )
            if file_exists(url)
        ]
        if not chroot_urls:
            print(f"no published artifact for {version_release} in {chroot}", file=sys.stderr)
            return []
        found.extend(chroot_urls)
    return sorted(found)


def self_test() -> int:
    """Check the metadata parsing and version matching without network access."""
    assert primary_href(REPOMD) == "repodata/abc-primary.xml.gz"
    assert packages(PRIMARY) == [
        (
            "quads-client-0.10.0-20261012",
            "noarch",
            "11113567-quads-client/quads-client-0.10.0-20261012.noarch.rpm",
        ),
        (
            "quads-client-0.10.0-20261012",
            "src",
            "11113567-quads-client/quads-client-0.10.0-20261012.src.rpm",
        ),
        (
            "quads-client-gui-0.10.0-20261012",
            "noarch",
            "11113567-quads-client/quads-client-gui-0.10.0-20261012.noarch.rpm",
        ),
        (
            "quads-client-0.9.0-20261008",
            "noarch",
            "11094413-quads-client/quads-client-0.9.0-20261008.noarch.rpm",
        ),
        (
            "quads-3.0.2-20261012",
            "noarch",
            "11111888-quads/quads-3.0.2-20261012.noarch.rpm",
        ),
    ]
    assert artifact_locations(PRIMARY, "0.10.0-20261012") == [
        "11113567-quads-client/quads-client-0.10.0-20261012.noarch.rpm",
        "11113567-quads-client/quads-client-gui-0.10.0-20261012.noarch.rpm",
    ]
    assert artifact_locations(PRIMARY, "0.11.0-20261016") == []
    assert artifact_locations(PRIMARY, "3.0.2-20261012") == []
    for bad in (
        "11094413-quads-client/quads-client`-0.9.0.noarch.rpm",
        "11094413-quads-client/a b.rpm",
        "11094413-quads-client/quads-client-0.9.0-20261008.txt",
    ):
        assert not LOCATION.fullmatch(bad)
        rejected = PRIMARY.replace(b"11094413-quads-client/quads-client-0.9.0-20261008.noarch.rpm", bad.encode())
        try:
            packages(rejected)
        except UndeterminedError:
            continue
        raise AssertionError(f"a foreign location must be rejected: {bad}")
    # build_version_release() is checked with the Copr API mocked: the newest
    # succeeded build of the version wins even when the list is truncated, a
    # newer build that is still running is ignored, and a longer version is no
    # match.
    builds = {
        "items": [
            {"state": "succeeded", "source_package": {"name": PACKAGE, "version": "0.10.0-20261012"}},
            {"state": "running", "source_package": {"name": PACKAGE, "version": "0.10.0-20261016"}},
            {"state": "succeeded", "source_package": {"name": PACKAGE, "version": "10.10.0-20261016"}},
            {"state": "succeeded", "source_package": {"name": "quads", "version": "0.10.0-20261016"}},
        ]
        + [
            {"state": "succeeded", "source_package": {"name": PACKAGE, "version": "0.9.9-1"}}
            for _ in range(BUILD_LIMIT)
        ]
    }

    def api_fetch(url: str, headers: dict[str, str] | None = None) -> bytes:
        return json.dumps(builds).encode()

    global fetch
    original = fetch
    try:
        fetch = api_fetch
        assert build_version_release("0.10.0") == "0.10.0-20261012"
        builds["items"] = [{"state": "running", "source_package": {"name": PACKAGE, "version": "0.10.0-20261016"}}]
        assert build_version_release("0.11.0") == ""
        builds["items"] = [{"state": "failed", "source_package": {"name": PACKAGE, "version": "0.10.0-20261016"}}]
        try:
            build_version_release("0.10.0")
        except BuildFailedError:
            pass
        else:
            raise AssertionError("a build of the version that cannot publish must raise")
        builds["items"] = [
            {"state": "running", "source_package": {"name": PACKAGE, "version": "0.10.0-20261016"}}
        ] * BUILD_LIMIT
        assert build_version_release("0.11.0") == ""
    finally:
        fetch = original
    print("copr_release_urls self-test ok")
    return 0


def dispatch(argv: list[str]) -> int:
    """Run the requested mode."""
    if argv[1:2] == ["urls"] and len(argv) == 3:
        found = urls(argv[2])
        if not found:
            return EXIT_MISSING
        print("\n".join(found))
        return 0
    print(__doc__, file=sys.stderr)
    return EXIT_UNREADABLE


def main(argv: list[str]) -> int:
    """Dispatch the mode, reporting any failed lookup on one line.

    The self-test runs outside the catch-all, so a broken assertion reaches
    the log as a traceback. Anything that stops a lookup from being
    determined maps to EXIT_UNREADABLE: a request failure, metadata that does
    not parse, or an unexpected error. EXIT_MISSING is reserved for an answer
    that was determined.
    """
    if argv[1:2] == ["--self-test"]:
        return self_test()
    try:
        return dispatch(argv)
    except BuildFailedError as error:
        print(f"copr_release_urls: {error}", file=sys.stderr)
        return EXIT_FAILED
    except Exception as error:  # noqa: BLE001 - every failure is "undetermined"
        print(f"copr_release_urls: {type(error).__name__}: {error}", file=sys.stderr)
        return EXIT_UNREADABLE


if __name__ == "__main__":
    sys.exit(main(sys.argv))

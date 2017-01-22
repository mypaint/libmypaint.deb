#!/usr/bin/python
# Build source+changes uploads for the Ubuntu PPA, for all supported
# Ubuntu releases.

import os
import sys
import subprocess
import time
import shutil
import logging
import re
import tempfile


SUPPORTED_UBUNTU_SERIES = (
    "trusty",
    "vivid",
    "xenial",
    "yakkety",
)
TAILORED_VERSION_TMPL = ("{upstream_version}-{deb_revision_base}"
                         "ppa1~{ubuntu_series}1")

CHANGELOG_FIRST_LINE_RE = re.compile(
    r'''
        ^ (?P<package>libmypaint)
        \s* \(
        \s* (?P<upstream_version>.+)      # e.g. 1.1.1~alpha
        - (?P<deb_revision_base>0dev\d+)  # e.g. 0dev3
        \s* \)
        \s* UNRELEASED \s* ;              # distribution field
        \s* urgency \s* =
        \s* (?P<urgency>.*)               # e.g. urgency=low
    ''',
    re.VERBOSE,
)


logger = logging.getLogger(os.path.basename(sys.argv[0]))


def parse_newest_changelog_entry():
    # Extract information about the newest debian/changelog entry
    fp = open("debian/changelog", "r")
    line = fp.readline()
    fp.close()
    m = re.match(CHANGELOG_FIRST_LINE_RE, line)
    assert m is not None, \
        "Cannot parse 1st line of debian/changelog"
    info = m.groupdict()
    logger.info("Parsed %r from newest changlog entry", info)
    return info


def unpack_pristine_tarball(tmpdir, tarball_basename, package_name):
    # Unpack a pristine tarball into tmpdir, and rename it sensibly
    tarball_path = os.path.join(tmpdir, tarball_basename)
    subprocess.check_call(["tar", "-xp", "-C", tmpdir, "-f", tarball_path])
    unpacked_source_path = os.path.join(tmpdir, package_name)
    for entry_basename in os.listdir(tmpdir):
        entry_path = os.path.join(tmpdir, entry_basename)
        if os.path.isdir(entry_path):
            assert entry_basename.startswith(entry_basename)
            if entry_basename != package_name:
                os.rename(entry_path, unpacked_source_path)
            break
    assert os.path.isdir(unpacked_source_path)
    return unpacked_source_path


def copy_pristine_tarball(rel_tarball_path, tmpdir, newest_change_info):
    # Copy an existing pristine tarball.
    # The name must be as generated
    # by "make dist", e.g. mypaint-1.2.0-beta.0.tar.xz, and will
    # be renamed to, e.g. mypaint_1.2.0~beta.0.orig.tar.gz
    # to keep the debian tools happy.
    rel_tarball_bn = os.path.basename(rel_tarball_path)
    upstream_version = newest_change_info["upstream_version"]
    rel_tarball_bn_pfx = "{package}-{upstream_version}".format(
        package = newest_change_info["package"],
        upstream_version = upstream_version.replace("~", "-"),
    )
    deb_tarball_bn_pfx = "{package}_{upstream_version}".format(
        **newest_change_info
    )
    assert rel_tarball_bn_pfx != deb_tarball_bn_pfx
    rel_tarball_bn_sfx = ".tar.xz"
    deb_tarball_bn_sfx = ".orig.tar.xz"
    assert rel_tarball_bn_sfx != deb_tarball_bn_sfx
    assert rel_tarball_bn.startswith(rel_tarball_bn_pfx)
    assert rel_tarball_bn.endswith(rel_tarball_bn_sfx)
    deb_tarball_bn = (
        rel_tarball_bn
        .replace(rel_tarball_bn_pfx, deb_tarball_bn_pfx, 1)
        .replace(rel_tarball_bn_sfx, deb_tarball_bn_sfx, 1)
    )
    assert deb_tarball_bn != rel_tarball_bn
    deb_tarball_path = os.path.join(tmpdir, deb_tarball_bn)
    logger.info("Copying %r to %r...", rel_tarball_path, deb_tarball_path)
    shutil.copy(rel_tarball_path, deb_tarball_path)
    return deb_tarball_bn, upstream_version


def tailor_debian_changelog(unpack_root, formal_version, ubuntu_series,
                            newest_change_info):
    # Rewrite debian/changelog so that it contains the formal version
    # of the release tarball we made, and so that uploads are uniquely
    # named for each Ubuntu series being built.
    changelog_path = os.path.join(unpack_root, "debian", "changelog")
    changelog_orig_path = os.path.join(unpack_root, "debian", "changelog.orig")

    logger.info(
        "Tailoring base debian/changelog for %r and %r",
        formal_version,
        ubuntu_series,
    )
    upstream_version = formal_version
    upstream_version = upstream_version.replace("-", "~")
    os.rename(changelog_path, changelog_orig_path)
    changelog_src_fp = open(changelog_orig_path, "r")
    changelog_targ_fp = open(changelog_path, "w")
    for i, line in enumerate(changelog_src_fp):
        if i == 0:
            params = newest_change_info.copy()
            params["upstream_version"] = upstream_version
            params["ubuntu_series"] = ubuntu_series
            tailored_version = TAILORED_VERSION_TMPL.format(**params)
            params["tailored_version"] = tailored_version
            tmpl = ("{package} ({tailored_version}) "
                    "{ubuntu_series}; urgency={urgency}")
            line = tmpl.format(**params)
        print >>changelog_targ_fp, line,
    changelog_src_fp.close()
    changelog_targ_fp.close()


def build_ppa_source_uploads(tmpdir, tarball_filename):
    logger.info("Building source uploads...")

    newest_change_info = parse_newest_changelog_entry()

    tarball_basename, upstream_version = copy_pristine_tarball(
        tarball_filename,
        tmpdir,
        newest_change_info,
    )

    orig_cwd = os.getcwd()
    package_name = newest_change_info["package"]
    for ubuntu_series in SUPPORTED_UBUNTU_SERIES:
        logger.info("Starting build for %r", ubuntu_series)
        # Unpack it, fiddle the path, and clone this debian/ tree into it
        unpacked_source_path = unpack_pristine_tarball(
            tmpdir, tarball_basename, package_name,
        )
        # Graft this debian tree there too
        os.chdir("debian")
        try:
            subprocess.check_call(["git", "diff", "--quiet"])
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "You have local changes in debian/. "
                "Stage them first with 'git add'"
            )
        graft_prefix = os.path.join(unpacked_source_path, "debian") + "/"
        subprocess.check_call([
            "git", "checkout-index",
            "-a", "-f",
            "--prefix=%s" % (graft_prefix,),
        ])
        os.chdir(orig_cwd)

        logger.info("Building %r for %r...", upstream_version, ubuntu_series)

        tailor_debian_changelog(
            unpacked_source_path,
            upstream_version,
            ubuntu_series,
            newest_change_info,
        )

        logger.info("Building package")
        os.chdir(unpacked_source_path)
        subprocess.check_call(["debuild", "-S", "-sa"]) ##, "-us", "-uc"])
        shutil.rmtree(unpacked_source_path, ignore_errors=True)
        os.chdir(orig_cwd)

    logger.info("Source uploads prepared for all series!")


def _main():
    tarball_filename = sys.argv[1]
    if not (os.path.isdir("debian") and os.path.isdir(".git")):
        logger.error(
            "This script must be run from within a "
            "MyPaint git checkout."
        )
        sys.exit(1)
    tmpdir = tempfile.mkdtemp(prefix="build-ppa-uploads.")
    logger.info("Using tmpdir %r", tmpdir)
    try:
        build_ppa_source_uploads(tmpdir, tarball_filename)
    except:
        logger.exception("Unhandled exception")
        logger.info("Cleaning up tmpdir %r", tmpdir)
        shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        output_path = "ppa-uploads-%s" % (time.strftime("%Y%m%dT%H%M%S"),)
        logger.info("Success! Moving build output tree to %r", output_path)
        shutil.move(tmpdir, output_path)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    _main()


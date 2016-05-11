## libmypaint.deb

This is an EXPERIMENTAL Debianization of the (equally experimental)
autotools port of libmypaint that the MyPaint team is currently
developing. Right now, it only builds from git and not from a release
tarball. It is maintained in a separate module to give you the option of
making your own.

To use it, check out the relevant branch of libmypaint, then drop this
repository into it under the name `debian`:

    git clone https://github.com/mypaint/libmypaint.git
    cd libmypaint
    git checkout autotools-port
    git clone https://github.com/mypaint/libmypaint.deb.git debian

The usual Debian-style build trickery will then work, and spit out
packages into `../*.deb`, assuming the dependencies are correct.

    fakeroot debian/rules binary

If the autotools port looks solid, this repository will likely form the
basis for future PPA builds of libmypaint.

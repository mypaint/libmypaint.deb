## libmypaint.deb

This our Debianization of libmypaint as an indepdendent package.
Right now, it only builds from git and not from a release tarball.
It is maintained in a separate module to give you the option of making your own.

To use it, check out the relevant branch of libmypaint, then drop this
repository into it under the name `debian`:

    git clone https://github.com/mypaint/libmypaint.git
    cd libmypaint
    git clone https://github.com/mypaint/libmypaint.deb.git debian

The usual Debian-style build trickery should then work if you have the right dependencies:

    fakeroot debian/rules binary

This repository will likely form the basis for future PPA builds of libmypaint.

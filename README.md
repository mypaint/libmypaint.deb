## libmypaint.deb

This our Debianization of libmypaint as an indepdendent package.
It is maintained in a separate module to give you the option of making your own.

To use it, check out the relevant branch of libmypaint, then drop this
repository into it under the name `debian`:

    git clone https://github.com/mypaint/libmypaint.git
    cd libmypaint
    git clone https://github.com/mypaint/libmypaint.deb.git debian

The usual Debian-style build trickery should then work if you have the right dependencies:

    fakeroot debian/rules binary

This repository is the basis for our [PPA builds of libmypaint](https://launchpad.net/~achadwick/+archive/ubuntu/mypaint-testing).

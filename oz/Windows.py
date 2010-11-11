# Copyright (C) 2010  Chris Lalancette <clalance@redhat.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import Guest
import random
import subprocess
import re
import os
import ozutil

class Windows2000andXPand2003(Guest.CDGuest):
    def __init__(self, idl, config):
        update = idl.update()
        arch = idl.arch()

        if update == "2000" and arch != "i386":
            raise Exception, "Windows 2000 only supports i386 architecture"
        self.key = idl.key()
        if self.key is None:
            raise Exception, "A key is required when installing Windows 2000, XP, or 2003"
        self.siffile = ozutil.generate_full_auto_path("windows-" + update + "-jeos.sif")

        self.url = ozutil.check_url(idl.iso())
        if idl.installtype() != 'iso':
            raise Exception, "Windows installs must be done via iso"

        Guest.CDGuest.__init__(self, "Windows", update, arch, None,
                               "localtime", "usb", None, config)

    def generate_new_iso(self):
        self.log.debug("Generating new ISO")
        Guest.subprocess_check_output(["mkisofs", "-b", "cdboot/boot.bin",
                                       "-no-emul-boot", "-boot-load-seg",
                                       "1984", "-boot-load-size", "4",
                                       "-iso-level", "2", "-J", "-l", "-D",
                                       "-N", "-joliet-long",
                                       "-relaxed-filenames", "-v", "-v",
                                       "-V", "Custom",
                                       "-o", self.output_iso, self.iso_contents])

    def modify_iso(self):
        os.mkdir(self.iso_contents + "/cdboot")
        self.geteltorito(self.orig_iso, self.iso_contents + "/cdboot/boot.bin")

        if self.arch == "i386":
            winarch = self.arch
        elif self.arch == "x86_64":
            winarch = "amd64"
        else:
            raise Exception, "Unexpected architecture " + self.arch

        computername = "OZ" + str(random.randrange(1, 900000))

        f = open(self.siffile, "r")
        lines = f.readlines()
        f.close()

        for line in lines:
            if re.match(" *ProductKey", line):
                lines[lines.index(line)] = "    ProductKey=" + self.key + "\n"
            elif re.match(" *ProductID", line):
                lines[lines.index(line)] = "    ProductID=" + self.key + "\n"
            elif re.match(" *ComputerName", line):
                lines[lines.index(line)] = "    ComputerName=" + computername + "\n"

        # FIXME: with windows 2000 Server, there doesn't seem to be an
        # i386 directory that we can stuff winnt.sif into.  Either we should
        # create that directory, or find another way to make that work
        f = open(self.iso_contents + "/" + winarch + "/winnt.sif", "w")
        f.writelines(lines)
        f.close()

    def generate_install_media(self, force_download):
        self.get_original_iso(self.url, force_download)
        self.copy_iso()
        self.modify_iso()
        self.generate_new_iso()
        self.cleanup_iso()

    def install(self):
        self.log.info("Running install for %s" % (self.name))
        self.generate_define_xml("cdrom")
        self.libvirt_dom.create()
        self.wait_for_install_finish(1000)
        self.generate_define_xml("hd")
        self.libvirt_dom.create()
        self.wait_for_install_finish(3600)
        self.generate_define_xml("hd", want_install_disk=False)

class Windows2008(Guest.CDGuest):
    def __init__(self, idl, config):
        update = idl.update()
        arch = idl.arch()
        self.siffile = ozutil.generate_full_auto_path("windows-" + update + "-jeos.sif")

        self.url = ozutil.check_url(idl.iso())

        if idl.installtype() != 'iso':
            raise Exception, "Windows installs must be done via iso"

        Guest.CDGuest.__init__(self, "Windows", update, arch, None,
                               "localtime", "usb", None, config)

    def generate_new_iso(self):
        self.log.debug("Generating new ISO")
        # NOTE: Windows 2008 is very picky about which arguments to mkisofs
        # will generate a bootable CD, so modify these at your own risk
        Guest.subprocess_check_output(["mkisofs", "-b", "cdboot/boot.bin",
                                       "-no-emul-boot", "-c", "BOOT.CAT",
                                       "-iso-level", "2", "-J", "-l", "-D",
                                       "-N", "-joliet-long",
                                       "-relaxed-filenames", "-v", "-v",
                                       "-V", "Custom", "-udf",
                                       "-o", self.output_iso, self.iso_contents])

    def modify_iso(self):
        os.mkdir(self.iso_contents + "/cdboot")
        self.geteltorito(self.orig_iso, self.iso_contents + "/cdboot/boot.bin")

        if self.arch == "i386":
            winarch = self.arch
        elif self.arch == "x86_64":
            winarch = "amd64"
        else:
            raise Exception, "Unexpected architecture " + self.arch

    def generate_install_media(self, force_download):
        self.get_original_iso(self.url, force_download)
        self.copy_iso()
        self.modify_iso()
        self.generate_new_iso()
        self.cleanup_iso()

    def install(self):
        self.log.info("Running install for %s" % (self.name))
        self.generate_define_xml("cdrom")
        self.libvirt_dom.create()
        self.wait_for_install_finish(1000)
        self.generate_define_xml("hd")
        self.libvirt_dom.create()
        self.wait_for_install_finish(3600)
        self.generate_define_xml("hd", want_install_disk=False)

def get_class(idl, config):
    update = idl.update()
    if update == "2000" or update == "XP" or update == "2003":
        return Windows2000andXPand2003(idl, config)
    if update == "2008":
        return Windows2008(idl, config)
    raise Exception, "Unsupported Windows update " + update
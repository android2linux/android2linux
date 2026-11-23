# Cameras on a mainline Qualcomm kernel

How to find out why a phone's cameras don't work under a mainline kernel, which of them can, and how to try a fix without risking the boot. The example is the Redmi Note 9 Pro Max (`excalibur`, SM7125) on postmarketOS, whose macro camera works this way; [its page](../../../../phones/xiaomi-excalibur/#cameras-on-postmarketos) has the files.

## Contents

- [How it fits together](#how-it-fits-together)
- [What the phone has now](#what-the-phone-has-now)
- [Which sensors the phone really has](#which-sensors-the-phone-really-has)
- [Which variant a unit has](#which-variant-a-unit-has)
- [The usual causes](#the-usual-causes)
- [A sensor with no mainline driver](#a-sensor-with-no-mainline-driver)
- [Build on the phone](#build-on-the-phone)
- [Boot it from a second entry](#boot-it-from-a-second-entry)
- [Count, don't trust one boot](#count-dont-trust-one-boot)
- [Take a picture](#take-a-picture)
- [Check the frames](#check-the-frames)
- [Last verified](#last-verified)

## How it fits together

- **CAMSS** (`qcom-camss`) is the SoC's camera block: it receives the sensor's data over MIPI CSI-2 (through the **CSIPHY**s) and writes frames to memory.
- **CCI** (`i2c-qcom-cci`) is the I2C controller the sensors are configured over. Each sensor sits on a CCI bus at an address.
- **A sensor driver** per sensor model (`drivers/media/i2c/`), told by the **device tree** where the sensor is: its bus and address, its clock (MCLK), its power rails, its reset GPIO and which CSIPHY its lanes go to.
- **libcamera** turns the raw sensor frames into pictures in user space (its "simple" pipeline with a software ISP on these phones); apps use it directly or through PipeWire.

CAMSS registers its media device (`/dev/media0`) only when **every sensor its device tree links to has bound**. One sensor that never binds, because it's the wrong chip, unpowered or without a driver, hides every camera, including ones that would work.

## What the phone has now

```sh
ls /dev/media* /dev/v4l-subdev* /dev/video*
sudo dmesg | grep -iE 'camss|cci|<sensor names>'
tr '\0' ' ' < /proc/device-tree/model; echo
tr '\0' ' ' < /proc/device-tree/compatible; echo
lsmod | grep -iE 'camss|cci'
zcat /proc/config.gz | grep -E 'CAMSS|CCI'    # or the package's config in /boot
```

- `/dev/video*` alone means little (the video codec has some); **no `/dev/media0`** means CAMSS never finished.
- A sensor's probe failing with `Cannot read register …` and error -5 (EIO), or a `master N queue M timeout` from CCI, means nothing answered at that address: the wrong chip, or the right chip unpowered or unclocked.
- The **model** and **compatible** say which device tree the kernel booted. An unsupported variant often boots its sibling's, and then the tree describes the sibling's cameras.
- To see the sensor nodes the booted tree has: `ls /proc/device-tree/soc@0/cci@*/i2c-bus@*/`.

## Which sensors the phone really has

Spec sheets give megapixels, rarely sensor models. Better sources, most reliable first:

1. **Android's own kernel source** for the phone (the vendor's GPL release, or LineageOS' kernel tree): its camera device tree names each sensor's CCI device and master, slave address, MCLK and rate, regulators and reset GPIO. Xiaomi's miatoll tree, for example, puts excalibur's cameras in `curtana-atoll-camera-sensor-idp.dtsi`.
2. **LineageOS' proprietary-files list** for the phone: the camera module blobs are named after the sensors (`sunny_ov32a1q`, `ofilm_s5kgw1`), often with which variant they come from.
3. **Device-spec pages** that list sensor models (devicespecifications.com, reviews).

Some phones ship different sensors in different units (excalibur's ultrawide is an OV8856 or a GC8034). Only the sensor's chip ID, read over CCI once it's powered, tells which one yours has.

Then check each model for a driver: mainline `drivers/media/i2c/` (its Kconfig), the phone family's kernel fork, and the linux-media list. With no mainline driver, look in other vendors' kernels ([below](#a-sensor-with-no-mainline-driver)) before writing one.

## Which variant a unit has

When a camera ships with two sensors, they usually sit at different addresses on the same bus: excalibur's ultrawide is an OV8856 at `0x36` or a GC8034 at `0x37`. An existing driver can tell which one answers before you have the other's driver:

1. Add a node for the sensor that has a driver, wired as the vendor's tree says (bus, clock, reset, rails, CSIPHY), and boot it once.
2. `Cannot read …`, `failed to find sensor: -5` (EIO) or `-110` means nothing answered at that address (or it's unpowered).
3. Move the node to the other address. A **wrong chip ID** (`chip id mismatch: 885a!=0`, `-6`) means a chip answered there, just not the one the driver expects. Each vendor reads its ID from different registers, so the value it reads is meaningless; that something answered is the answer.

## The usual causes

- **A sibling's sensor in the device tree.** The tree describes a chip the phone doesn't have; its probe fails and blocks CAMSS. Disable that sensor node **and the CAMSS endpoint that links to it** (`status = "disabled"` on the endpoint; `camss_of_parse_ports` skips unavailable endpoints).
- **The right sensor, wrongly powered or clocked.** Compare the node with the vendor's: the MCLK rate (excalibur's macro wants 24 MHz, the mainline node had 19.2) and every rail (a second analog supply on another GPIO, for another production batch of the same module). A fixed regulator with `regulator-always-on` is enough for a first test.
- **A sensor that sometimes doesn't answer at boot.** If a re-probe later works (`echo <bus>-<addr> > /sys/bus/i2c/drivers/<driver>/bind`), the first read failed on a CCI controller that only resets when it suspends and resumes (about a second idle): a retry in the driver's probe that waits that long finds the sensor. Give the sensor node the camera block's power domain (`power-domains = <&camcc TITAN_TOP_GDSC>` on SC7180-class SoCs), or a second try fails with `Failed to enable xvclk` (-16).
- **The CSIPHY programming.** Frames need the PHY's lane settings for that SoC; on SM7125 the mainline table is wrong and a community fix replaces it ([asidko/qcom-camss-mainline](https://github.com/asidko/qcom-camss-mainline)).

## A sensor with no mainline driver

Many sensors with no mainline driver have one in an SoC vendor's kernel: Rockchip's [rockchip-linux/kernel](https://github.com/rockchip-linux/kernel) (`drivers/media/i2c/`) has dozens, GalaxyCore and SmartSens among them, under the GPL. They are ordinary V4L2 subdevice drivers with the register tables a sensor needs to start, so porting one is mostly removing what is Rockchip's own:

- **Remove** `rkmodule` ioctls and module info, `rk-camera-module.h`, OTP calibration through Rockchip's `otp_eeprom`, and `rockchip,camera_*` pinctrl states.
- **Change** for the current kernel: `probe(struct i2c_client *)`, `remove` returning `void`, `v4l2_subdev_state_get_format` for try formats, `DEFINE_RUNTIME_DEV_PM_OPS`, `v4l2_link_freq_to_bitmap` against the tree's `link-frequencies`, and `v4l2_ctrl_new_fwnode_properties` so libcamera gets the rotation and the mounting position.
- **Keep** the vendor's tables for your lane count and input clock (they usually assume 24 MHz: run the clock at that, `assigned-clock-rates`), the exposure and gain programming, and the power sequence.

The vendor's driver often carries several table sets; they aren't all equally tested. Excalibur's [ported GC8034](../../../../phones/xiaomi-excalibur/camera/gc8034/) streamed with Rockchip's 30 fps two-lane set but the frames were wrong ([below](#check-the-frames)); its 15 fps set was right.

A driver built outside the kernel tree needs only a one-line `Makefile` (`obj-m := <name>.o`): `make -C <kernel tree> M=$PWD modules`.

## Build on the phone

Build against the **exact** source and config of the kernel the phone runs, with the same compiler, so the module loads: on postmarketOS the phone itself has it.

1. Find the kernel package's source: its `APKBUILD` in pmaports (`source=`, and any patches it applies). Check its config for `CONFIG_MODVERSIONS` and `CONFIG_MODULE_SIG_FORCE`: without them, a module built from the same source and config loads.
2. On the phone:
   ```sh
   sudo apk add build-base bc flex bison perl openssl-dev elfutils-dev linux-headers diffutils findutils xz tar
   wget <the package's source tarball> && tar xzf <it> && cd <the tree>
   patch -p1 < camss-csiphy-fix.patch
   cp <your-phone>.dts arch/arm64/boot/dts/qcom/        # and add its .dtb to that folder's Makefile
   sudo cat /boot/config > .config && make olddefconfig
   make -j"$(nproc)" modules_prepare
   make qcom/<your-phone>.dtb
   make KBUILD_MODPOST_WARN=1 M=drivers/media/platform/qcom/camss modules
   modinfo drivers/media/platform/qcom/camss/qcom-camss.ko | grep vermagic   # must match `uname -r`'s
   ```
   The `modpost … undefined!` warnings are expected: a single module built outside the full kernel build has no `Module.symvers`; the kernel resolves the symbols when it loads it.

## Boot it from a second entry

Change nothing the phone boots from now; add beside it.

- The module goes in `/lib/modules/$(uname -r)/updates/` (then `sudo depmod`): it wins over the original, and deleting it goes back.
- The tree goes next to the others (`/boot/dtbs/qcom/`), and a **second boot entry** uses it. With systemd-boot (postmarketOS on U-Boot boards): copy `/boot/loader/entries/pmos.conf` to a new file, change its `title` and `sort-key`, and add `devicetree /dtbs/qcom/<your-phone>.dtb`. In `/boot/loader/loader.conf`, `default <new file>` and `timeout 10` make it the default and show the menu, so the old entry can be picked at boot if the new one doesn't start.
- **A tree for one boot.** systemd-boot has a one-shot entry (`bootctl set-oneshot`), but U-Boot's EFI variables don't survive a reboot, so it has no effect there. Instead, set `default` to the test entry, reboot, and set it back as soon as the phone is up. A tree that breaks only the camera still boots, so this is safe for sensor nodes.
- Charge first. A build at full load drains a phone quickly, and one without a charger driver may not start again until it has charged with the screen off ([Charging without a driver](charging-without-a-driver.md)).

## Count, don't trust one boot

A probe that works once may fail on the next boot. Reboot several times and count, from the PC:

```sh
for i in 1 2 3 4 5 6 7 8; do
  ssh <phone> 'sudo systemctl reboot'; sleep 90
  ssh <phone> 'sudo dmesg | grep -E "<sensor>.*(Detected|Cannot|failed)" | head -2'
done
```

## Take a picture

```sh
sudo apk add libcamera-tools
cam -l
cam -c1 --capture=8 --stream role=still --file=/tmp/frame#.ppm
```

`cam -l` lists the cameras libcamera found; a warning that there's no tuning file (`<sensor>.yaml`) or sensor helper means it uses uncalibrated defaults, so the colours are off but the picture is real. The first frames may be dark while exposure settles: keep the last.

## Check the frames

Frames that arrive aren't necessarily right. Capture a raw frame (`cam -c<n> --capture=6 --stream role=raw --file=raw#.bin`) and look at its bytes:

- **Real data fills the frame.** A black band at the bottom (zeros after some line) means less data came than the format says.
- **A sheared or striped picture** means the lines are a different length from what the format says. Find the real length: the offset at which each byte best matches the byte one line further on.

  ```python
  import numpy as np
  d = np.fromfile("raw.bin", dtype=np.uint8).astype(np.int16)[200_000:2_200_000]
  print(sorted((float(np.abs(d[:-L] - d[L:]).mean()), L) for L in range(3000, 8400))[:3])
  ```

  For RAW10 the line should be width × 5/4 bytes (4080 for 3264). Excalibur's GC8034 on Rockchip's 30 fps tables gave 3856, and on the 15 fps tables 4080.
- **Then look at it** in good light, beside a camera that works.

## Last verified

On excalibur, postmarketOS v26.06, `linux-postmarketos-qcom-sm7125` 6.14.7-r0, libcamera 0.7.1: 2026-11-23. The macro (S5K5E9) captures; with the probe retry it was found on eight boots in a row, and a late re-probe catches the rarer misses. The ultrawide (GC8034, with the ported driver) captures at 3264 × 2448 and 15 fps. Chromium uses the camera through PipeWire in a tab, and a GStreamer pipeline (`libcamerasrc`) runs it for a camera app.

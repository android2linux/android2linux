# Device tree

[`sm7125-xiaomi-excalibur.dts`](sm7125-xiaomi-excalibur.dts) is the phone's own device tree: joyeuse's Huaxing tree adapted for excalibur. It includes `sm7125-xiaomi-joyeuse.dtsi`, so the rest comes from the family's tree.

## Changes by area

- **Cameras.** The front sensor and its CAMSS endpoint are disabled, the macro's clock runs at 24 MHz with a second 2.8 V analog rail, and the ultrawide has a `galaxycore,gc8034` node. The camera files (the CSIPHY fix, the sensor driver, the probe retry) are in [`../camera/`](../camera/); [the phone's Cameras section](../README.md#cameras-on-postmarketos) explains them.
- **Charging.** The `&pm6150_typec` block at the end makes the USB-C port dual-role, preferring sink, so a USB-C charger turns its output on. [`../charging/`](../charging/) has the fix; the background is in [Charging on a mainline Qualcomm kernel](../../../skills/android2linux/references/guides/charging-without-a-driver.md).

## Install

Build the tree like any other: `make qcom/sm7125-xiaomi-excalibur.dtb` against the phone's kernel source and config. Put the result at `/boot/dtbs/qcom/sm7125-xiaomi-excalibur.dtb` and give it its own systemd-boot entry, keeping the original entry. The [camera guide](../../../skills/android2linux/references/guides/mainline-camera.md#boot-it-from-a-second-entry) has the steps.

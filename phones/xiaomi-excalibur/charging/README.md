# Charging on excalibur (postmarketOS)

The [charging guide](../../../skills/android2linux/references/guides/charging-without-a-driver.md) explains the causes. This folder lists what excalibur runs.

| Change | Where | Applies to |
|---|---|---|
| The USB-C port dual-role, preferring sink, 5 V | the connector block at the end of [`../devicetree/sm7125-xiaomi-excalibur.dts`](../devicetree/sm7125-xiaomi-excalibur.dts) | every `miatoll` phone: the source-only setting is in `sm7125-xiaomi-common.dtsi`. Tested on excalibur only |
| Suspend instead of power-off at critical battery | `/etc/UPower/UPower.conf` | any postmarketOS phone with a charger that powers it on |
| The power-saver profile | tuned-ppd (tuned's `powersave`) | any phone running tuned-ppd |

## The port

With the stock tree, a USB-C-to-C charger (tested: a Mac USB-C power adapter) never turned on and the battery drained. With the dual-role tree the phone charged at about 0.75 A with the screen on. The effective input limit read 1.4 A, up from 0. There's no charger driver, so there's still no fast charging, and the battery status stays "Unknown".

To test it without changing a working tree, the installed `.dtb` was decompiled, only the connector edited, recompiled and booted from its own entry, `excalibur-charge.conf`, with the original entries kept. The guide has the [commands](../../../skills/android2linux/references/guides/charging-without-a-driver.md#fix-make-the-port-dual-role).

## UPower

The phone boot-looped from a flat battery on its charger. UPower powered it off at 3 %, about 34 s into each boot, and the charger switched it back on. In `/etc/UPower/UPower.conf`, in place of `CriticalPowerAction=PowerOff`:

```ini
AllowRiskyCriticalPowerAction=true
CriticalPowerAction=Suspend
```

UPower 1.91 ignores `AllowRiskyCriticalPowerAction` in `UPower.conf.d`, so this edits the main file. On upgrades `apk` keeps the edited file and writes the package's version beside it as `UPower.conf.apk-new`. To undo it, put `CriticalPowerAction=PowerOff` back, delete the other line and run `sudo systemctl restart upower`.

## Power profile

```sh
sudo busctl set-property org.freedesktop.UPower.PowerProfiles /org/freedesktop/UPower/PowerProfiles \
  org.freedesktop.UPower.PowerProfiles ActiveProfile s power-saver
```

`tuned-adm active` then reports `powersave`. It keeps the `schedutil` governor, turns CPU boost off and adds panel, audio and VM power savings. tuned-ppd keeps the choice across reboots. Set `balanced` to go back.

## Last checked

2026-11-28, postmarketOS v26.06, kernel `6.14.7-sm7125`.

# Charging on a mainline Qualcomm kernel

Why a phone on a mainline kernel charges slowly or not at all, how to tell which of the two causes you have, and what fixes each. The example is the PM6150 PMIC in Snapdragon 720G phones (the `miatoll` family): its USB-C port is set up as a power **source** only, and its charger ("SMB5") has no mainline driver.

## Contents

- [Two separate problems](#two-separate-problems)
- [Is the port a sink?](#is-the-port-a-sink)
- [Fix: make the port dual-role](#fix-make-the-port-dual-role)
- [What the charger does without a driver](#what-the-charger-does-without-a-driver)
- [How to measure charging](#how-to-measure-charging)
- [A flat battery and a boot loop](#a-flat-battery-and-a-boot-loop)
- [Suspend](#suspend)
- [What a real driver would take](#what-a-real-driver-would-take)
- [Last verified](#last-verified)

## Two separate problems

| | What it controls | Symptom when it's wrong |
|---|---|---|
| **The USB-C port's power role** (device tree, Type-C driver `qcom_pmic_tcpm`) | Whether a USB-C charger turns its output on at all | A USB-C-to-C charger does nothing; the battery drains while plugged in |
| **The charger** (PMIC charger block, no mainline driver for SMB5) | How much current goes in, fast charging, charging status | Charging works but slowly; status always "Unknown" |

A USB-C charger keeps its 5 V off until the phone shows itself as a sink on the CC line. A USB-A charger or PC port puts 5 V on the cable regardless. So with a source-only port, only USB-A sources reach the charger. Ubuntu Touch charges properly because Android's kernel runs the port as dual-role and has Qualcomm's `qpnp-smb5` charger driver.

## Is the port a sink?

```sh
cat /sys/class/typec/port0/port_type    # [source] = source only; [dual] source sink = dual-role
cat /sys/class/typec/port0/power_role   # with a charger plugged in, it should read source [sink]
ls /sys/class/typec/                     # port0-partner appears when something is attached
cat /sys/class/power_supply/tcpm-source-psy-*/online   # 1 once a source is attached
sudo cat /sys/kernel/debug/usb/tcpm-*/log             # the Type-C state machine; reading empties it
```

On a source-only port `port_type` reads `[source]`, nothing attaches, and the log stays at `SRC_UNATTACHED` and `Start toggling` from boot. Writing `dual` or `sink` to `port_type` fails: the role comes from the device tree.

The source-only setting is in `sm7125-xiaomi-common.dtsi` in the sm7125-mainline kernel, which every `miatoll` tree includes (curtana, joyeuse, excalibur and gram):

```dts
&pm6150_typec {
	connector {
		compatible = "usb-c-connector";
		power-role = "source";
		data-role = "dual";
		self-powered;
		source-pdos = <PDO_FIXED(5000, 3000, ...)>;
	};
};
```

## Fix: make the port dual-role

Override the connector in your phone's own device tree, preferring sink and asking for 5 V only (with no charger driver nothing could use more):

```dts
&pm6150_typec {
	connector {
		power-role = "dual";
		try-power-role = "sink";
		sink-pdos = <PDO_FIXED(5000, 3000, PDO_FIXED_DUAL_ROLE |
				PDO_FIXED_USB_COMM | PDO_FIXED_DATA_SWAP)>;
		op-sink-microwatt = <10000000>;
	};
};
```

Without a tree of your own, change the one you boot and nothing else. Decompile it, edit the connector, recompile, and check that the round trip differs only there. Use the kernel tree's `scripts/dtc/dtc` or the `dtc` package:

```sh
dtc -q -I dtb -O dts -o orig.dts /boot/dtbs/qcom/<tree>.dtb
# edit the connector in a copy: power-role "dual", and add try-power-role, sink-pdos, op-sink-microwatt.
# In a decompiled tree the PDO is a number: <0x2601912c> is PDO_FIXED(5000, 3000, dual-role | USB comm | data swap)
dtc -q -I dts -O dtb -o <tree>-charge.dtb charge.dts
dtc -q -I dtb -O dts -o check.dts <tree>-charge.dtb && diff orig.dts check.dts   # only the connector lines
```

Boot it from a second systemd-boot entry first, with the original entry kept ([the camera guide](mainline-camera.md#boot-it-from-a-second-entry) has the steps). With a USB-C charger plugged in, the checks above should then read `power_role: source [sink]`, `port0-partner` present, `online` 1, and the supply `5000000` µV, `3000000` µA.

Seen on excalibur with a Mac USB-C power adapter: the log shows two `HARD_RESET`s while waiting for Power Delivery capabilities, then `SNK_READY` on Type-C current (3.0 A advertised). No PD contract is made, which doesn't matter at 5 V. USB networking to a PC wasn't tested on the dual-role tree.

## What the charger does without a driver

With no driver the charger runs on its power-on defaults. It still charges, with no fast charging and no status: the battery's `status` reads "Unknown" all the time.

The PMIC's registers are readable through debugfs: `sudo cat /sys/kernel/debug/regmap/0-00/registers` for the PM6150 (SPMI SID 0). Writing them needs a rebuilt kernel. The SMB5 registers that matter:

| Register | What | Seen on excalibur |
|---|---|---|
| `0x1366` `USBIN_ICL_OPTIONS` | bit 0 `USBIN_MODE_CHG` (high-current mode), bit 1 `USB51_MODE` (500 mA rather than 100 mA) | `0x02`: USB 500 mA mode |
| `0x1370` `USBIN_CURRENT_LIMIT_CFG` | input current limit, 50 mA steps | `0x1c` = 1.4 A |
| `0x1108` | the input limit actually in force (after AICL) | `0x00` with the port source-only, on a USB-C charger and on a PC port; `0x1c` = 1.4 A with the port dual-role on a USB-C charger |
| `0x1061` `FAST_CHARGE_CURRENT_CFG` | charge current, 50 mA steps | `0x3c` = 3 A |
| `0x1006` `BATTERY_CHARGER_STATUS_1` | low 3 bits: the charger's state | `0x47` source-only, `0x03` dual-role and charging |

What that gives:

| Setup | Result |
|---|---|
| USB-C charger, port **source-only** | Nothing: the charger never turns on; the battery drains |
| USB-C charger, port **dual-role**, screen on | About 0.75 A into the battery (excalibur, Mac adapter), voltage climbing steadily |
| USB-A wall charger, screen off | Charges, slowly: 75 % → 83 % in 30 minutes on excalibur |
| PC USB port | About break-even; the battery still supplies part of the load |

## How to measure charging

The battery gauge (`qcom_qg`) reads capacity and voltage, but its current reading is unreliable and its status is always "Unknown". UPower then shows "discharging" even while the phone charges. Measure by **capacity and voltage over time**:

- Note capacity (%) and voltage (mV), wait a known interval, note them again.
- A rising voltage alongside rising capacity is real charging.
- Use `current_now` mainly for its **sign**: positive means drawn from the battery, negative means charging. Its magnitude can be far off.
- The capacity can jump across a reboot (28 % → 46 % on excalibur): the gauge re-estimates at boot. Compare within one boot.

```sh
q=/sys/class/power_supply/qcom_qg
while sleep 10; do echo "$(date +%T) $(cat $q/capacity)% $(cat $q/voltage_now) $(cat $q/current_now)"; done
```

## A flat battery and a boot loop

With the battery nearly empty and a charger attached, the phone can loop. UPower's `CriticalPowerAction=PowerOff` fires at `PercentageAction` (3 %), about 30 s after each boot. The charger then powers the phone straight back on, and a phone that keeps booting gains almost nothing. In the journal it looks like a run of one-minute boots, each ending with `poweroff requested from client … ('upowerd')`. Check with `journalctl --list-boots`.

Suspend instead of powering off, so the phone charges while it sleeps. UPower calls `Suspend` risky and needs `AllowRiskyCriticalPowerAction=true`, and UPower 1.91 reads that key only from the main `/etc/UPower/UPower.conf`, not from `UPower.conf.d`. In `UPower.conf`:

```ini
AllowRiskyCriticalPowerAction=true
CriticalPowerAction=Suspend
```

Restart `upower` and check its log: it should say `Use AllowRiskyCriticalPowerAction=false to disable support for risky settings`. If it says `The system will perform "HybridSleep" instead`, the key wasn't read, and with no hibernation HybridSleep falls back to powering off. Off the charger, a phone suspended this way sleeps until the battery cuts out.

## Suspend

Suspend is **`s2idle`** only. It works: the phone sleeps and resumes, with a kernel warning logged on resume (benign). A suspended phone with the screen off is the best case for charging on the defaults. A session other than Phosh may never suspend at all: check `cat /sys/power/suspend_stats/success`.

## What a real driver would take

Fast charging, a higher input limit and a real charging status need a charger driver:

1. **SMB5 support in the kernel.** The upstream series "power: supply: qcom_smbx: add SMB5 support" (v4, 2026-08-20, by Casey Connolly and others) adds SMB5 to `qcom_smbx`. It isn't merged, and it lists PM8150B and PM7250B, not PM6150. The sm6350-mainline tree carries an older version with a PM7250B node. Out-of-tree modules for PM6150 on the sm7125 kernel exist ([asidko/pm6150-charger-mainline](https://github.com/asidko/pm6150-charger-mainline)), not reviewed here: build them from source rather than loading prebuilt modules.
2. **A charger node in the device tree** (`charger@1000` in `pm6150.dtsi`), with `monitored-battery` pointing at the battery.
3. **Building it** against your kernel, and booting it from a second entry first.

Until then, the dual-role port and a USB-C charger give steady charging at about 0.75 A.

## Last verified

Source-only port, the dual-role fix, the registers and the boot loop: excalibur, postmarketOS v26.06, kernel `6.14.7-sm7125`, 2026-11-28. Driver absence in `sm7125-mainline` up to `sm7125-7.4.0-next-20261113`, and suspend: 2026-11-21. The upstream SMB5 series' status: 2026-11-28.

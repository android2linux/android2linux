# Charging a phone with no charger driver

This guide is about a phone whose charger chip has **no mainline driver**, and what you can still rely on. It explains why the PM6150 "SMB5" charger does not work as expected under a mainline kernel, what the hardware's power-on defaults actually give you (a PC port is roughly break-even, a wall charger works with the screen off), how to measure charging honestly with the battery gauge, how suspend behaves, and what a real fix would take. It is the honest answer to "does it charge?" for the device in [`../devices/xiaomi-redmi-note-9-pro-max.md`](../../../../phones/xiaomi-excalibur/).

## The missing driver

The phone's charger is part of the **PM6150** PMIC and belongs to Qualcomm's **"SMB5"** charger generation. Mainline, and every `sm7125-mainline` branch up to `sm7125-7.4.0-next-20261113`, only carries **`qcom_smbx`** (formerly `qcom_pmi8998_charger`), which targets PMI8998/PM660 — the older **"SMB2"** generation. There is no SMB5 driver anywhere upstream.

That is why Ubuntu Touch charged properly: it ran Android's kernel, which has Qualcomm's **`qpnp-smb5`** driver. Under a mainline kernel, nothing drives the charger.

## What the hardware defaults give you

With no driver, the chip runs on its **power-on defaults**:

- **No fast charging.** It trickles at whatever the default mode allows.
- **No status reporting.** The battery `status` reads "Unknown" all the time; the USB-C type supply reports `online=0`; `power_role` can show `[source]` while `usb_vbus` is off — nothing is negotiated.

What that means in practice:

| Setup | Result |
|---|---|
| USB-C **wall charger**, **screen off** | Works, slowly: 75 % → 83 % in 30 min, voltage 4152 → 4228 mV (2026-11-21) |
| **PC USB port** | Roughly break-even with the screen on; the battery still supplies part of the load (~55–240 mA plugged in vs ~200–350 mA unplugged) |
| Screen on, heavy use | Drains (~540 mA at full brightness with a browser open, about 10 %/hour on 5,020 mAh) |

The power chip still supplies part of the load on its own, which is why a PC port can nudge the gauge up (97 → 98 % plugged in) rather than only slowing the drain. But it is not real charging, and with the screen on it is close to a wash.

**The practical advice:** charge from a wall charger with the screen off. It is slow but it works.

## How to measure charging without trusting the gauge

The battery gauge (`qcom_qg`) reads capacity and voltage, but its current reading is unreliable and its status is always "Unknown". Measure by **capacity and voltage over time** instead:

- Note capacity (%) and voltage (mV), wait a known interval, note them again.
- A rising voltage (e.g. 4152 → 4228 mV over 30 min) alongside rising capacity is real charging.
- Use `current_now` only for its **sign**: positive means drawn from the battery, negative means charging (into the battery). Do not trust its magnitude — the gauge reported only about −200 mA while the voltage climbed clearly.

Read the values from the standard power-supply sysfs nodes for the battery. Because the status field is useless here, always cross-check with capacity and voltage.

## Suspend

Suspend is **`s2idle`** only. It works: the phone slept 10:15–10:23 on 2026-11-21 and resumed, with a kernel warning logged on resume (benign for this test). Suspend matters for charging because a suspended phone with the screen off is the best case for the trickle-charge defaults — it is the state in which a wall charger actually gains.

Standby drain while locked with the screen off had not been measured at the time of these notes; only the screen-on drain (~540 mA) was.

## What a real fix would take

This is not a setting you can toggle. A proper fix needs:

1. **Port SMB5 support** into the kernel charger driver. There is a proposed upstream direction for adding it to `qcom_smbx`; it is not there yet.
2. **A charger node in the device tree** describing this PMIC's charger to that driver.
3. **Building your own kernel** with both, since neither is in the current kernel you are running.

Until then, watch `sm7125-mainline` for charger work. The honest status is: it charges slowly on its defaults, and that is not going to change without kernel work.

## Last verified

Wall-charger gain (75 → 83 % in 30 min, screen off) and s2idle suspend: 2026-11-21. Driver absence checked against `sm7125-mainline` up to `sm7125-7.4.0-next-20261113`: 2026-11-21. Checked 2026-11-21.

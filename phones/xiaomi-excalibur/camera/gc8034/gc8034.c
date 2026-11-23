// SPDX-License-Identifier: GPL-2.0
/*
 * GalaxyCore GC8034 8 MP image sensor, two MIPI CSI-2 lanes, 3264x2448 at 15 fps (RAW10).
 *
 * A mainline port of Rockchip's driver (rockchip-linux/kernel develop-6.1, drivers/media/i2c/
 * gc8034.c, Copyright (C) 2019 Rockchip Electronics Co., Ltd.): its register tables, exposure and
 * gain programming and power sequence, without Rockchip's module ioctls and OTP. Written for the
 * Redmi Note 9 Pro Max's ultrawide camera.
 */

#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/pm_runtime.h>
#include <linux/regulator/consumer.h>
#include <media/media-entity.h>
#include <media/v4l2-ctrls.h>
#include <media/v4l2-device.h>
#include <media/v4l2-fwnode.h>
#include <media/v4l2-subdev.h>

#define GC8034_CHIP_ID		0x8044
#define GC8034_REG_CHIP_ID_H	0xf0
#define GC8034_REG_CHIP_ID_L	0xf1
#define GC8034_REG_SET_PAGE	0xfe
#define GC8034_REG_CTRL_MODE	0x3f
#define GC8034_MODE_STANDBY	0x00
/* Streaming on two lanes (Rockchip: 0xd0 is for four). */
#define GC8034_MODE_STREAMING	0x91
#define GC8034_REG_EXPOSURE_H	0x03
#define GC8034_REG_EXPOSURE_L	0x04
#define GC8034_REG_VB_H		0x07
#define GC8034_REG_VB_L		0x08

#define GC8034_WIDTH		3264
#define GC8034_HEIGHT		2448
#define GC8034_HTS		(0x0858 * 2)
#define GC8034_VTS_MAX		0x1fff
#define GC8034_XVCLK_FREQ	24000000
#define GC8034_EXPOSURE_MIN	4
/*
 * Rockchip's 15 fps set for two lanes (672 Mbps a lane). Its 30 fps set (634 MHz) came out on
 * excalibur as lines of 3856 bytes instead of 4080, sheared and short of the frame.
 */
#define GC8034_VTS		0x09c4
#define GC8034_FPS		15
#define GC8034_LINK_FREQ	336000000ULL
#define GC8034_EXPOSURE_DEF	0x09a0
#define GC8034_PIXEL_RATE	(GC8034_HTS * GC8034_VTS * GC8034_FPS)
#define GC8034_GAIN_MIN		64
#define GC8034_GAIN_MAX		1092
#define GC8034_GAIN_DEF		64
#define GC8034_MBUS_CODE	MEDIA_BUS_FMT_SRGGB10_1X10

#define REG_NULL		0xff

struct gc8034_reg {
	u8 addr;
	u8 val;
};

#include "gc8034-tables.inc"

static const char * const gc8034_supply_names[] = { "dovdd", "dvdd", "avdd" };
#define GC8034_NUM_SUPPLIES ARRAY_SIZE(gc8034_supply_names)

static const s64 gc8034_link_freqs[] = { GC8034_LINK_FREQ };

struct gc8034 {
	struct i2c_client *client;
	struct clk *xvclk;
	struct gpio_desc *reset_gpio;
	struct gpio_desc *pwdn_gpio;
	struct regulator_bulk_data supplies[GC8034_NUM_SUPPLIES];

	struct v4l2_subdev sd;
	struct media_pad pad;
	struct v4l2_ctrl_handler ctrls;
	struct v4l2_ctrl *exposure;
	struct v4l2_ctrl *vblank;

	/* Serialises the controls and streaming. */
	struct mutex lock;
	bool streaming;
	/* The digital gain that makes up for an odd exposure (it is written in steps of two). */
	u32 dgain_ratio;
};

static inline struct gc8034 *to_gc8034(struct v4l2_subdev *sd)
{
	return container_of(sd, struct gc8034, sd);
}

static int gc8034_write(struct gc8034 *gc, u8 reg, u8 val)
{
	int ret = i2c_smbus_write_byte_data(gc->client, reg, val);

	if (ret < 0)
		dev_err(&gc->client->dev, "write 0x%02x=0x%02x failed: %d\n", reg, val, ret);
	return ret < 0 ? ret : 0;
}

static int gc8034_read(struct gc8034 *gc, u8 reg, u8 *val)
{
	int ret = i2c_smbus_read_byte_data(gc->client, reg);

	if (ret < 0)
		return ret;
	*val = ret;
	return 0;
}

static int gc8034_write_array(struct gc8034 *gc, const struct gc8034_reg *regs)
{
	int ret = 0;

	for (; ret == 0 && regs->addr != REG_NULL; regs++)
		ret = gc8034_write(gc, regs->addr, regs->val);
	return ret;
}

static int gc8034_set_exposure(struct gc8034 *gc, u32 exposure)
{
	u32 shutter = exposure & ~1u;
	int ret;

	gc->dgain_ratio = 256 * exposure / shutter;
	ret = gc8034_write(gc, GC8034_REG_SET_PAGE, 0x00);
	ret |= gc8034_write(gc, GC8034_REG_EXPOSURE_H, (shutter >> 8) & 0x7f);
	ret |= gc8034_write(gc, GC8034_REG_EXPOSURE_L, shutter & 0xff);
	return ret;
}

#define GC8034_GAIN_STEPS 9
#define GC8034_GAIN_STEPS_USED 7

/* Analogue gain steps in 1/64 (1.0, 1.375, 1.95, 2.7, 3.8, 5.4, 7.66, 10.688, 15.03). */
static const u16 gc8034_gain_levels[GC8034_GAIN_STEPS] = {
	0x0040, 0x0058, 0x007d, 0x00ad, 0x00f3, 0x0159, 0x01ea, 0x02ac, 0x03c2,
};

/* The analogue settings for each step: page 0 0x20, 0x33; page 1 0xdf, 0xe7..0xee. */
static const u8 gc8034_gain_regs[GC8034_GAIN_STEPS][14] = {
	{ 0x00, 0x55, 0x83, 0x01, 0x06, 0x18, 0x20, 0x16, 0x17, 0x50, 0x6c, 0x9b, 0xd8, 0x00 },
	{ 0x00, 0x55, 0x83, 0x01, 0x06, 0x18, 0x20, 0x16, 0x17, 0x50, 0x6c, 0x9b, 0xd8, 0x00 },
	{ 0x00, 0x4e, 0x84, 0x01, 0x0c, 0x2e, 0x2d, 0x15, 0x19, 0x47, 0x70, 0x9f, 0xd8, 0x00 },
	{ 0x00, 0x51, 0x80, 0x01, 0x07, 0x28, 0x32, 0x22, 0x20, 0x49, 0x70, 0x91, 0xd9, 0x00 },
	{ 0x00, 0x4d, 0x83, 0x01, 0x0f, 0x3b, 0x3b, 0x1c, 0x1f, 0x47, 0x6f, 0x9b, 0xd3, 0x00 },
	{ 0x00, 0x50, 0x83, 0x01, 0x08, 0x35, 0x46, 0x1e, 0x22, 0x4c, 0x70, 0x9a, 0xd2, 0x00 },
	{ 0x00, 0x52, 0x80, 0x01, 0x0c, 0x35, 0x3a, 0x2b, 0x2d, 0x4c, 0x67, 0x8d, 0xc0, 0x00 },
	{ 0x00, 0x52, 0x80, 0x01, 0x0c, 0x35, 0x3a, 0x2b, 0x2d, 0x4c, 0x67, 0x8d, 0xc0, 0x00 },
	{ 0x00, 0x52, 0x80, 0x01, 0x0c, 0x35, 0x3a, 0x2b, 0x2d, 0x4c, 0x67, 0x8d, 0xc0, 0x00 },
};

static const u8 gc8034_gain_addrs[14] = {
	0xfe, 0x20, 0x33, 0xfe, 0xdf, 0xe7, 0xe8, 0xe9, 0xea, 0xeb, 0xec, 0xed, 0xee, 0xfe,
};

static int gc8034_set_gain(struct gc8034 *gc, u32 gain)
{
	int step, i, ret;
	u32 dgain;

	for (step = GC8034_GAIN_STEPS_USED - 1; step > 0; step--)
		if (gain >= gc8034_gain_levels[step])
			break;

	dgain = 256 * gain / gc8034_gain_levels[step];
	dgain = dgain * gc->dgain_ratio / 256;

	ret = gc8034_write(gc, GC8034_REG_SET_PAGE, 0x00);
	ret |= gc8034_write(gc, 0xb6, step);
	ret |= gc8034_write(gc, 0xb1, dgain >> 8);
	ret |= gc8034_write(gc, 0xb2, dgain & 0xff);
	for (i = 0; i < 14; i++)
		ret |= gc8034_write(gc, gc8034_gain_addrs[i], gc8034_gain_regs[step][i]);
	return ret;
}

static int gc8034_s_ctrl(struct v4l2_ctrl *ctrl)
{
	struct gc8034 *gc = container_of(ctrl->handler, struct gc8034, ctrls);
	struct device *dev = &gc->client->dev;
	int ret = 0;
	int vb;

	if (ctrl->id == V4L2_CID_VBLANK)
		__v4l2_ctrl_modify_range(gc->exposure, gc->exposure->minimum,
					 GC8034_HEIGHT + ctrl->val - 4, gc->exposure->step,
					 gc->exposure->default_value);

	if (!pm_runtime_get_if_in_use(dev))
		return 0;

	switch (ctrl->id) {
	case V4L2_CID_EXPOSURE:
		ret = gc8034_set_exposure(gc, ctrl->val);
		break;
	case V4L2_CID_ANALOGUE_GAIN:
		ret = gc8034_set_gain(gc, ctrl->val);
		break;
	case V4L2_CID_VBLANK:
		/* The sensor's blanking register counts from 36 lines (Rockchip, after Android's). */
		vb = ctrl->val - 36;
		ret = gc8034_write(gc, GC8034_REG_SET_PAGE, 0x00);
		ret |= gc8034_write(gc, GC8034_REG_VB_H, (vb >> 8) & 0xff);
		ret |= gc8034_write(gc, GC8034_REG_VB_L, vb & 0xff);
		break;
	default:
		break;
	}

	pm_runtime_put(dev);
	return ret;
}

static const struct v4l2_ctrl_ops gc8034_ctrl_ops = {
	.s_ctrl = gc8034_s_ctrl,
};

static int gc8034_start(struct gc8034 *gc)
{
	int ret;

	ret = gc8034_write_array(gc, gc8034_global_regs);
	ret = ret ?: gc8034_write_array(gc, gc8034_3264x2448_regs);
	if (ret)
		return ret;
	ret = __v4l2_ctrl_handler_setup(&gc->ctrls);
	if (ret)
		return ret;
	ret = gc8034_write(gc, GC8034_REG_SET_PAGE, 0x00);
	return ret ?: gc8034_write(gc, GC8034_REG_CTRL_MODE, GC8034_MODE_STREAMING);
}

static void gc8034_stop(struct gc8034 *gc)
{
	gc8034_write(gc, GC8034_REG_SET_PAGE, 0x00);
	gc8034_write(gc, GC8034_REG_CTRL_MODE, GC8034_MODE_STANDBY);
}

static int gc8034_s_stream(struct v4l2_subdev *sd, int on)
{
	struct gc8034 *gc = to_gc8034(sd);
	struct device *dev = &gc->client->dev;
	int ret = 0;

	mutex_lock(&gc->lock);
	if (!!on == gc->streaming)
		goto out;

	if (on) {
		ret = pm_runtime_resume_and_get(dev);
		if (ret < 0)
			goto out;
		ret = gc8034_start(gc);
		if (ret) {
			pm_runtime_put(dev);
			goto out;
		}
	} else {
		gc8034_stop(gc);
		pm_runtime_put(dev);
	}
	gc->streaming = !!on;
out:
	mutex_unlock(&gc->lock);
	return ret;
}

static void gc8034_fill_fmt(struct v4l2_mbus_framefmt *fmt)
{
	fmt->width = GC8034_WIDTH;
	fmt->height = GC8034_HEIGHT;
	fmt->code = GC8034_MBUS_CODE;
	fmt->field = V4L2_FIELD_NONE;
	fmt->colorspace = V4L2_COLORSPACE_RAW;
	fmt->ycbcr_enc = V4L2_YCBCR_ENC_601;
	fmt->quantization = V4L2_QUANTIZATION_FULL_RANGE;
	fmt->xfer_func = V4L2_XFER_FUNC_NONE;
}

/* One mode: setting a format answers it, whatever was asked. */
static int gc8034_get_fmt(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
			  struct v4l2_subdev_format *fmt)
{
	gc8034_fill_fmt(&fmt->format);
	return 0;
}

static int gc8034_enum_mbus_code(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
				 struct v4l2_subdev_mbus_code_enum *code)
{
	if (code->index > 0)
		return -EINVAL;
	code->code = GC8034_MBUS_CODE;
	return 0;
}

static int gc8034_enum_frame_size(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
				  struct v4l2_subdev_frame_size_enum *fse)
{
	if (fse->index > 0 || fse->code != GC8034_MBUS_CODE)
		return -EINVAL;
	fse->min_width = fse->max_width = GC8034_WIDTH;
	fse->min_height = fse->max_height = GC8034_HEIGHT;
	return 0;
}

static int gc8034_get_selection(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
				struct v4l2_subdev_selection *sel)
{
	switch (sel->target) {
	case V4L2_SEL_TGT_CROP:
	case V4L2_SEL_TGT_CROP_DEFAULT:
	case V4L2_SEL_TGT_CROP_BOUNDS:
	case V4L2_SEL_TGT_NATIVE_SIZE:
		sel->r.left = 0;
		sel->r.top = 0;
		sel->r.width = GC8034_WIDTH;
		sel->r.height = GC8034_HEIGHT;
		return 0;
	default:
		return -EINVAL;
	}
}

static const struct v4l2_subdev_video_ops gc8034_video_ops = {
	.s_stream = gc8034_s_stream,
};

static const struct v4l2_subdev_pad_ops gc8034_pad_ops = {
	.enum_mbus_code = gc8034_enum_mbus_code,
	.enum_frame_size = gc8034_enum_frame_size,
	.get_fmt = gc8034_get_fmt,
	.set_fmt = gc8034_get_fmt,
	.get_selection = gc8034_get_selection,
};

static const struct v4l2_subdev_ops gc8034_subdev_ops = {
	.video = &gc8034_video_ops,
	.pad = &gc8034_pad_ops,
};

static int gc8034_power_on(struct device *dev)
{
	struct v4l2_subdev *sd = dev_get_drvdata(dev);
	struct gc8034 *gc = to_gc8034(sd);
	int ret;

	gpiod_set_value_cansleep(gc->reset_gpio, 1);
	ret = regulator_bulk_enable(GC8034_NUM_SUPPLIES, gc->supplies);
	if (ret) {
		dev_err(dev, "failed to enable the regulators: %d\n", ret);
		return ret;
	}
	usleep_range(100, 200);
	ret = clk_prepare_enable(gc->xvclk);
	if (ret) {
		dev_err(dev, "failed to enable xvclk: %d\n", ret);
		regulator_bulk_disable(GC8034_NUM_SUPPLIES, gc->supplies);
		return ret;
	}
	usleep_range(1000, 1100);
	gpiod_set_value_cansleep(gc->pwdn_gpio, 0);
	usleep_range(500, 1000);
	gpiod_set_value_cansleep(gc->reset_gpio, 0);
	/* 6 ms, then 8192 input clock cycles before the first command. */
	usleep_range(6000, 7000);
	usleep_range(400, 800);
	return 0;
}

static int gc8034_power_off(struct device *dev)
{
	struct v4l2_subdev *sd = dev_get_drvdata(dev);
	struct gc8034 *gc = to_gc8034(sd);

	gpiod_set_value_cansleep(gc->pwdn_gpio, 1);
	gpiod_set_value_cansleep(gc->reset_gpio, 1);
	clk_disable_unprepare(gc->xvclk);
	regulator_bulk_disable(GC8034_NUM_SUPPLIES, gc->supplies);
	return 0;
}

static int gc8034_identify(struct gc8034 *gc)
{
	u8 high = 0, low = 0;
	int ret;

	ret = gc8034_read(gc, GC8034_REG_CHIP_ID_H, &high);
	ret = ret ?: gc8034_read(gc, GC8034_REG_CHIP_ID_L, &low);
	if (ret) {
		dev_err(&gc->client->dev, "cannot read the chip id: %d\n", ret);
		return ret;
	}
	if (((high << 8) | low) != GC8034_CHIP_ID) {
		dev_err(&gc->client->dev, "unexpected chip id %02x%02x\n", high, low);
		return -ENXIO;
	}
	dev_info(&gc->client->dev, "detected gc8034 sensor\n");
	return 0;
}

static int gc8034_check_endpoint(struct device *dev)
{
	struct v4l2_fwnode_endpoint bus = { .bus_type = V4L2_MBUS_CSI2_DPHY };
	struct fwnode_handle *ep;
	unsigned long freq;
	int ret;

	ep = fwnode_graph_get_next_endpoint(dev_fwnode(dev), NULL);
	if (!ep)
		return dev_err_probe(dev, -EINVAL, "no endpoint\n");
	ret = v4l2_fwnode_endpoint_alloc_parse(ep, &bus);
	fwnode_handle_put(ep);
	if (ret)
		return dev_err_probe(dev, ret, "cannot parse the endpoint\n");
	if (bus.bus.mipi_csi2.num_data_lanes != 2) {
		ret = dev_err_probe(dev, -EINVAL, "only two data lanes are supported\n");
		goto out;
	}
	ret = v4l2_link_freq_to_bitmap(dev, bus.link_frequencies, bus.nr_of_link_frequencies,
				       gc8034_link_freqs, ARRAY_SIZE(gc8034_link_freqs), &freq);
out:
	v4l2_fwnode_endpoint_free(&bus);
	return ret;
}

static int gc8034_init_controls(struct gc8034 *gc)
{
	struct v4l2_ctrl_handler *h = &gc->ctrls;
	struct v4l2_fwnode_device_properties props;
	struct v4l2_ctrl *ctrl;
	u32 vblank = GC8034_VTS - GC8034_HEIGHT;
	u32 hblank = GC8034_HTS - GC8034_WIDTH;
	int ret;

	v4l2_ctrl_handler_init(h, 9);
	h->lock = &gc->lock;

	ctrl = v4l2_ctrl_new_int_menu(h, NULL, V4L2_CID_LINK_FREQ, 0, 0, gc8034_link_freqs);
	if (ctrl)
		ctrl->flags |= V4L2_CTRL_FLAG_READ_ONLY;
	v4l2_ctrl_new_std(h, NULL, V4L2_CID_PIXEL_RATE, GC8034_PIXEL_RATE, GC8034_PIXEL_RATE, 1,
			  GC8034_PIXEL_RATE);
	ctrl = v4l2_ctrl_new_std(h, NULL, V4L2_CID_HBLANK, hblank, hblank, 1, hblank);
	if (ctrl)
		ctrl->flags |= V4L2_CTRL_FLAG_READ_ONLY;
	gc->vblank = v4l2_ctrl_new_std(h, &gc8034_ctrl_ops, V4L2_CID_VBLANK, vblank,
				       GC8034_VTS_MAX - GC8034_HEIGHT, 1, vblank);
	gc->exposure = v4l2_ctrl_new_std(h, &gc8034_ctrl_ops, V4L2_CID_EXPOSURE,
					 GC8034_EXPOSURE_MIN, GC8034_VTS - 4, 1, GC8034_EXPOSURE_DEF);
	v4l2_ctrl_new_std(h, &gc8034_ctrl_ops, V4L2_CID_ANALOGUE_GAIN, GC8034_GAIN_MIN,
			  GC8034_GAIN_MAX, 1, GC8034_GAIN_DEF);

	ret = v4l2_fwnode_device_parse(&gc->client->dev, &props);
	if (!ret)
		v4l2_ctrl_new_fwnode_properties(h, &gc8034_ctrl_ops, &props);

	if (h->error) {
		ret = h->error;
		v4l2_ctrl_handler_free(h);
		return ret;
	}
	gc->sd.ctrl_handler = h;
	return 0;
}

static int gc8034_probe(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct gc8034 *gc;
	unsigned int i;
	int ret;

	ret = gc8034_check_endpoint(dev);
	if (ret)
		return ret;

	gc = devm_kzalloc(dev, sizeof(*gc), GFP_KERNEL);
	if (!gc)
		return -ENOMEM;
	gc->client = client;
	gc->dgain_ratio = 256;

	gc->xvclk = devm_clk_get(dev, "xvclk");
	if (IS_ERR(gc->xvclk))
		return dev_err_probe(dev, PTR_ERR(gc->xvclk), "no xvclk\n");
	ret = clk_set_rate(gc->xvclk, GC8034_XVCLK_FREQ);
	if (ret)
		return dev_err_probe(dev, ret, "cannot set xvclk to 24 MHz\n");

	gc->reset_gpio = devm_gpiod_get_optional(dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(gc->reset_gpio))
		return dev_err_probe(dev, PTR_ERR(gc->reset_gpio), "no reset gpio\n");
	gc->pwdn_gpio = devm_gpiod_get_optional(dev, "pwdn", GPIOD_OUT_HIGH);
	if (IS_ERR(gc->pwdn_gpio))
		return dev_err_probe(dev, PTR_ERR(gc->pwdn_gpio), "no pwdn gpio\n");

	for (i = 0; i < GC8034_NUM_SUPPLIES; i++)
		gc->supplies[i].supply = gc8034_supply_names[i];
	ret = devm_regulator_bulk_get(dev, GC8034_NUM_SUPPLIES, gc->supplies);
	if (ret)
		return dev_err_probe(dev, ret, "cannot get the regulators\n");

	mutex_init(&gc->lock);
	v4l2_i2c_subdev_init(&gc->sd, client, &gc8034_subdev_ops);

	/*
	 * On excalibur the sensor shares its CCI bus with the macro camera, and a first read at boot
	 * sometimes gets no answer (-110, -5): the bus recovers once it has suspended (a second
	 * idle), so the sensor is powered off and tried again after two seconds.
	 */
	for (i = 1; ; i++) {
		ret = gc8034_power_on(dev);
		if (ret)
			goto err_mutex;
		ret = gc8034_identify(gc);
		if (!ret || ret == -ENXIO || i == 4)
			break;
		dev_warn(dev, "no answer on try %u, power-cycling the sensor\n", i);
		gc8034_power_off(dev);
		msleep(2000);
	}
	if (ret)
		goto err_power;

	ret = gc8034_init_controls(gc);
	if (ret)
		goto err_power;

	gc->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
	gc->sd.entity.function = MEDIA_ENT_F_CAM_SENSOR;
	gc->pad.flags = MEDIA_PAD_FL_SOURCE;
	ret = media_entity_pads_init(&gc->sd.entity, 1, &gc->pad);
	if (ret)
		goto err_ctrls;

	pm_runtime_set_active(dev);
	pm_runtime_enable(dev);

	ret = v4l2_async_register_subdev_sensor(&gc->sd);
	if (ret) {
		dev_err(dev, "cannot register the subdevice: %d\n", ret);
		goto err_pm;
	}

	pm_runtime_idle(dev);
	return 0;

err_pm:
	pm_runtime_disable(dev);
	pm_runtime_set_suspended(dev);
	media_entity_cleanup(&gc->sd.entity);
err_ctrls:
	v4l2_ctrl_handler_free(&gc->ctrls);
err_power:
	gc8034_power_off(dev);
err_mutex:
	mutex_destroy(&gc->lock);
	return ret;
}

static void gc8034_remove(struct i2c_client *client)
{
	struct v4l2_subdev *sd = i2c_get_clientdata(client);
	struct gc8034 *gc = to_gc8034(sd);

	v4l2_async_unregister_subdev(sd);
	media_entity_cleanup(&sd->entity);
	v4l2_ctrl_handler_free(&gc->ctrls);
	pm_runtime_disable(&client->dev);
	if (!pm_runtime_status_suspended(&client->dev))
		gc8034_power_off(&client->dev);
	pm_runtime_set_suspended(&client->dev);
	mutex_destroy(&gc->lock);
}

static DEFINE_RUNTIME_DEV_PM_OPS(gc8034_pm_ops, gc8034_power_off, gc8034_power_on, NULL);

static const struct of_device_id gc8034_of_match[] = {
	{ .compatible = "galaxycore,gc8034" },
	{ }
};
MODULE_DEVICE_TABLE(of, gc8034_of_match);

static struct i2c_driver gc8034_driver = {
	.driver = {
		.name = "gc8034",
		.pm = pm_ptr(&gc8034_pm_ops),
		.of_match_table = gc8034_of_match,
	},
	.probe = gc8034_probe,
	.remove = gc8034_remove,
};
module_i2c_driver(gc8034_driver);

MODULE_DESCRIPTION("GalaxyCore GC8034 image sensor driver");
MODULE_LICENSE("GPL");

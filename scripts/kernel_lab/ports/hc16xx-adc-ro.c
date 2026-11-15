// SPDX-License-Identifier: GPL-2.0
/* Passive access to SAR result bytes, preserving conversions configured by AVP. */
#include <linux/clk.h>
#include <linux/iio/iio.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>

struct hc16xx_adc_ro { void __iomem *results; };

static int adc_read(struct iio_dev *indio, const struct iio_chan_spec *channel,
                    int *value, int *value2, long mask)
{
    struct hc16xx_adc_ro *adc = iio_priv(indio);
    unsigned int offset = channel->channel;
    if (mask != IIO_CHAN_INFO_RAW) return -EINVAL;
    if (offset >= 4) offset += 2;
    *value = readb(adc->results + offset);
    return IIO_VAL_INT;
}

#define ADC_CHANNEL(n) { .type = IIO_VOLTAGE, .indexed = 1, .channel = (n), \
                        .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) }
static const struct iio_chan_spec adc_channels[] = {
    ADC_CHANNEL(0), ADC_CHANNEL(1), ADC_CHANNEL(2),
    ADC_CHANNEL(3), ADC_CHANNEL(4), ADC_CHANNEL(5),
};
static const struct iio_info adc_info = { .read_raw = adc_read };

static int adc_probe(struct platform_device *pdev)
{
    struct iio_dev *indio;
    struct hc16xx_adc_ro *adc;
    struct clk *clk;
    indio = devm_iio_device_alloc(&pdev->dev, sizeof(*adc));
    if (!indio) return -ENOMEM;
    adc = iio_priv(indio);
    adc->results = devm_platform_ioremap_resource(pdev, 0);
    if (IS_ERR(adc->results)) return PTR_ERR(adc->results);
    clk = devm_clk_get_enabled(&pdev->dev, NULL);
    if (IS_ERR(clk)) return dev_err_probe(&pdev->dev, PTR_ERR(clk), "ADC clock unavailable\n");
    indio->name = "hc16xx-adc-ro";
    indio->info = &adc_info;
    indio->modes = INDIO_DIRECT_MODE;
    indio->channels = adc_channels;
    indio->num_channels = ARRAY_SIZE(adc_channels);
    return devm_iio_device_register(&pdev->dev, indio);
}

static const struct of_device_id adc_match[] = {
    { .compatible = "r36lab,hc16xx-adc-ro" }, { }
};
MODULE_DEVICE_TABLE(of, adc_match);
static struct platform_driver adc_driver = {
    .probe = adc_probe,
    .driver = { .name = "r36-hc16xx-adc-ro", .of_match_table = adc_match },
};
module_platform_driver(adc_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Read-only HC16xx SAR results while stock AVP owns conversion setup");

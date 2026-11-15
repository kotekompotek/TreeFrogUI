from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usb_overlay import patch_musb_irq_lifecycle

SOURCE = '''static void hc16xx_musb_enable(struct musb *musb)
{
    struct hc16xx_glue *glue = get(musb);
    enable_irq(glue->irq);
}

static void hc16xx_musb_disable(struct musb *musb)
{
    struct hc16xx_glue *glue = get(musb);
    disable_irq(glue->irq);
}

static const struct musb_platform_ops ops = {
\t.enable\t\t= hc16xx_musb_enable,
\t.disable\t= hc16xx_musb_disable,
};
int probe(void) {
\tdisable_irq(glue->irq);
\treturn 0;

err_pdev:
    return -1;
}
'''


def test_no_nested_irq_depth_or_waiting_under_musb_spinlock():
    patched = patch_musb_irq_lifecycle(SOURCE)
    assert 'enable_irq(' not in patched and 'disable_irq(' not in patched
    assert patch_musb_irq_lifecycle(patched) == patched
    assert 'Core owns IRQ registration' in patched
    # No claim that this model explains the old physical enumeration failure:
    # regression scope is removal of waiting IRQ-depth calls from the glue.
    assert '.disable' not in patched


def test_unknown_callback_or_probe_fails_closed():
    with pytest.raises(ValueError):
        patch_musb_irq_lifecycle(SOURCE.replace('disable_irq(glue->irq);', 'custom_disable();'))
    with pytest.raises(ValueError):
        patch_musb_irq_lifecycle(SOURCE.replace('err_pdev:', 'different:'))
    with pytest.raises(ValueError):
        patch_musb_irq_lifecycle(SOURCE.replace('enable_irq(glue->irq);', 'writel(1, regs);\n    enable_irq(glue->irq);'))

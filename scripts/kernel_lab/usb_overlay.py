"""Private MUSB IRQ-lifecycle fix; no fabricated USB/host/DMA support."""
import re


def patch_musb_irq_lifecycle(text):
    before = text
    for name in ('hc16xx_musb_enable', 'hc16xx_musb_disable'):
        # These wrappers only operate the Linux IRQ depth, not extra SoC gates.
        # Core start/stop already masks the controller and calls disable under
        # musb->lock. disable_irq() may wait for an ISR taking the same lock.
        pattern = (r'static void ' + name + r'\(struct musb \*musb\)\n\{\n'
                   r'.*?\n\}\n\n')
        matches = list(re.finditer(pattern, text, re.S))
        if matches:
            if len(matches) != 1:
                raise ValueError('duplicate USB IRQ callback')
            block = matches[0].group()
            call = 'enable_irq(glue->irq);' if name.endswith('_enable') else 'disable_irq(glue->irq);'
            if block.count(call) != 1 or 'writel' in block or 'writeb' in block:
                raise ValueError('USB IRQ callback has changed semantics')
            text = text[:matches[0].start()] + text[matches[0].end():]
        binding = '.enable\t\t= hc16xx_musb_enable,' if name.endswith('_enable') else '.disable\t= hc16xx_musb_disable,'
        if binding in text:
            text = text.replace('\t' + binding + '\n', '', 1)
        elif name in text:
            raise ValueError('unexpected USB callback binding')
    old = '\tdisable_irq(glue->irq);\n\treturn 0;\n\nerr_pdev:'
    new = '\t/* Core owns IRQ registration and controller interrupt masking. */\n\treturn 0;\n\nerr_pdev:'
    if text.count(old) == 1:
        text = text.replace(old, new, 1)
    elif text.count(new) != 1:
        raise ValueError('unexpected post-child USB IRQ disable')
    if 'enable_irq(glue->irq)' in text or 'disable_irq(glue->irq)' in text:
        raise ValueError('unbalanced IRQ-depth calls remain')
    if text == before and new not in text:
        raise ValueError('USB IRQ patch not applied')
    return text

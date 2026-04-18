#!/usr/bin/env python3
"""Patch api_update to save all new campaign settings."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/bp_api_core.py"
with open(path, "r") as f:
    content = f.read()

old_update = """            # Update delay
            delay_val = request.form.get(f'{sector_name}_delay_min')
            if delay_val:
                sector['delay_min'] = int(delay_val)

            # Update sender
            sender_val = request.form.get(f'{sector_name}_sender')
            if sender_val:
                sector['sender_email'] = sender_val"""

new_update = """            # Update delays
            delay_val = request.form.get(f'{sector_name}_delay_min')
            if delay_val:
                sector['delay_min'] = int(delay_val)
            delay_max = request.form.get(f'{sector_name}_delay_max')
            if delay_max:
                sector['delay_max'] = int(delay_max)

            # Update sender
            sender_val = request.form.get(f'{sector_name}_sender')
            if sender_val:
                sector['sender_email'] = sender_val

            # Sender type
            st = request.form.get(f'{sector_name}_sender_type')
            if st:
                sector['sender_type'] = st

            # Reply-to
            rt = request.form.get(f'{sector_name}_reply_to', '')
            if rt:
                sector['reply_to'] = rt

            # Sender name
            sn = request.form.get(f'{sector_name}_sender_name', '')
            if sn:
                sector['sender_name'] = sn

            # SQL filter
            filt = request.form.get(f'{sector_name}_filter', '')
            sector['filter'] = filt

            # Batch size
            bs = request.form.get(f'{sector_name}_batch_size')
            if bs is not None:
                sector['batch_size'] = int(bs)

            # Business hours
            bh = sector.get('business_hours', {})
            bh_en = request.form.get(f'{sector_name}_bh_enabled', 'false')
            bh['enabled'] = bh_en == 'true'
            bh_s = request.form.get(f'{sector_name}_bh_start')
            if bh_s:
                bh['start'] = int(bh_s)
            bh_e = request.form.get(f'{sector_name}_bh_end')
            if bh_e:
                bh['end'] = int(bh_e)
            sector['business_hours'] = bh

            # Template rotation
            tc = request.form.get(f'{sector_name}_template_count')
            if tc:
                sector['template_count'] = int(tc)

            # Gov filter
            gf = request.form.get(f'{sector_name}_gov_filter', 'false')
            if gf == 'true':
                cfg['gov_domains'] = ['gov', 'edu', 'mil', 'politia', 'primaria']
            else:
                cfg.pop('gov_domains', None)"""

content = content.replace(old_update, new_update)

with open(path, "w") as f:
    f.write(content)

n = sum(1 for _ in open(path))
print(f"bp_api_core.py: {n} lines {'OK' if n <= 250 else 'OVER'}")

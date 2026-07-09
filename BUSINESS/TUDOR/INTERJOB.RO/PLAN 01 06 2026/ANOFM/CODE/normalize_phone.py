def normalize_phone(phone):
    """Normalize Romanian phone numbers to +40 format."""
    import re
    if not phone or phone.strip() == '':
        return ''
    # Remove all non-numeric except +
    cleaned = re.sub(r'[^0-9+]', '', phone)
    # Check if it's actually a phone (length 9-15 after cleanup)
    if len(cleaned) < 9 or len(cleaned) > 15:
        return ''
    # Convert 07... (10 digits) to +407... (replace leading 0 with +40)
    if cleaned.startswith('07') and len(cleaned) == 10:
        return '+40' + cleaned[1:]
    # Convert 02... 03... 025... 026... (9-10 digits) to +402... etc
    if cleaned.startswith('0') and not cleaned.startswith('00'):
        if len(cleaned) == 9 or len(cleaned) == 10:
            return '+40' + cleaned[1:]
    # Already has +40
    if cleaned.startswith('+40'):
        return cleaned
    return cleaned
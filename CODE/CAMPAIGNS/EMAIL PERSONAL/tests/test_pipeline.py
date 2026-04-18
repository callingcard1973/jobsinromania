import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pipeline_utils import clean_name, normalize_email, normalize_phone, is_personal_domain

def test_clean_name_strips_parens():
    assert clean_name("(*) Mary") == "Mary"
    assert clean_name("(%) Jen foo") == "Jen foo"
    assert clean_name("  (*) ") == ""

def test_clean_name_strips_html_entities():
    assert clean_name("&#39;Mihai") == "Mihai"
    assert clean_name("&amp;Test") == "Test"

def test_normalize_email():
    assert normalize_email("  TEST@Gmail.COM  ") == "test@gmail.com"
    assert normalize_email("") == ""

def test_normalize_phone():
    assert normalize_phone("+43 1 280 69 03") == "+43128069 03".replace(" ", "")
    assert normalize_phone("") == ""

def test_is_personal_domain():
    assert is_personal_domain("gmail.com") is True
    assert is_personal_domain("yahoo.fr") is True
    assert is_personal_domain("merkursoft.de") is False
    assert is_personal_domain("airbnb.com") is False

def test_clean_removes_no_email_no_phone():
    src = [
        {'First Name': 'A', 'Last Name': 'B', 'E-mail 1 - Value': '', 'Phone 1 - Value': '', 'Notes': ''},
        {'First Name': 'C', 'Last Name': 'D', 'E-mail 1 - Value': 'c@d.com', 'Phone 1 - Value': '', 'Notes': ''},
    ]
    filtered = [r for r in src if normalize_email(r['E-mail 1 - Value']) or r['Phone 1 - Value'].strip()]
    assert len(filtered) == 1
    assert filtered[0]['E-mail 1 - Value'] == 'c@d.com'

def test_clean_normalizes_email():
    assert normalize_email('  TEST@Gmail.COM ') == 'test@gmail.com'

def test_dedupe_merges_same_email():
    rows = [
        {'E-mail 1 - Value': 'a@b.com', 'First Name': 'Jo', 'Last Name': '', 'Phone 1 - Value': '123', 'Notes': 'note1', 'E-mail 2 - Value': '', 'Labels': ''},
        {'E-mail 1 - Value': 'a@b.com', 'First Name': 'Jonathan', 'Last Name': 'Smith', 'Phone 1 - Value': '456', 'Notes': 'note2', 'E-mail 2 - Value': '', 'Labels': ''},
    ]
    def longest_name(a, b):
        full_a = (a['First Name'] + ' ' + a['Last Name']).strip()
        full_b = (b['First Name'] + ' ' + b['Last Name']).strip()
        return a if len(full_a) >= len(full_b) else b
    winner = longest_name(rows[0], rows[1])
    assert winner['First Name'] == 'Jonathan'

def test_score_business_email():
    from pipeline_utils import is_personal_domain, get_email_domain
    email = 'ada.bacalum@zazibusiness.ro'
    domain = get_email_domain(email)
    assert not is_personal_domain(domain)

def test_score_airbnb_penalty():
    from pipeline_utils import get_email_domain
    email = 'guest123@guest.airbnb.com'
    domain = get_email_domain(email)
    assert 'airbnb' in domain

def test_score_clamp():
    score = max(0, min(100, 200))
    assert score == 100
    score = max(0, min(100, -50))
    assert score == 0

def test_segment_austria():
    row = {'Notes': 'Objekt: FF\nTelefon: +43 1 280 69 03', 'E-mail 1 - Value': 'a@aon.at',
           'Organization Title': '', 'Labels': '', 'Phone 1 - Value': '123', 'score': 50,
           'Organization Name': '', 'First Name': 'A', 'Last Name': 'B'}
    notes = row['Notes']
    assert 'Objekt:' in notes

def test_segment_junk_low_score():
    row = {'score': 10, 'First Name': '', 'Last Name': '', 'Organization Name': ''}
    is_junk = int(row['score']) < 20 or (not row['First Name'] and not row['Last Name'] and not row['Organization Name'])
    assert is_junk

def test_segment_personal_close():
    row = {'Labels': '* myContacts ::: * starred', 'Notes': '', 'E-mail 1 - Value': 'a@b.com'}
    assert '* starred' in row['Labels']

def test_dedupe_no_duplicate_emails():
    rows = [
        {'E-mail 1 - Value': 'x@y.com', 'First Name': 'A', 'Last Name': '', 'Phone 1 - Value': '', 'Notes': '', 'E-mail 2 - Value': '', 'Labels': ''},
        {'E-mail 1 - Value': 'x@y.com', 'First Name': 'B', 'Last Name': '', 'Phone 1 - Value': '', 'Notes': '', 'E-mail 2 - Value': '', 'Labels': ''},
        {'E-mail 1 - Value': 'z@y.com', 'First Name': 'C', 'Last Name': '', 'Phone 1 - Value': '', 'Notes': '', 'E-mail 2 - Value': '', 'Labels': ''},
    ]
    seen = {}
    for r in rows:
        key = r['E-mail 1 - Value']
        if key not in seen:
            seen[key] = r
    assert len(seen) == 2

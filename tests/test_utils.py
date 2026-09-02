from decimal import Decimal
from app.utils import normalize_phone,is_valid_yemeni_phone,normalize_name,is_valid_full_name

def test_phone_formats():
    for x in ['771234567','967771234567','+967771234567','00967771234567','٧٧١٢٣٤٥٦٧']:
        assert is_valid_yemeni_phone(normalize_phone(x))
def test_invalid_phone():
    assert not is_valid_yemeni_phone(normalize_phone('78123456'))
    assert not is_valid_yemeni_phone(normalize_phone('abc771234567'))
def test_name():
    assert is_valid_full_name('محمد علي')
    assert is_valid_full_name('أحمد')
    assert not is_valid_full_name('')

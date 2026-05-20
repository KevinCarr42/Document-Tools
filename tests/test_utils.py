from src.utils import mb


class TestMb:
    def test_zero(self):
        assert mb(0) == "0.00 MB"
    
    def test_one_megabyte(self):
        assert mb(1024 * 1024) == "1.00 MB"
    
    def test_ten_megabytes(self):
        assert mb(10 * 1024 * 1024) == "10.00 MB"
    
    def test_rounds_to_two_decimals(self):
        assert mb(1024 * 1024 + 512 * 1024) == "1.50 MB"
    
    def test_sub_megabyte(self):
        assert mb(256 * 1024) == "0.25 MB"

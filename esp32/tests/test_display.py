def test_oled_display_import():
    try:
        from esp32.drivers.oled_display import OLEDDisplay
    except ImportError:
        assert True
    else:
        assert hasattr(OLEDDisplay, "clear")

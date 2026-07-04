"""
Compatibility entry point with a more descriptive tool name.

The implementation stays in ``hid_mapper.py`` so existing deployment commands
continue to work. New workflows can keep both files together and run this
descriptive entry point, or import BLEHIDAnalyzer directly.
"""

from hid_mapper import BLEHIDAnalyzer, HidMapper, main


if __name__ == "__main__":
    main()

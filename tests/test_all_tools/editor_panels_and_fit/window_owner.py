"""WHO, a snippet defining who(number): window `number`, any app's, named as CoreGraphics lists it, by its owner and
its layer (REVIEW.md TST-419).

The window checks' snippets run it (window_states.py). So does the frames fact's (checks.py, FRAMES), to name the
windows that came in front of Designer's while it was read on screen (REVIEW.md TST-444).
"""

from textwrap import dedent

WHO = dedent("""
    def who(number):
        import ctypes.util
        cg = ctypes.CDLL(ctypes.util.find_library('CoreGraphics'))
        cf = ctypes.CDLL(ctypes.util.find_library('CoreFoundation'))
        cg.CGWindowListCopyWindowInfo.restype = ctypes.c_void_p
        cg.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        cf.CFArrayGetCount.restype, cf.CFArrayGetCount.argtypes = ctypes.c_long, [ctypes.c_void_p]
        cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
        cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
        cf.CFDictionaryGetValue.restype = ctypes.c_void_p
        cf.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
        cf.CFStringGetCString.restype = ctypes.c_bool  # a Boolean, not an int (REVIEW.md TST-430)
        cf.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p]
        cf.CFNumberGetValue.restype = ctypes.c_bool
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        keys = [cf.CFStringCreateWithCString(None, k, 0x08000100) for k in (b'kCGWindowOwnerName', b'kCGWindowLayer')]
        listed = cg.CGWindowListCopyWindowInfo(1 << 3, number)  # kCGWindowListOptionIncludingWindow: that one
        try:
            if not listed or cf.CFArrayGetCount(listed) == 0:
                return 'window %d, not listed' % number
            info = cf.CFArrayGetValueAtIndex(listed, 0)
            owner, layer = ctypes.create_string_buffer(256), ctypes.c_int64()
            name = cf.CFDictionaryGetValue(info, keys[0])
            if not (name and cf.CFStringGetCString(name, owner, 256, 0x08000100)):
                owner.value = b'?'
            cf.CFNumberGetValue(cf.CFDictionaryGetValue(info, keys[1]), 4, ctypes.byref(layer))  # kCFNumberSInt64Type
            return '%s, layer %d' % (owner.value.decode('utf-8', 'replace'), layer.value)
        finally:
            if listed:
                cf.CFRelease(listed)
            for key in keys:
                cf.CFRelease(key)
""")

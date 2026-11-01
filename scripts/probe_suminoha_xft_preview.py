import ctypes as C,ctypes.util,json
x=C.CDLL(ctypes.util.find_library('X11'));ft=C.CDLL(ctypes.util.find_library('Xft'));fc=C.CDLL(ctypes.util.find_library('fontconfig'));x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p;d=x.XOpenDisplay(b':0');assert d
class F(C.Structure):_fields_=[('ascent',C.c_int),('descent',C.c_int),('height',C.c_int),('max_advance_width',C.c_int),('charset',C.c_void_p),('pattern',C.c_void_p)]
class G(C.Structure):_fields_=[('width',C.c_ushort),('height',C.c_ushort),('x',C.c_short),('y',C.c_short),('xOff',C.c_short),('yOff',C.c_short)]
ft.XftFontOpenName.argtypes=[C.c_void_p,C.c_int,C.c_char_p];ft.XftFontOpenName.restype=C.POINTER(F);ft.XftTextExtents16.argtypes=[C.c_void_p,C.POINTER(F),C.POINTER(C.c_uint16),C.c_int,C.POINTER(G)];ft.XftFontClose.argtypes=[C.c_void_p,C.POINTER(F)];fc.FcPatternGetString.argtypes=[C.c_void_p,C.c_char_p,C.c_int,C.POINTER(C.c_char_p)];x.XCloseDisplay.argtypes=[C.c_void_p]
text='The quick brown fox jumps over the lazy dog';u=(C.c_uint16*len(text))(*map(ord,text));out={}
for name in ['Suminoha Maru Gothic Han JP','Suminoha Maru Gothic','Noto Sans']:
 f=ft.XftFontOpenName(d,0,(name+':pixelsize=16').encode());assert f;g=G();ft.XftTextExtents16(d,f,u,len(text),C.byref(g));p=C.c_char_p();fc.FcPatternGetString(f.contents.pattern,b'file',0,C.byref(p));out[name]={'file':p.value.decode(),'ink_width':g.width,'ink_height':g.height,'x_advance':g.xOff};ft.XftFontClose(d,f)
x.XCloseDisplay(d);print(json.dumps(out,ensure_ascii=False))

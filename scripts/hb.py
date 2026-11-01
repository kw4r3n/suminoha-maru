"""Small ctypes adapter to the existing system HarfBuzz; no Python binding install."""
import ctypes as C, ctypes.util
from fontTools.ttLib import TTFont
lib=C.CDLL(ctypes.util.find_library('harfbuzz'))
class Info(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ['codepoint','mask','cluster','var1','var2']]
class Feature(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ["tag","value","start","end"]]
class Position(C.Structure):
    _fields_=[(n,C.c_int32) for n in ['x_advance','y_advance','x_offset','y_offset','var']]

def bind(name,restype,*args):
    f=getattr(lib,name);f.restype=restype;f.argtypes=list(args);return f
ptr=C.c_void_p; uint=C.c_uint; string=C.c_char_p
blob_create=bind('hb_blob_create_from_file_or_fail',ptr,string)
face_create=bind('hb_face_create',ptr,ptr,uint)
font_create=bind('hb_font_create',ptr,ptr)
ot_funcs=bind('hb_ot_font_set_funcs',None,ptr)
scale=bind('hb_font_set_scale',None,ptr,C.c_int,C.c_int)
buffer_create=bind('hb_buffer_create',ptr)
add=bind('hb_buffer_add_utf8',None,ptr,string,C.c_int,uint,C.c_int)
guess=bind('hb_buffer_guess_segment_properties',None,ptr)
lang=bind('hb_language_from_string',ptr,string,C.c_int)
setlang=bind('hb_buffer_set_language',None,ptr,ptr)
shape=bind('hb_shape',None,ptr,ptr,ptr,uint)
infos=bind('hb_buffer_get_glyph_infos',C.POINTER(Info),ptr,C.POINTER(uint))
positions=bind('hb_buffer_get_glyph_positions',C.POINTER(Position),ptr,C.POINTER(uint))
version=bind('hb_version_string',string)
for kind in ['blob','face','font','buffer']: bind('hb_'+kind+'_destroy',None,ptr)

class Shaper:
    def __init__(self,path):
        self.tt=TTFont(path);self.upem=self.tt['head'].unitsPerEm
        blob=blob_create(str(path).encode());assert blob,f'Cannot open {path}'
        face=face_create(blob,0);self.font=font_create(face);ot_funcs(self.font)
        scale(self.font,self.upem,self.upem)
        lib.hb_face_destroy(face);lib.hb_blob_destroy(blob)
    def shape(self,text,language='en',features=None):
        b=buffer_create();encoded=text.encode('utf8');add(b,encoded,len(encoded),0,len(encoded))
        setlang(b,lang(language.encode(),-1));guess(b)
        ff=(Feature*len(features or {}))(*(Feature(int.from_bytes(tag.encode(),"big"),value,0,0xffffffff) for tag,value in (features or {}).items()))
        shape(self.font,b,ff,len(ff))
        count=uint();ii=infos(b,C.byref(count));pp=positions(b,C.byref(count))
        result=[dict(gid=ii[i].codepoint,glyph=self.tt.getGlyphName(ii[i].codepoint),
                     cluster=ii[i].cluster,advance=pp[i].x_advance,y_advance=pp[i].y_advance,
                     dx=pp[i].x_offset,dy=pp[i].y_offset) for i in range(count.value)]
        lib.hb_buffer_destroy(b);return result
    def close(self):
        if self.font: lib.hb_font_destroy(self.font);self.font=None

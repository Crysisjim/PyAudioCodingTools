# taskbar_utils.py
import sys
import os
import ctypes
from ctypes import wintypes

# --- DÉFINITIONS CONSTANTES WINDOWS ---
CLSID_TaskbarList = "{56FDF344-FD6D-11d0-958A-006097C9A090}"
IID_ITaskbarList3 = "{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}"

TBPF_NOPROGRESS = 0
TBPF_INDETERMINATE = 1
TBPF_NORMAL = 2
TBPF_ERROR = 4
TBPF_PAUSED = 8

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8)
    ]

class TaskbarController:
    def __init__(self, root):
        self.root = root
        self.taskbar_interface = None
        self.hwnd = 0
        self.ptr = None
        
        if os.name == 'nt':
            try:
                # 1. Initialiser COM
                ctypes.windll.ole32.CoInitialize(0)
                
                # 2. Créer l'objet TaskbarList
                clsid = GUID()
                iid = GUID()
                ctypes.windll.ole32.CLSIDFromString(ctypes.c_wchar_p(CLSID_TaskbarList), ctypes.byref(clsid))
                ctypes.windll.ole32.CLSIDFromString(ctypes.c_wchar_p(IID_ITaskbarList3), ctypes.byref(iid))
                
                self.ptr = ctypes.c_void_p()
                ctypes.windll.ole32.CoCreateInstance(
                    ctypes.byref(clsid),
                    0,
                    1, # CLSCTX_INPROC_SERVER
                    ctypes.byref(iid),
                    ctypes.byref(self.ptr)
                )
                
                # 3. Récupérer le HWND (Handle de fenêtre)
                try:
                    self.hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                    if not self.hwnd:
                        self.hwnd = self.root.winfo_id()
                except Exception as e:
                    print(f"Avertissement: Impossible de récupérer le HWND: {e}")
                    self.hwnd = 0

            except Exception as e:
                print(f"Erreur init Taskbar: {e}")
                self.ptr = None

    def _call_method(self, method_index, *args):
        """Appelle une méthode COM par son index dans la VTable"""
        if not self.ptr or not self.hwnd:
            return
        try:
            # Récupération de la VTable (table des méthodes virtuelles)
            vtable = ctypes.cast(self.ptr, ctypes.POINTER(ctypes.c_void_p)).contents
            func_ptr = ctypes.cast(vtable.value + (method_index * ctypes.sizeof(ctypes.c_void_p)), ctypes.POINTER(ctypes.c_void_p)).contents
            
            # Définition de la signature de la fonction (WINFUNCTYPE pour stdcall)
            arg_types = [ctypes.c_void_p, ctypes.c_void_p] + [ctypes.c_uint64 for _ in args]
            
            functype = ctypes.WINFUNCTYPE(ctypes.c_long, *arg_types)
            func = functype(func_ptr.value)
            
            func(self.ptr, ctypes.c_void_p(self.hwnd), *args)
        except Exception as e:
            print(f"Erreur appel COM méthode {method_index}: {e}")

    def set_progress(self, current, total):
        # SetProgressValue est la méthode index 9 dans ITaskbarList3
        self._call_method(9, int(current), int(total))

    def set_state_normal(self):
        # SetProgressState est la méthode index 10
        self._call_method(10, TBPF_NORMAL)

    def set_state_paused(self):
        self._call_method(10, TBPF_PAUSED)

    def set_state_error(self):
        self._call_method(10, TBPF_ERROR)

    def set_state_off(self):
        self._call_method(10, TBPF_NOPROGRESS)

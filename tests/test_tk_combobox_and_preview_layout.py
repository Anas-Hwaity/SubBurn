from __future__ import annotations
import importlib.util, pathlib, sys, time, tkinter.ttk as ttk
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_tk_combo_layout',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
root=mod.create_root(); app=mod.SubBurnApp(root)
def pump(n=12):
    for _ in range(n): root.update(); time.sleep(.01)
try:
    pump()
    # The themed combobox popdown must construct and post correctly; one global option-db defect breaks every selector.
    probe=ttk.Combobox(root,values=('One','Two','Three'),state='readonly'); probe.set('One'); probe.place(x=350,y=20,width=220,height=32); pump(3)
    probe.event_generate('<Button-1>',x=210,y=15); pump(3)
    pop=probe.tk.call('ttk::combobox::PopdownWindow',probe._w)
    assert bool(int(probe.tk.call('winfo','ismapped',pop))), 'TCombobox popdown did not map after click'
    probe.event_generate('<Button-1>',x=210,y=15); pump(2)
    assert not bool(int(probe.tk.call('winfo','ismapped',pop))), 'TCombobox popdown did not unpost on second click'

    # Preview explanatory text must wrap to the available width instead of being clipped.
    target='Render frame is exact and interactive.'
    found=[]
    def walk(w):
        for child in w.winfo_children():
            try:
                if isinstance(child,ttk.Label) and str(child.cget('text')).startswith(target): found.append(child)
            except Exception: pass
            walk(child)
    walk(root)
    assert found, 'preview helper label not found'
    label=found[0]; pump(3)
    assert int(float(label.cget('wraplength'))) >= 320, label.cget('wraplength')
    assert str(label.cget('justify'))=='left'
    print('TK COMBOBOX GLOBAL POSTING + PREVIEW WRAP PASS')
finally:
    try: app.dashboard_server.shutdown()
    except Exception: pass
    try: app.system_usage_sampler.stop_event.set()
    except Exception: pass
    try: root.destroy()
    except Exception: pass

from swesmith.profiles import registry
from swesmith.bug_gen.procedural.golang.control_flow import ControlIfElseInvertModifier


def test_control_if_else_invert():
    rp = registry.get("caddyserver__caddy.77dd12cc")
    entities = rp.extract_entities()
    pm = ControlIfElseInvertModifier(likelihood=1.0)
    entities = [x for x in entities if pm.can_change(x)]
    assert len(entities) == 164
    test_entity = entities[4]
    modified = pm.modify(test_entity)
    expected = """func (up *UsagePool) LoadOrNew(key any, construct Constructor) (value any, loaded bool, err error) {
	var upv *usagePoolVal
	up.Lock()
	upv, loaded = up.pool[key]
	if loaded {
		upv = &usagePoolVal{refs: 1}
		upv.Lock()
		up.pool[key] = upv
		up.Unlock()
		value, err = construct()
		if err == nil {
			upv.value = value
		} else {
			upv.err = err
			up.Lock()
			// this *should* be safe, I think, because we have a
			// write lock on upv, but we might also need to ensure
			// that upv.err is nil before doing this, since we
			// released the write lock on up during construct...
			// but then again it's also after midnight...
			delete(up.pool, key)
			up.Unlock()
		}
		upv.Unlock()
	} else {
		atomic.AddInt32(&upv.refs, 1)
		up.Unlock()
		upv.RLock()
		value = upv.value
		err = upv.err
		upv.RUnlock()
	}
	return
}"""
    assert modified.rewrite == expected
